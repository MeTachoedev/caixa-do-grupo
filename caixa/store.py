"""SQLite local: transações curtas para compartilhar as vendas entre sessões."""

import sqlite3
import time
from contextlib import closing, contextmanager
from pathlib import Path
from uuid import UUID, uuid4

from .domain import ICONS, PAYMENTS, Invalid, check_cents, clean_text, stamp, text_key

SCHEMA = """
CREATE TABLE IF NOT EXISTS people (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, name_key TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS products (
 id TEXT PRIMARY KEY, person_id TEXT NOT NULL REFERENCES people(id),
 name TEXT NOT NULL, name_key TEXT NOT NULL, icon TEXT NOT NULL,
 price INTEGER NOT NULL CHECK(price BETWEEN 1 AND 99999999),
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
 version INTEGER NOT NULL DEFAULT 1,
 UNIQUE(person_id, name_key)
);
CREATE TABLE IF NOT EXISTS sales (
 id TEXT PRIMARY KEY, operation TEXT NOT NULL UNIQUE,
 person_id TEXT NOT NULL REFERENCES people(id),
 product_id TEXT NOT NULL REFERENCES products(id),
 person_name TEXT NOT NULL, product_name TEXT NOT NULL,
 base_price INTEGER NOT NULL CHECK(base_price BETWEEN 1 AND 99999999),
 amount INTEGER NOT NULL CHECK(amount > 0 AND amount <= base_price),
 payment TEXT NOT NULL CHECK(payment IN ('pix','credito','debito')),
 created_at TEXT NOT NULL,
 cancelled_at TEXT, cancel_reason TEXT,
 CHECK((cancelled_at IS NULL AND cancel_reason IS NULL) OR
       (cancelled_at IS NOT NULL AND length(cancel_reason) BETWEEN 3 AND 300))
);
CREATE INDEX IF NOT EXISTS sales_date ON sales(created_at);
CREATE TABLE IF NOT EXISTS login_attempts (at REAL NOT NULL);
"""


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(SCHEMA)

    def connect(self):
        conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @contextmanager
    def write(self):
        with closing(self.connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def people(self):
        with closing(self.connect()) as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM people ORDER BY name_key")]

    def add_person(self, name):
        name = clean_text(name, 60)
        person_id = str(uuid4())
        try:
            with self.write() as conn:
                conn.execute("INSERT INTO people VALUES (?,?,?)", (person_id, name, text_key(name)))
        except sqlite3.IntegrityError as exc:
            raise Invalid("Já existe uma pessoa com esse nome. Selecione o cadastro existente.") from exc
        return person_id

    def products(self, person_id, include_archived=False):
        with closing(self.connect()) as conn:
            sql = "SELECT * FROM products WHERE person_id=?"
            if not include_archived:
                sql += " AND active=1"
            return [dict(r) for r in conn.execute(sql + " ORDER BY name_key", (person_id,))]

    def save_product(self, person_id, name, icon, price, product_id=None):
        name = clean_text(name, 80)
        check_cents(price)
        if icon not in ICONS:
            raise Invalid("Selecione um ícone da lista.")
        target = product_id or str(uuid4())
        try:
            with self.write() as conn:
                if not conn.execute("SELECT 1 FROM people WHERE id=?", (person_id,)).fetchone():
                    raise Invalid("Selecione uma pessoa cadastrada.")
                if product_id:
                    cursor = conn.execute(
                        "UPDATE products SET name=?,name_key=?,icon=?,price=?,version=version+1 WHERE id=? AND person_id=?",
                        (name, text_key(name), icon, price, product_id, person_id),
                    )
                    if cursor.rowcount != 1:
                        raise Invalid("Produto não encontrado para essa pessoa.")
                else:
                    conn.execute(
                        "INSERT INTO products(id,person_id,name,name_key,icon,price) VALUES (?,?,?,?,?,?)",
                        (target, person_id, name, text_key(name), icon, price),
                    )
        except sqlite3.IntegrityError as exc:
            raise Invalid("Essa pessoa já tem um produto com esse nome, inclusive nos arquivados.") from exc
        return target

    def archive_product(self, person_id, product_id, active=False):
        with self.write() as conn:
            changed = conn.execute(
                "UPDATE products SET active=?,version=version+1 WHERE id=? AND person_id=?",
                (int(bool(active)), product_id, person_id),
            )
            if changed.rowcount != 1:
                raise Invalid("Produto não encontrado para essa pessoa.")

    def proposal(self, person_id, product_id):
        with closing(self.connect()) as conn:
            row = conn.execute(
                "SELECT p.*,u.name AS person_name FROM products p JOIN people u ON u.id=p.person_id WHERE p.id=? AND p.person_id=? AND p.active=1",
                (product_id, person_id),
            ).fetchone()
            if not row:
                raise Invalid("Esse produto não está disponível. Atualize a lista.")
        result = dict(row)
        result["operation"] = str(uuid4())
        return result

    def record(self, proposal, amount, payment, now=None):
        check_cents(amount)
        if payment not in PAYMENTS:
            raise Invalid("Escolha Pix, crédito ou débito antes de confirmar.")
        try:
            operation = str(UUID(proposal["operation"]))
            product_id, person_id = str(UUID(proposal["id"])), str(UUID(proposal["person_id"]))
            version = proposal["version"]
        except (KeyError, ValueError, TypeError, AttributeError) as exc:
            raise Invalid("A confirmação expirou. Abra a venda novamente.") from exc
        with self.write() as conn:
            prior = conn.execute("SELECT * FROM sales WHERE operation=?", (operation,)).fetchone()
            if prior:
                if (prior["amount"], prior["payment"], prior["product_id"], prior["person_id"]) != (amount, payment, product_id, person_id):
                    raise Invalid("Essa confirmação já foi usada com outros valores. Confira o extrato.")
                return dict(prior)
            product = conn.execute(
                "SELECT p.*,u.name AS person_name FROM products p JOIN people u ON u.id=p.person_id WHERE p.id=? AND p.person_id=?",
                (product_id, person_id),
            ).fetchone()
            if not product or not product["active"] or product["version"] != version:
                raise Invalid("O produto mudou ou foi arquivado. Volte e abra uma nova venda.")
            if amount > product["price"]:
                raise Invalid("O valor da venda não pode superar o preço cadastrado.")
            sale_id = str(uuid4())
            conn.execute(
                "INSERT INTO sales(id,operation,person_id,product_id,person_name,product_name,base_price,amount,payment,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (sale_id, operation, person_id, product_id, product["person_name"], product["name"], product["price"], amount, payment, stamp(now)),
            )
            return dict(conn.execute("SELECT * FROM sales WHERE id=?", (sale_id,)).fetchone())

    def sales(self, start, end, person_id=None, payment=None):
        sql = "SELECT * FROM sales WHERE created_at>=? AND created_at<?"
        params = [start, end]
        if person_id:
            sql += " AND person_id=?"
            params.append(person_id)
        if payment:
            if payment not in PAYMENTS:
                raise Invalid("Forma de pagamento inválida.")
            sql += " AND payment=?"
            params.append(payment)
        with closing(self.connect()) as conn:
            return [dict(r) for r in conn.execute(sql + " ORDER BY created_at,id", params)]

    def cancel(self, sale_id, reason, now=None):
        reason = clean_text(reason, 300, 3)
        with self.write() as conn:
            sale = conn.execute("SELECT * FROM sales WHERE id=?", (sale_id,)).fetchone()
            if not sale:
                raise Invalid("Venda não encontrada.")
            if sale["cancelled_at"] is None:
                conn.execute("UPDATE sales SET cancelled_at=?,cancel_reason=? WHERE id=?", (stamp(now), reason, sale_id))

    def admit_login(self, now=None):
        now = time.time() if now is None else now
        with self.write() as conn:
            conn.execute("DELETE FROM login_attempts WHERE at<=?", (now - 60,))
            count = conn.execute("SELECT COUNT(*) FROM login_attempts").fetchone()[0]
            if count >= 20:
                return False
            conn.execute("INSERT INTO login_attempts(at) VALUES (?)", (now,))
            return True
