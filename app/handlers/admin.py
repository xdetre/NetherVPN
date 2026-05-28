from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.models import User, Subscription, Payment
from app.config import settings

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id == settings.ADMIN_ID


@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "🛠 <b>Админ панель Nether VPN</b>\n\n"
        "Команды:\n"
        "/stats — статистика\n"
        "/users — список пользователей\n"
        "/ban {user_id} — забанить\n"
        "/unban {user_id} — разбанить\n"
        "/addsub {user_id} {days} — добавить дни подписки",
        parse_mode="HTML"
    )


@router.message(Command("stats"))
async def stats(message: Message, session: AsyncSession):
    if not is_admin(message.from_user.id):
        return

    total_users = await session.scalar(select(func.count(User.id)))
    active_subs = await session.scalar(
        select(func.count(Subscription.id)).where(Subscription.is_active == True)
    )
    total_payments = await session.scalar(
        select(func.count(Payment.id)).where(Payment.status == "success")
    )

    await message.answer(
        f"📊 <b>Статистика Nether VPN</b>\n\n"
        f"👤 Всего пользователей: <b>{total_users}</b>\n"
        f"✅ Активных подписок: <b>{active_subs}</b>\n"
        f"💳 Успешных платежей: <b>{total_payments}</b>",
        parse_mode="HTML"
    )


@router.message(Command("ban"))
async def ban_user(message: Message, session: AsyncSession):
    if not is_admin(message.from_user.id):
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /ban {user_id}")
        return

    user_id = int(args[1])
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        await message.answer("Пользователь не найден.")
        return

    user.is_banned = True
    await session.commit()
    await message.answer(f"✅ Пользователь {user_id} забанен.")


@router.message(Command("unban"))
async def unban_user(message: Message, session: AsyncSession):
    if not is_admin(message.from_user.id):
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /unban {user_id}")
        return

    user_id = int(args[1])
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        await message.answer("Пользователь не найден.")
        return

    user.is_banned = False
    await session.commit()
    await message.answer(f"✅ Пользователь {user_id} разбанен.")


@router.message(Command("addsub"))
async def add_sub(message: Message, session: AsyncSession):
    if not is_admin(message.from_user.id):
        return

    args = message.text.split()
    if len(args) < 3:
        await message.answer("Использование: /addsub {user_id} {days}")
        return

    user_id = int(args[1])
    days = int(args[2])

    from datetime import timedelta
    from app.services.subscription import get_active_subscription
    from app.services.xui import xui_service

    sub = await get_active_subscription(session, user_id)
    if not sub:
        await message.answer("У пользователя нет активной подписки.")
        return

    from datetime import datetime
    sub.expires_at = sub.expires_at + timedelta(days=days)
    await xui_service.update_client_expiry(
        email=sub.xui_client_email,
        client_uuid=sub.xui_client_uuid,
        days=days
    )
    await session.commit()
    await message.answer(f"✅ Добавлено {days} дней пользователю {user_id}.")