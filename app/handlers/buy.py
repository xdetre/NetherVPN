from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery, InlineKeyboardMarkup, \
    InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.subscription import create_paid_subscription, get_or_create_user
from app.keyboards.inline import buy_kb, payment_kb, back_main_kb, main_menu_kb
from app.services.cbr import get_usd_rub_rate

import uuid, yookassa
from yookassa import Payment as YKPayment
from app.config import settings

from aiohttp import web

from app.utils import safe_edit

router = Router()

PLANS = {
    1: {"usd": 1.0, "stars": 50, "label": "1 месяц"},
    3: {"usd": 2.5, "stars": 125, "label": "3 месяца"},
    6: {"usd": 5.0, "stars": 250, "label": "6 месяцев"},
}


@router.message(Command("buy"))
@router.callback_query(F.data == "buy")
async def buy(update: Message | CallbackQuery):
    rate = await get_usd_rub_rate()
    text = (
        "💳 <b>Выбери план подписки:</b>\n\n"
        f"1 месяц — <b>$1</b> / 50 ⭐ (~{round(1.0 * rate)}₽)\n"
        f"3 месяца — <b>$2.5</b> / 125 ⭐ (~{round(2.5 * rate)}₽)\n"
        f"6 месяцев — <b>$5</b> / 250 ⭐ (~{round(5.0 * rate)}₽)\n\n"
        "🌍 Сервер: <b>Финляндия</b>\n"
        "🔒 Протокол: <b>AmneziaWG</b>\n"
        "💱 Цена в рублях по курсу ЦБ РФ"
    )
    if isinstance(update, CallbackQuery):
        await update.message.edit_text(text, reply_markup=buy_kb(), parse_mode="HTML")
    else:
        await update.answer(text, reply_markup=buy_kb(), parse_mode="HTML")


@router.callback_query(F.data.startswith("buy_"))
async def buy_plan(callback: CallbackQuery):
    months = int(callback.data.split("_")[1])
    plan = PLANS[months]
    rate = await get_usd_rub_rate()
    rub = round(plan["usd"] * rate)
    text = (
        f"📦 <b>{plan['label']}</b>\n\n"
        f"Стоимость: <b>${plan['usd']}</b> / <b>{plan['stars']} ⭐ Stars</b>\n"
        f"В рублях: <b>~{rub}₽</b> (курс ЦБ: {rate:.2f} ₽/$)\n\n"
        f"Выбери способ оплаты:"
    )
    await safe_edit(callback.message, text, reply_markup=payment_kb(months))


@router.callback_query(F.data.startswith("pay_stars_"))
async def pay_stars(callback: CallbackQuery):
    months = int(callback.data.split("_")[2])
    plan = PLANS[months]

    await callback.message.delete()

    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"Nether VPN — {plan['label']}",
        description=f"Подписка на {plan['label']}, сервер Финляндия, протокол AmneziaWG",
        payload=f"sub_{months}",
        currency="XTR",
        prices=[LabeledPrice(label=plan["label"], amount=plan["stars"])],
        provider_token=""
    )
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message, session: AsyncSession):
    payment = message.successful_payment
    months = int(payment.invoice_payload.split("_")[1])
    plan = PLANS[months]

    user, _ = await get_or_create_user(
        session=session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )

    sub = await create_paid_subscription(
        session=session,
        user=user,
        months=months,
        amount=plan["usd"],
        currency="XTR",
        telegram_payment_id=payment.telegram_payment_charge_id
    )

    if sub:
        await message.answer(
            f"✅ <b>Оплата прошла успешно!</b>\n\n"
            f"📦 План: <b>{plan['label']}</b>\n"
            f"📅 Действует до: <b>{sub.expires_at.strftime('%d.%m.%Y')}</b>\n\n"
            f"Получи конфиг командой /config",
            reply_markup=main_menu_kb(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "⚠️ Оплата прошла но что-то пошло не так при активации. "
            "Напиши в поддержку — разберёмся.",
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("pay_yukassa_"))
async def pay_yukassa(callback: CallbackQuery):
    months = int(callback.data.split("_")[2])
    plan = PLANS[months]

    rate = await get_usd_rub_rate()
    rub = round(plan["usd"] * rate, 2)

    yookassa.Configuration.account_id = settings.YUKASSA_SHOP_ID
    yookassa.Configuration.secret_key = settings.YUKASSA_SECRET_KEY

    payment = YKPayment.create({
        "amount": {
            "value": f"{rub:.2f}",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": f"https://t.me/{(await callback.bot.get_me()).username}"
        },
        "capture": True,
        "description": f"Nether VPN — {plan['label']}",
        "metadata": {
            "user_id": callback.from_user.id,
            "months": months
        }
    }, str(uuid.uuid4()))

    await callback.message.delete()
    await callback.bot.send_message(
        chat_id=callback.from_user.id,
        text=(
            f"💳 <b>Оплата через ЮКассу</b>\n\n"
            f"План: <b>{plan['label']}</b>\n"
            f"Сумма: <b>{rub:.2f}₽</b> (${plan['usd']} по курсу ЦБ)\n\n"
            f"Нажми кнопку ниже для оплаты:"
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="💳 Перейти к оплате",
                url=payment.confirmation.confirmation_url
            )
        ]]),
        parse_mode="HTML"
    )
    await callback.answer()


async def yukassa_webhook(request: web.Request) -> web.Response:
    data = await request.json()

    if data.get("event") != "payment.succeeded":
        return web.Response(status=200)

    payment_obj = data.get("object", {})
    metadata = payment_obj.get("metadata", {})
    user_id = int(metadata.get("user_id", 0))
    months = int(metadata.get("months", 1))
    payment_id = payment_obj.get("id", "")
    amount = float(payment_obj.get("amount", {}).get("value", 0))

    if not user_id:
        return web.Response(status=200)

    plan = PLANS[months]

    from app.database import async_session
    from app.services.subscription import get_or_create_user, create_paid_subscription

    async with async_session() as session:
        from aiogram import Bot
        from app.config import settings as cfg
        bot = Bot(token=cfg.BOT_TOKEN)

        user, _ = await get_or_create_user(
            session=session,
            telegram_id=user_id,
            username=None,
            full_name="",
        )
        sub = await create_paid_subscription(
            session=session,
            user=user,
            months=months,
            amount=amount,
            currency="RUB",
            telegram_payment_id=payment_id
        )
        if sub:
            await bot.send_message(
                chat_id=user_id,
                text=(
                    f"✅ <b>Оплата прошла успешно!</b>\n\n"
                    f"📦 План: <b>{plan['label']}</b>\n"
                    f"📅 Действует до: <b>{sub.expires_at.strftime('%d.%m.%Y')}</b>\n\n"
                    f"Получи конфиг командой /config"
                ),
                reply_markup=main_menu_kb(),
                parse_mode="HTML"
            )
        await bot.session.close()

    return web.Response(status=200)
