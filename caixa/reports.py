"""Extratos do mesmo conjunto de lançamentos mostrado na tela."""

import csv
import io
import unicodedata

from .domain import PAYMENTS, decimal_text, local_time


def totals(rows):
    active = [r for r in rows if not r["cancelled_at"]]
    return {
        "units": len(active),
        "amount": sum(r["amount"] for r in active),
        "discount": sum(r["base_price"] - r["amount"] for r in active),
        "payments": {key: sum(r["amount"] for r in active if r["payment"] == key) for key in PAYMENTS},
    }


def groups(rows, field):
    result = {}
    for row in rows:
        if row["cancelled_at"]:
            continue
        key = row[f"{field}_id"]
        item = result.setdefault(key, {"name": "", "units": 0, "amount": 0})
        item["name"] = row[f"{field}_name"]
        if field == "product":
            item["person"] = row["person_name"]
        item["units"] += 1
        item["amount"] += row["amount"]
    return list(result.values())


def safe_cell(value):
    value = str(value)
    normalized = unicodedata.normalize("NFKC", value)
    stripped = normalized.lstrip(" \t\r\n\v\f\ufeff\u200b")
    if stripped.startswith(("=", "+", "-", "@")) or any(unicodedata.category(c).startswith("C") for c in normalized):
        return "texto: " + value
    return value


def export_csv(rows):
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=";", lineterminator="\r\n")
    writer.writerow(["Identificador", "Data e hora (Brasília)", "Pessoa", "Produto", "Unidades", "Preço padrão (R$)", "Desconto (R$)", "Valor da venda (R$)", "Pagamento", "Situação", "Cancelada em (Brasília)", "Motivo"])
    for row in rows:
        writer.writerow([
            row["id"], local_time(row["created_at"]), safe_cell(row["person_name"]), safe_cell(row["product_name"]), 1,
            decimal_text(row["base_price"]), decimal_text(row["base_price"] - row["amount"]), decimal_text(row["amount"]),
            PAYMENTS[row["payment"]], "Cancelada" if row["cancelled_at"] else "Válida",
            local_time(row["cancelled_at"]) if row["cancelled_at"] else "", safe_cell(row["cancel_reason"] or ""),
        ])
    return output.getvalue().encode("utf-8")
