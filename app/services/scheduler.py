import asyncio
import logging
from datetime import datetime
from sqlalchemy import select
from app.database import async_session
from app.models.models import Subscription
from app.services.amnezia import delete_client

logger = logging.getLogger(__name__)


async def cleanup_expired_subscriptions():
    """Удалить истёкшие подписки"""
    async with async_session() as session:
        result = await session.execute(
            select(Subscription).where(
                Subscription.is_active == True,
                Subscription.expires_at < datetime.utcnow()
            )
        )
        expired = result.scalars().all()

        for sub in expired:
            success = await delete_client(sub.wg_public_key)
            if success:
                sub.is_active = False
                logger.info(f"Деактивирована подписка user_id={sub.user_id}")
            else:
                logger.error(f"Ошибка деактивации user_id={sub.user_id}")

        await session.commit()


async def run_scheduler():
    """Запускать проверку каждый час"""
    while True:
        try:
            await cleanup_expired_subscriptions()
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        await asyncio.sleep(3600)