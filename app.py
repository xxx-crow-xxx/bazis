import asyncio
import os

from cleanup_scheduler import setup_scheduler, cleanup_past_dates
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from dotenv import find_dotenv, load_dotenv

from common.commands import private
from middlewares.db import DataBaseSession
load_dotenv(find_dotenv())

from database.engine import create_db, drop_db, session_maker

from handlers.user_private import user_private_router

ALLOWED_UPDATES = ['message, edited_message']

bot = Bot(token=os.getenv('TOKEN'), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

dp.include_router(user_private_router)


async def on_startup():
    await setup_scheduler(bot)
    await cleanup_past_dates(bot)

    run_param = False
    if run_param:
        await drop_db()

    await create_db()


async def on_shutdown(bot):
    print('бот лёг')


async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    dp.update.middleware(DataBaseSession(session_pool=session_maker))
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands(commands=private, scope=types.BotCommandScopeAllPrivateChats())
    await dp.start_polling(bot, allowed_updates=ALLOWED_UPDATES)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('exit')