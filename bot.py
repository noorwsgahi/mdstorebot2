from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from dotenv import load_dotenv

from config import config

load_dotenv()
logging.basicConfig(level=logging.INFO)

router = Router()

CLOSED_MESSAGE = (
    "تم قفل البوت ونقل البوت، البوت الجديد هنا: @TopupPrimeBot\n\n"
    "The bot has been closed and moved. The new bot is here: @TopupPrimeBot"
)


@router.message(CommandStart())
async def start_redirect(message: Message) -> None:
    await message.answer(CLOSED_MESSAGE)


@router.message()
async def any_message_redirect(message: Message) -> None:
    await message.answer(CLOSED_MESSAGE)


@router.callback_query()
async def any_button_redirect(call: CallbackQuery) -> None:
    await call.answer()
    if call.message:
        await call.message.answer(CLOSED_MESSAGE)


async def main() -> None:
    if not config.bot_token:
        raise RuntimeError("BOT_TOKEN is missing. Please set it in .env")

    bot = Bot(
        config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
