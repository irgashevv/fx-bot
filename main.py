import asyncio
import logging
from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from db.database import create_tables
from handlers import user_commands, request_handlers

logging.basicConfig(level=logging.INFO)


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(user_commands.router)
    dp.include_router(request_handlers.fsm_router)

    print("Starting bot...")

    await create_tables()

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped.")
