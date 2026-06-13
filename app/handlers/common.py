"""Команды привязки и навигации: /start, /link, /help, /unlink."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.api_client import ApiError, NotLinkedError, client
from app.formatting import esc
from app.keyboards import main_menu

router = Router()


HELP_TEXT = (
    "<b>CashControl</b> — управление финансами прямо из Telegram.\n\n"
    "Доступные команды:\n"
    "💰 /balance — баланс по всем счетам\n"
    "🏦 /accounts — список счетов\n"
    "➕ /add — добавить доход или расход\n"
    "🧾 /last — последние операции\n"
    "🔗 /link &lt;код&gt; — привязать аккаунт\n"
    "🚫 /unlink — отвязать аккаунт\n"
    "❓ /help — эта справка"
)

LINK_HINT = (
    "Чтобы пользоваться ботом, привяжите аккаунт CashControl:\n\n"
    "1. Откройте веб-приложение → Настройки → «Подключить Telegram».\n"
    "2. Скопируйте одноразовый код.\n"
    "3. Отправьте сюда: <code>/link КОД</code>"
)


async def _do_link(message: Message, code: str) -> None:
    telegram_id = message.from_user.id
    try:
        user = await client.link(code=code, telegram_id=telegram_id)
    except ApiError as e:
        await message.answer(f"❌ {e.message}\n\n{LINK_HINT}")
        return
    name = esc(user.get("full_name") or user.get("email") or "пользователь")
    await message.answer(
        f"✅ Аккаунт привязан: <b>{name}</b>\n\nТеперь доступны все функции.",
        reply_markup=main_menu,
    )


@router.message(CommandStart(deep_link=True))
async def start_with_payload(message: Message, command: CommandObject, state: FSMContext) -> None:
    await state.clear()
    code = (command.args or "").strip()
    if code:
        await _do_link(message, code)
    else:
        await start(message, state)


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    if await client.is_linked(message.from_user.id):
        await message.answer(
            "С возвращением! 👋\nВыберите действие или используйте /help.",
            reply_markup=main_menu,
        )
    else:
        await message.answer(f"👋 Добро пожаловать в CashControl!\n\n{LINK_HINT}")


@router.message(Command("link"))
async def link_command(message: Message, command: CommandObject) -> None:
    code = (command.args or "").strip()
    if not code:
        await message.answer("Укажите код: <code>/link КОД</code>")
        return
    await _do_link(message, code)


@router.message(Command("unlink"))
async def unlink_command(message: Message) -> None:
    try:
        await client.unlink(message.from_user.id)
    except NotLinkedError:
        await message.answer("Аккаунт и так не привязан.")
        return
    except ApiError as e:
        await message.answer(f"❌ {e.message}")
        return
    await message.answer("✅ Аккаунт отвязан. Чтобы снова пользоваться ботом, выполните /link.")


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=main_menu)
