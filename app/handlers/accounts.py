"""Баланс и счета: /balance, /accounts."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.api_client import ApiError, NotLinkedError, client
from app.formatting import esc, money

router = Router()

NOT_LINKED = "🔗 Сначала привяжите аккаунт: /link КОД (код берётся в веб-приложении)."

_ACCOUNT_TYPE_EMOJI = {
    "cash": "💵",
    "card": "💳",
    "deposit": "🏦",
    "credit": "💳",
}


async def _show_balance(message: Message) -> None:
    try:
        accounts = await client.get_accounts(message.from_user.id)
    except NotLinkedError:
        await message.answer(NOT_LINKED)
        return
    except ApiError as e:
        await message.answer(f"❌ {e.message}")
        return

    if not accounts:
        await message.answer("У вас пока нет счетов. Создайте их в веб-приложении.")
        return

    totals: dict[str, Decimal] = defaultdict(Decimal)
    lines = ["<b>💰 Баланс</b>", ""]
    for acc in accounts:
        emoji = _ACCOUNT_TYPE_EMOJI.get(acc.get("account_type"), "•")
        currency = acc.get("currency", "RUB")
        balance = Decimal(str(acc.get("balance", 0)))
        totals[currency] += balance
        lines.append(f"{emoji} {esc(acc['name'])}: <b>{money(balance, currency)}</b>")

    lines.append("")
    if len(totals) == 1:
        currency, total = next(iter(totals.items()))
        lines.append(f"Итого: <b>{money(total, currency)}</b>")
    else:
        lines.append("Итого:")
        for currency, total in totals.items():
            lines.append(f"  • <b>{money(total, currency)}</b>")

    await message.answer("\n".join(lines))


async def _show_accounts(message: Message) -> None:
    try:
        accounts = await client.get_accounts(message.from_user.id)
    except NotLinkedError:
        await message.answer(NOT_LINKED)
        return
    except ApiError as e:
        await message.answer(f"❌ {e.message}")
        return

    if not accounts:
        await message.answer("У вас пока нет счетов. Создайте их в веб-приложении.")
        return

    lines = ["<b>🏦 Счета</b>", ""]
    for acc in accounts:
        emoji = _ACCOUNT_TYPE_EMOJI.get(acc.get("account_type"), "•")
        currency = acc.get("currency", "RUB")
        lines.append(f"{emoji} <b>{esc(acc['name'])}</b> — {money(acc.get('balance', 0), currency)}")
    await message.answer("\n".join(lines))


@router.message(Command("balance"))
async def balance_command(message: Message) -> None:
    await _show_balance(message)


@router.message(F.text == "💰 Баланс")
async def balance_button(message: Message) -> None:
    await _show_balance(message)


@router.message(Command("accounts"))
async def accounts_command(message: Message) -> None:
    await _show_accounts(message)


@router.message(F.text == "🏦 Счета")
async def accounts_button(message: Message) -> None:
    await _show_accounts(message)
