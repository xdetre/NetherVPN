import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from app.config import settings
from app.database import init_db, async_session
from app.handlers import start, buy, profile, admin
from app.handlers.buy import yukassa_webhook
from app.services.scheduler import run_scheduler

logging.basicConfig(level=logging.INFO)


async def db_middleware(handler, event, data):
    async with async_session() as session:
        data["session"] = session
        return await handler(event, data)


async def main():
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(db_middleware)

    dp.include_router(start.router)
    dp.include_router(buy.router)
    dp.include_router(profile.router)
    dp.include_router(admin.router)

    await init_db()

    # aiohttp сервер для вебхука ЮКассы
    app = web.Application()
    app.router.add_post("/yukassa/webhook", yukassa_webhook)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()

    # Запуск планировщика
    asyncio.create_task(run_scheduler())

    try:
        logging.info("Nether VPN Bot запущен")
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())