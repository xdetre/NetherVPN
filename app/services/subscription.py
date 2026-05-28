from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import User, Subscription, Payment
from app.services.amnezia import create_client, delete_client
from app.config import settings


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    full_name: str,
    referred_by: int | None = None
) -> tuple[User, bool]:
    result = await session.execute(select(User).where(User.id == telegram_id))
    user = result.scalar_one_or_none()

    if user:
        return user, False

    user = User(
        id=telegram_id,
        username=username,
        full_name=full_name,
        referred_by=referred_by
    )
    session.add(user)
    await session.commit()
    return user, True


async def get_active_subscription(
    session: AsyncSession,
    user_id: int
) -> Subscription | None:
    result = await session.execute(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.is_active == True,
            Subscription.expires_at > datetime.utcnow()
        )
    )
    return result.scalar_one_or_none()


async def create_free_subscription(
    session: AsyncSession,
    user: User
) -> Subscription | None:
    conf = await create_client(user.id, user.username or str(user.id))
    if not conf:
        return None

    # Извлечь публичный ключ из конфига
    public_key = ""
    private_key = ""
    for line in conf.splitlines():
        if line.startswith("PrivateKey"):
            private_key = line.split("=", 1)[1].strip()

    # Получить публичный ключ из приватного
    import subprocess
    result = subprocess.run(
        f"echo '{private_key}' | docker exec -i amnezia-awg2 awg pubkey",
        shell=True, capture_output=True, text=True
    )
    public_key = result.stdout.strip()

    subscription = Subscription(
        user_id=user.id,
        wg_public_key=public_key,
        wg_config=conf,
        expires_at=datetime.utcnow() + timedelta(days=settings.FREE_DAYS),
    )
    session.add(subscription)
    await session.commit()
    return subscription


async def create_paid_subscription(
    session: AsyncSession,
    user: User,
    months: int,
    amount: float,
    currency: str,
    telegram_payment_id: str
) -> Subscription | None:
    days = months * 30

    existing = await get_active_subscription(session, user.id)

    if existing:
        existing.expires_at = datetime.utcnow() + timedelta(days=days)
        existing.is_active = True
        sub = existing
    else:
        conf = await create_client(user.id, user.username or str(user.id))
        if not conf:
            return None

        import subprocess
        private_key = ""
        for line in conf.splitlines():
            if line.startswith("PrivateKey"):
                private_key = line.split("=", 1)[1].strip()

        result = subprocess.run(
            f"echo '{private_key}' | docker exec -i amnezia-awg2 awg pubkey",
            shell=True, capture_output=True, text=True
        )
        public_key = result.stdout.strip()

        sub = Subscription(
            user_id=user.id,
            wg_public_key=public_key,
            wg_config=conf,
            expires_at=datetime.utcnow() + timedelta(days=days),
        )
        session.add(sub)

    payment = Payment(
        user_id=user.id,
        amount=amount,
        currency=currency,
        months=months,
        status="success",
        telegram_payment_id=telegram_payment_id
    )
    session.add(payment)
    await session.commit()

    if user.referred_by:
        await add_referral_bonus(session, user.referred_by)

    return sub


async def add_referral_bonus(
    session: AsyncSession,
    referrer_id: int
) -> None:
    sub = await get_active_subscription(session, referrer_id)
    if not sub:
        return
    sub.expires_at = sub.expires_at + timedelta(days=settings.REFERRAL_DAYS)
    await session.commit()


async def get_referral_count(
    session: AsyncSession,
    user_id: int
) -> int:
    result = await session.execute(
        select(User).where(User.referred_by == user_id)
    )
    return len(result.scalars().all())