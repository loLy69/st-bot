import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database.db import init_db
from handlers import common, student, parent, teacher, admin
from middlewares.role_check import RoleCheckMiddleware
from middlewares.throttling import ThrottlingMiddleware

logging.basicConfig(level=logging.INFO)

async def health(request):
    return web.Response(text="OK")

async def run_web():
    app = web.Application()
    app.router.add_get('/', health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

async def main():
    await init_db()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(ThrottlingMiddleware(rate_limit=10, time_window=10))
    dp.message.middleware(RoleCheckMiddleware())
    dp.callback_query.middleware(RoleCheckMiddleware())

    dp.include_router(common.router)
    dp.include_router(student.router)
    dp.include_router(parent.router)
    dp.include_router(teacher.router)
    dp.include_router(admin.router)

    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запускаем обе задачи одновременно
    await asyncio.gather(
        run_web(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
