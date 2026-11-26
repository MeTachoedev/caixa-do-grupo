import csv
import io
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone

import pytest

from caixa.auth import IDLE, MAX_AGE, authenticate, authorized
from caixa.domain import Invalid, cents, day_bounds, money
from caixa.reports import export_csv, groups, safe_cell, totals
from caixa.store import Store


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "test.sqlite3")


def item(store, name="Pessoa fictícia", product="Produto de teste", price=1000):
    person = store.add_person(name)
    product_id = store.save_product(person, product, "Produto", price)
    return store.proposal(person, product_id)


def all_sales(store):
    return store.sales(*day_bounds(date(2000, 1, 1), date(2099, 1, 1)))


@pytest.mark.parametrize("raw,expected", [("12,50", 1250), ("0.01", 1), ("10", 1000), ("999999,99", 99999999), (" 1,2 ", 120)])
def test_money_exact(raw, expected):
    assert cents(raw) == expected


@pytest.mark.parametrize("raw", ["", "0", "-1", "1,001", "1.000,00", "NaN", "Infinity", "1e3", "1000000", "01", "=1+1", None, 1.2])
def test_money_rejects_invalid(raw):
    with pytest.raises(Invalid):
        cents(raw)


def test_money_display():
    assert money(123456) == "R$ 1.234,56"


def test_people_products_and_reopen(store):
    proposal = item(store)
    reopened = Store(store.path)
    assert reopened.people()[0]["name"] == "Pessoa fictícia"
    assert reopened.products(proposal["person_id"])[0]["price"] == 1000
    with pytest.raises(Invalid):
        reopened.add_person(" PESSOA FICTÍCIA ")
    with pytest.raises(Invalid):
        reopened.save_product(proposal["person_id"], "produto de teste", "Produto", 500)
    other = reopened.add_person("Outra pessoa fictícia")
    reopened.save_product(other, "Produto de teste", "Produto", 500)


@pytest.mark.parametrize("name", ["", "x" * 61, "linha\nnova", "oculto\x00"])
def test_bad_person(store, name):
    with pytest.raises(Invalid):
        store.add_person(name)


def test_sale_discount_and_idempotency(store):
    proposal = item(store)
    sale = store.record(proposal, 800, "pix")
    assert store.record(proposal, 800, "pix")["id"] == sale["id"]
    assert len(all_sales(store)) == 1
    assert store.products(proposal["person_id"])[0]["price"] == 1000
    with pytest.raises(Invalid):
        store.record(proposal, 900, "pix")


@pytest.mark.parametrize("amount,payment", [(0, "pix"), (1001, "pix"), (1000, None), (1000, "dinheiro"), (True, "pix"), (1.1, "pix")])
def test_bad_sale(store, amount, payment):
    proposal = item(store)
    with pytest.raises(Invalid):
        store.record(proposal, amount, payment)
    assert not all_sales(store)


def test_stale_proposal_historical_snapshot_and_replay(store):
    proposal = item(store)
    sale = store.record(proposal, 800, "pix")
    unrecorded = store.proposal(proposal["person_id"], proposal["id"])
    store.save_product(proposal["person_id"], "Novo nome fictício", "Comida", 1500, proposal["id"])
    with pytest.raises(Invalid, match="mudou"):
        store.record(unrecorded, 1000, "debito")
    assert store.record(proposal, 800, "pix")["id"] == sale["id"]
    assert all_sales(store)[0]["product_name"] == "Produto de teste"
    assert all_sales(store)[0]["base_price"] == 1000


def test_archived_product_not_sold_but_keeps_history(store):
    proposal = item(store)
    store.record(proposal, 1000, "credito")
    unrecorded = store.proposal(proposal["person_id"], proposal["id"])
    store.archive_product(proposal["person_id"], proposal["id"])
    with pytest.raises(Invalid):
        store.record(unrecorded, 1000, "pix")
    assert store.products(proposal["person_id"]) == []
    assert len(all_sales(store)) == 1
    store.archive_product(proposal["person_id"], proposal["id"], True)
    assert len(store.products(proposal["person_id"])) == 1


def test_cancel_and_replay_do_not_resurrect(store):
    proposal = item(store)
    sale = store.record(proposal, 800, "pix")
    store.cancel(sale["id"], "Motivo fictício")
    store.cancel(sale["id"], "Outro motivo fictício")
    replay = store.record(proposal, 800, "pix")
    assert replay["cancelled_at"]
    assert replay["cancel_reason"] == "Motivo fictício"
    assert totals(all_sales(store))["units"] == 0
    assert len(all_sales(store)) == 1


