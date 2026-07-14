import asyncio
import logging
import signal

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database.db import init_db
from handlers import admin, common, parent, student, teacher
from middlewares.role_check import RoleCheckMiddleware
from middlewares.throttling import ThrottlingMiddleware

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger(__name__)


async def health(_: web.Request) -> web.Response:
    return web.json_response({'status': 'ok', 'service': 'mindspark-bot'})


async def start_health_server() -> web.AppRunner:
    app = web.Application()
    app.router.add_get('/', health)
    app.router.add_get('/health', health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', config.port).start()
    return runner


async def main() -> None:
    config.validate()
    await init_db()
    bot = Bot(config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(RoleCheckMiddleware())
    dp.message.middleware(ThrottlingMiddleware(rate_limit=12, time_window=10))
    dp.include_routers(common.router, student.router, parent.router, teacher.router, admin.router)
    runner = await start_health_server()
    try:
        await bot.delete_webhook(drop_pending_updates=False)
        logger.info('MindSpark запущен')
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await runner.cleanup()
        await bot.session.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
