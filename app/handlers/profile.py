from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.services.subscription import (
    get_active_subscription,
    get_referral_count
)
from app.keyboards.inline import main_menu_kb, back_main_kb
from app.utils import safe_edit


router = Router()


def format_subscription_text(sub) -> str:
    days_left = (sub.expires_at - datetime.utcnow()).days
    return (
        f"✅ <b>Подписка активна</b>\n\n"
        f"📅 Действует до: <b>{sub.expires_at.strftime('%d.%m.%Y')}</b>\n"
        f"⏳ Осталось дней: <b>{days_left}</b>\n"
        f"📦 Трафик: <b>100 ГБ / месяц</b>\n"
    )


@router.message(Command("profile"))
@router.callback_query(F.data == "profile")
async def profile(update: Message | CallbackQuery, session: AsyncSession):
    user_id = update.from_user.id
    sub = await get_active_subscription(session, user_id)
    referrals = await get_referral_count(session, user_id)

    if sub:
        text = format_subscription_text(sub)
    else:
        text = "❌ <b>Подписка неактивна</b>\n\nКупи подписку чтобы пользоваться Nether VPN."

    text += f"\n👥 Приглашено друзей: <b>{referrals}</b>"

    if isinstance(update, CallbackQuery):
        await safe_edit(update.message, text, reply_markup=back_main_kb())
    else:
        await update.answer(text, reply_markup=back_main_kb(), parse_mode="HTML")


@router.message(Command("config"))
@router.callback_query(F.data == "config")
async def config(update: Message | CallbackQuery, session: AsyncSession):
    user_id = update.from_user.id
    sub = await get_active_subscription(session, user_id)

    if not sub:
        text = "❌ У тебя нет активной подписки.\n\nКупи подписку чтобы получить конфиг."
        if isinstance(update, CallbackQuery):
            await safe_edit(update.message, text, reply_markup=back_main_kb())
        else:
            await update.answer(text, reply_markup=back_main_kb(), parse_mode="HTML")
        return

    from aiogram.types import BufferedInputFile
    conf_bytes = sub.wg_config.encode()
    conf_file = BufferedInputFile(conf_bytes, filename="nether_vpn.conf")

    if isinstance(update, CallbackQuery):
        await update.message.answer_document(
            document=conf_file,
            caption="🔗 <b>Твой VPN конфиг</b>\n\nИмпортируй в Amnezia VPN.",
            parse_mode="HTML"
        )
        await update.answer()
    else:
        await update.answer_document(
            document=conf_file,
            caption="🔗 <b>Твой VPN конфиг</b>\n\nИмпортируй в Amnezia VPN.",
            parse_mode="HTML"
        )


@router.message(Command("referral"))
@router.callback_query(F.data == "referral")
async def referral(update: Message | CallbackQuery, session: AsyncSession):
    user_id = update.from_user.id
    referrals = await get_referral_count(session, user_id)
    bot = update.bot
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"

    text = (
        f"👥 <b>Реферальная программа</b>\n\n"
        f"Приглашай друзей и получай <b>+15 дней</b> за каждого кто оплатит подписку.\n\n"
        f"🔗 Твоя ссылка:\n<code>{ref_link}</code>\n\n"
        f"👤 Приглашено друзей: <b>{referrals}</b>"
    )

    if isinstance(update, CallbackQuery):
        await safe_edit(update.message, text, reply_markup=back_main_kb())
    else:
        await update.answer(text, reply_markup=back_main_kb(), parse_mode="HTML")