def test_cancel_invalid(store):
    with pytest.raises(Invalid):
        store.cancel("inexistente", "Motivo fictício")
    with pytest.raises(Invalid):
        store.cancel("inexistente", " ")


def test_parallel_distinct_and_repeated_confirmations(store):
    proposal = item(store)
    different = store.proposal(proposal["person_id"], proposal["id"])
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda p: store.record(p, 1000, "pix"), [proposal, proposal, different, different]))
    assert len({r["id"] for r in results}) == 2
    assert totals(all_sales(store))["amount"] == 2000


def test_method_scenario_filters_and_csv(store):
    sales = []
    for name, base, paid, method in [("A fictício", 1000, 800, "pix"), ("B fictício", 2000, 2000, "credito"), ("C fictício", 1500, 1000, "debito")]:
        proposal = item(store, name=name, price=base)
        sales.append(store.record(proposal, paid, method))
    result = totals(all_sales(store))
    assert (result["units"], result["amount"], result["discount"]) == (3, 3800, 700)
    assert result["payments"] == {"pix": 800, "credito": 2000, "debito": 1000}
    store.cancel(sales[1]["id"], "Exemplo de correção")
    assert totals(all_sales(store))["amount"] == 1800
    filtered = store.sales(*day_bounds(date(2000, 1, 1), date(2099, 1, 1)), payment="debito")
    assert totals(filtered) == {"units": 1, "amount": 1000, "discount": 500, "payments": {"pix": 0, "credito": 0, "debito": 1000}}
    content = list(csv.reader(io.StringIO(export_csv(all_sales(store)).decode("utf-8")), delimiter=";"))
    assert len(content) == 4
    assert "Cancelada" in content[2]


def test_midnight_brasilia(store):
    proposal = item(store)
    for amount, hour in [(100, "2026-11-26T02:59:59+00:00"), (200, "2026-11-26T03:00:00+00:00"), (300, "2026-11-27T02:59:59+00:00"), (400, "2026-11-27T03:00:00+00:00")]:
        p = store.proposal(proposal["person_id"], proposal["id"])
        store.record(p, amount, "pix", datetime.fromisoformat(hour))
    rows = store.sales(*day_bounds(date(2026, 11, 26), date(2026, 11, 26)))
    assert (totals(rows)["units"], totals(rows)["amount"]) == (2, 500)
    with pytest.raises(Invalid):
        day_bounds(date(2026, 11, 27), date(2026, 11, 26))


def test_product_groups_keep_person_separate(store):
    first = item(store, name="Pessoa A", product="Igual")
    second = item(store, name="Pessoa B", product="Igual")
    store.record(first, 1000, "pix")
    store.record(second, 1000, "pix")
    assert len(groups(all_sales(store), "product")) == 2


@pytest.mark.parametrize("value", ["=1+1", " +1", "\t@SUM(1)", "\ufeff-1", "＝1+1", "\u200b=1", "A\n=2"])
def test_csv_formula_text(value):
    assert safe_cell(value).startswith("texto: ")


def test_csv_quotes_accents_and_formula(store):
    proposal = item(store, name="=1+1", product='Café; "Especial"')
    store.record(proposal, 1000, "pix")
    data = export_csv(all_sales(store))
    assert not data.startswith(b"\xef\xbb\xbf")
    row = list(csv.reader(io.StringIO(data.decode("utf-8")), delimiter=";"))[1]
    assert row[2] == "texto: =1+1"
    assert row[3] == 'Café; "Especial"'
    assert row[7] == "10,00"


def test_auth_expiry_rotation_and_global_limit(store):
    secret = "senha-ficticia-de-teste"
    session, error = authenticate(secret, secret, store, 100)
    assert not error and authorized(session, secret, 101)
    assert not authorized(session, secret, 100 + IDLE)
    session["last"] = 100 + MAX_AGE
    assert not authorized(session, secret, 100 + MAX_AGE)
    assert not authorized(session, "outra-senha-ficticia", 101)
    for _ in range(19):
        assert authenticate("errada", secret, store, 101)[0] is None
    assert "Muitas tentativas" in authenticate(secret, secret, Store(store.path), 102)[1]
    assert authenticate(secret, secret, store, 162)[0]


def test_parallel_login_limit(store):
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: store.admit_login(200), range(30)))
    assert sum(results) == 20
    assert store.admit_login(261)


def test_invalid_secret_or_session(store):
    assert authenticate("curta", "curta", store)[0] is None
    assert not authorized(None, "senha-ficticia-valida")
    assert not authorized({}, "senha-ficticia-valida")
    assert not authorized({"version": None}, "senha-ficticia-valida")
