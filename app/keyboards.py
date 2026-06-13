"""Клавиатуры бота."""
from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

# Главное меню (постоянная нижняя клавиатура)
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить"), KeyboardButton(text="💰 Баланс")],
        [KeyboardButton(text="🧾 Операции"), KeyboardButton(text="🏦 Счета")],
    ],
    resize_keyboard=True,
)


def transaction_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔴 Расход", callback_data="txtype:expense"),
                InlineKeyboardButton(text="🟢 Доход", callback_data="txtype:income"),
            ],
            [InlineKeyboardButton(text="✖️ Отмена", callback_data="tx:cancel")],
        ]
    )


def accounts_kb(accounts: list[dict]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=acc["name"], callback_data=f"txacc:{acc['id']}")]
        for acc in accounts
    ]
    rows.append([InlineKeyboardButton(text="✖️ Отмена", callback_data="tx:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def categories_kb(categories: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    row: list[InlineKeyboardButton] = []
    for cat in categories:
        row.append(InlineKeyboardButton(text=cat["name"], callback_data=f"txcat:{cat['id']}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="⏭ Без категории", callback_data="txcat:0")])
    rows.append([InlineKeyboardButton(text="✖️ Отмена", callback_data="tx:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def skip_note_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Без описания", callback_data="txnote:skip")],
            [InlineKeyboardButton(text="✖️ Отмена", callback_data="tx:cancel")],
        ]
    )
