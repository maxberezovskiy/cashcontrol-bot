"""Помощники форматирования сообщений бота."""
from __future__ import annotations

import html
from datetime import datetime
from decimal import Decimal, InvalidOperation


def esc(value) -> str:
    """Экранирует пользовательский текст для parse_mode=HTML (& < >)."""
    return html.escape(str(value), quote=False)

_CURRENCY_SIGN = {"RUB": "₽", "USD": "$", "EUR": "€"}

_TYPE_EMOJI = {"income": "🟢", "expense": "🔴", "transfer": "🔁"}
_TYPE_LABEL = {"income": "Доход", "expense": "Расход", "transfer": "Перевод"}


def money(amount, currency: str = "RUB") -> str:
    try:
        value = Decimal(str(amount))
    except (InvalidOperation, TypeError):
        value = Decimal(0)
    sign = _CURRENCY_SIGN.get(currency, currency)
    # Разделитель тысяч пробелом, 2 знака
    formatted = f"{value:,.2f}".replace(",", " ")
    return f"{formatted} {sign}"


def type_label(transaction_type: str) -> str:
    emoji = _TYPE_EMOJI.get(transaction_type, "•")
    label = _TYPE_LABEL.get(transaction_type, transaction_type)
    return f"{emoji} {label}"


def parse_date(value: str | None) -> str:
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%d.%m.%Y")
    except (ValueError, AttributeError):
        return str(value)


def transaction_line(
    tx: dict,
    *,
    accounts_by_id: dict[int, dict] | None = None,
    categories_by_id: dict[int, dict] | None = None,
) -> str:
    accounts_by_id = accounts_by_id or {}
    categories_by_id = categories_by_id or {}
    currency = tx.get("currency", "RUB")
    amount = money(tx.get("amount", 0), currency)
    ttype = tx.get("transaction_type", "")
    emoji = _TYPE_EMOJI.get(ttype, "•")
    sign = "+" if ttype == "income" else ("−" if ttype == "expense" else "")
    date = parse_date(tx.get("date"))

    cat = categories_by_id.get(tx.get("category_id"))
    cat_name = esc(cat["name"] if cat else (tx.get("description") or "—"))
    acc = accounts_by_id.get(tx.get("account_id"))
    acc_name = esc(acc["name"]) if acc else ""

    parts = [f"{emoji} {sign}{amount}", f"· {cat_name}"]
    if acc_name:
        parts.append(f"· {acc_name}")
    if date:
        parts.append(f"· {date}")
    return " ".join(parts)
