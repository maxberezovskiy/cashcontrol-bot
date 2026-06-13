"""Точка входа Telegram-бота CashControl (long polling)."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from app.api_client import client
from app.config import settings
from app.handlers import accounts, common, transactions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("cashcontrol.bot")


BOT_COMMANDS = [
    BotCommand(command="balance", description="💰 Баланс по счетам"),
    BotCommand(command="add", description="➕ Добавить операцию"),
    BotCommand(command="last", description="🧾 Последние операции"),
    BotCommand(command="accounts", description="🏦 Счета"),
    BotCommand(command="link", description="🔗 Привязать аккаунт"),
    BotCommand(command="unlink", description="🚫 Отвязать аккаунт"),
    BotCommand(command="help", description="❓ Справка"),
]


async def main() -> None:
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(common.router)
    dp.include_router(accounts.router)
    dp.include_router(transactions.router)

    await bot.set_my_commands(BOT_COMMANDS)
    logger.info("Bot starting (backend=%s)", settings.BACKEND_URL)
    try:
        await dp.start_polling(bot)
    finally:
        await client.aclose()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
