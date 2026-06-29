from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN missing in .env or Railway Variables")

NEW_BOT = "@TopupPrimeBot"
CLOSED_MESSAGE = (
    "تم قفل هذا البوت ونقل البوت إلى بوت جديد. البوت الجديد هنا: "
    f"{NEW_BOT}\n\n"
    "This bot has been closed and moved to a new bot. The new bot is here: "
    f"{NEW_BOT}"
)

session = AiohttpSession()
bot = Bot(BOT_TOKEN, session=session)
dp = Dispatcher()


async def send_closed_message(message: Message) -> None:
    await message.answer(CLOSED_MESSAGE, reply_markup=ReplyKeyboardRemove())


@dp.message()
async def catch_all_messages(message: Message) -> None:
    await send_closed_message(message)


@dp.callback_query()
async def catch_all_buttons(callback: CallbackQuery) -> None:
    try:
        await callback.answer("Bot moved to @TopupPrimeBot", show_alert=True)
    except Exception:
        pass

    if callback.message:
        await callback.message.answer(CLOSED_MESSAGE, reply_markup=ReplyKeyboardRemove())


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
