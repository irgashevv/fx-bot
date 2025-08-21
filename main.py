import asyncio
import logging
from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from db.database import create_tables
from handlers import user_commands, converter_handlers, admin_handlers,request_handlers

logging.basicConfig(level=logging.INFO)


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    await create_tables()

    dp.include_router(admin_handlers.admin_router)
    dp.include_router(user_commands.router)
    dp.include_router(request_handlers.router)
    dp.include_router(converter_handlers.converter_router)

    print("Starting bot...")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped.")
