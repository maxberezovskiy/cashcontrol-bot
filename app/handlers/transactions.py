"""Добавление и просмотр операций: /add (мастер), /last."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.api_client import ApiError, NotLinkedError, client
from app.formatting import esc, money, transaction_line
from app.keyboards import (
    accounts_kb,
    categories_kb,
    main_menu,
    skip_note_kb,
    transaction_type_kb,
)
from app.states import AddTransaction

router = Router()

NOT_LINKED = "🔗 Сначала привяжите аккаунт: /link КОД (код берётся в веб-приложении)."

_TYPE_TITLE = {"expense": "🔴 Расход", "income": "🟢 Доход"}


def _parse_amount(text: str) -> Decimal | None:
    cleaned = text.strip().replace(" ", "").replace(",", ".")
    try:
        value = Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None
    if value <= 0:
        return None
    return value


# --- /last ---


async def _show_last(message: Message) -> None:
    tg_id = message.from_user.id
    try:
        await client.authorize(tg_id)  # один минт токена до параллельных запросов
        transactions, accounts, categories = await asyncio.gather(
            client.get_transactions(tg_id, limit=10),
            client.get_accounts(tg_id),
            client.get_categories(tg_id),
        )
    except NotLinkedError:
        await message.answer(NOT_LINKED)
        return
    except ApiError as e:
        await message.answer(f"❌ {esc(e.message)}")
        return

    if not transactions:
        await message.answer("Операций пока нет. Добавьте первую через /add.")
        return

    accounts_by_id = {a["id"]: a for a in accounts}
    categories_by_id = {c["id"]: c for c in categories}
    lines = ["<b>🧾 Последние операции</b>", ""]
    for tx in transactions:
        lines.append(
            transaction_line(tx, accounts_by_id=accounts_by_id, categories_by_id=categories_by_id)
        )
    await message.answer("\n".join(lines))


@router.message(Command("last"))
async def last_command(message: Message) -> None:
    await _show_last(message)


@router.message(F.text == "🧾 Операции")
async def last_button(message: Message) -> None:
    await _show_last(message)


# --- /add (мастер) ---


@router.message(Command("add"))
async def add_command(message: Message, state: FSMContext) -> None:
    await _start_add(message, state)


@router.message(F.text == "➕ Добавить")
async def add_button(message: Message, state: FSMContext) -> None:
    await _start_add(message, state)


async def _start_add(message: Message, state: FSMContext) -> None:
    if not await client.is_linked(message.from_user.id):
        await message.answer(NOT_LINKED)
        return
    await state.clear()
    await state.set_state(AddTransaction.choosing_type)
    await message.answer("Что добавляем?", reply_markup=transaction_type_kb())


@router.callback_query(F.data == "tx:cancel")
async def cancel_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Отменено.")
    await callback.answer()


@router.callback_query(AddTransaction.choosing_type, F.data.startswith("txtype:"))
async def choose_type(callback: CallbackQuery, state: FSMContext) -> None:
    tx_type = callback.data.split(":", 1)[1]
    if tx_type not in {"expense", "income"}:
        await callback.answer("Неверный тип операции")
        return
    await state.update_data(transaction_type=tx_type)
    await state.set_state(AddTransaction.entering_amount)
    await callback.message.edit_text(
        f"{_TYPE_TITLE.get(tx_type, tx_type)}\n\n"
        "Введите сумму (например, <code>1500</code> или <code>1500.50</code>):"
    )
    await callback.answer()


@router.message(AddTransaction.entering_amount)
async def enter_amount(message: Message, state: FSMContext) -> None:
    amount = _parse_amount(message.text or "")
    if amount is None:
        await message.answer("Не понял сумму. Введите положительное число, например <code>1500</code>.")
        return
    await state.update_data(amount=str(amount))

    tg_id = message.from_user.id
    try:
        accounts = await client.get_accounts(tg_id)
    except ApiError as e:
        await state.clear()
        await message.answer(f"❌ {esc(e.message)}")
        return

    if not accounts:
        await state.clear()
        await message.answer("Нет ни одного счёта. Создайте счёт в веб-приложении.")
        return

    if len(accounts) == 1:
        await state.update_data(account_id=accounts[0]["id"])
        await _ask_category(message, state, tg_id, edit=False)
        return

    await state.set_state(AddTransaction.choosing_account)
    await message.answer("На каком счёте?", reply_markup=accounts_kb(accounts))


@router.callback_query(AddTransaction.choosing_account, F.data.startswith("txacc:"))
async def choose_account(callback: CallbackQuery, state: FSMContext) -> None:
    account_id = int(callback.data.split(":", 1)[1])
    await state.update_data(account_id=account_id)
    await _ask_category(callback.message, state, callback.from_user.id, edit=True)
    await callback.answer()


async def _ask_category(message: Message, state: FSMContext, tg_id: int, *, edit: bool) -> None:
    data = await state.get_data()
    tx_type = data["transaction_type"]
    try:
        categories = await client.get_categories(tg_id)
    except ApiError:
        categories = []
    # Категории нужного типа (income/expense)
    relevant = [c for c in categories if c.get("category_type") == tx_type]
    await state.set_state(AddTransaction.choosing_category)
    text = "Выберите категорию:"
    if edit:
        await message.edit_text(text, reply_markup=categories_kb(relevant))
    else:
        await message.answer(text, reply_markup=categories_kb(relevant))


@router.callback_query(AddTransaction.choosing_category, F.data.startswith("txcat:"))
async def choose_category(callback: CallbackQuery, state: FSMContext) -> None:
    cat_id = int(callback.data.split(":", 1)[1])
    await state.update_data(category_id=cat_id or None)
    await state.set_state(AddTransaction.entering_note)
    await callback.message.edit_text(
        "Добавьте описание или пропустите:", reply_markup=skip_note_kb()
    )
    await callback.answer()


@router.callback_query(AddTransaction.entering_note, F.data == "txnote:skip")
async def skip_note(callback: CallbackQuery, state: FSMContext) -> None:
    await _finish(callback.message, state, note=None, tg_id=callback.from_user.id, via_callback=True)
    await callback.answer()


@router.message(AddTransaction.entering_note)
async def enter_note(message: Message, state: FSMContext) -> None:
    await _finish(
        message, state, note=(message.text or "").strip(), tg_id=message.from_user.id, via_callback=False
    )


async def _finish(
    message: Message, state: FSMContext, *, note: str | None, tg_id: int, via_callback: bool
) -> None:
    data = await state.get_data()
    await state.clear()

    payload = {
        "transaction_type": data["transaction_type"],
        "amount": data["amount"],
        "currency": "RUB",
        "account_id": data["account_id"],
        "date": datetime.now(timezone.utc).isoformat(),
    }
    if data.get("category_id"):
        payload["category_id"] = data["category_id"]
    if note:
        payload["description"] = note

    try:
        tx = await client.create_transaction(tg_id, payload)
    except ApiError as e:
        error = f"❌ {esc(e.message)}"
        if via_callback:
            await message.edit_text(error)
        else:
            await message.answer(error)
        return

    title = _TYPE_TITLE.get(tx.get("transaction_type"), "Операция")
    confirmation = (
        f"✅ Добавлено!\n{title}: <b>{money(tx.get('amount', 0), tx.get('currency', 'RUB'))}</b>"
    )
    if via_callback:
        await message.edit_text(confirmation)
    else:
        await message.answer(confirmation, reply_markup=main_menu)
