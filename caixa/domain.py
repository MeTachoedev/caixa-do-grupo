"""Validações e formatos usados no caixa."""

import re
import unicodedata
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

ZONE = ZoneInfo("America/Sao_Paulo")
PAYMENTS = {"pix": "Pix", "credito": "Crédito", "debito": "Débito"}
ICONS = {
    "Produto": ":material/shopping_bag:",
    "Comida": ":material/restaurant:",
    "Bebida": ":material/local_drink:",
    "Café": ":material/local_cafe:",
    "Doce": ":material/cake:",
    "Roupa": ":material/checkroom:",
    "Presente": ":material/redeem:",
}
MAX_CENTS = 99_999_999


class Invalid(ValueError):
    """Entrada ou operação que não pode ser registrada."""


def clean_text(value, limit, minimum=1):
    if not isinstance(value, str):
        raise Invalid("Informe um texto válido.")
    value = unicodedata.normalize("NFC", value.strip())
    if not minimum <= len(value) <= limit or any(unicodedata.category(c).startswith("C") for c in value):
        raise Invalid(f"Use entre {minimum} e {limit} caracteres, sem quebras de linha.")
    return value


def text_key(value):
    return unicodedata.normalize("NFC", value).casefold()


def cents(value):
    if not isinstance(value, str) or not re.fullmatch(r"(?:0|[1-9][0-9]{0,5})(?:[,.][0-9]{1,2})?", value.strip()):
        raise Invalid("Informe o valor como 12,50, sem separador de milhar e com até duas casas.")
    result = int(Decimal(value.strip().replace(",", ".")) * 100)
    check_cents(result)
    return result


def check_cents(value):
    if type(value) is not int or not 1 <= value <= MAX_CENTS:
        raise Invalid("O valor deve ser maior que zero e no máximo R$ 999.999,99.")
    return value


def decimal_text(value):
    return f"{value // 100},{value % 100:02d}"


def money(value):
    return f"R$ {value // 100:,}".replace(",", ".") + f",{value % 100:02d}"


def day_bounds(first, last):
    if type(first) is not date or type(last) is not date or last < first:
        raise Invalid("Escolha um período válido; o fim deve ser igual ou posterior ao início.")
    start = datetime.combine(first, time.min, ZONE)
    end = datetime.combine(last + timedelta(days=1), time.min, ZONE)
    return stamp(start), stamp(end)


def stamp(value=None):
    value = value or datetime.now(timezone.utc)
    if value.tzinfo is None:
        raise Invalid("O horário precisa incluir o fuso.")
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")


def local_time(value):
    return datetime.fromisoformat(value).astimezone(ZONE).strftime("%d/%m/%Y %H:%M:%S")
