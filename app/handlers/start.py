from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.subscription import (
    get_or_create_user,
    get_active_subscription,
    create_free_subscription
)
from app.keyboards.inline import main_menu_kb, back_main_kb
from app.utils import safe_edit
from app.config import settings

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession):
    args = message.text.split()
    referred_by = None

    if len(args) > 1:
        try:
            referred_by = int(args[1])
            if referred_by == message.from_user.id:
                referred_by = None
        except ValueError:
            pass

    user, is_new = await get_or_create_user(
        session=session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
        referred_by=referred_by
    )

    if is_new:
        await message.answer(
            f"👋 Добро пожаловать в <b>Nether VPN</b>!\n\n"
            f"⏳ Создаю твой VPN конфиг...",
            parse_mode="HTML"
        )

        sub = await create_free_subscription(session, user)

        if sub:
            conf_bytes = sub.wg_config.encode()
            conf_file = BufferedInputFile(conf_bytes, filename="nether_vpn.conf")

            await message.answer_document(
                document=conf_file,
                caption=(
                    f"✅ <b>Готово! Твой VPN активирован на {settings.FREE_DAYS} дней</b>\n\n"
                    f"📱 <b>Как подключиться:</b>\n"
                    f"1. Скачай <a href='https://apps.apple.com/app/amnezia-vpn/id1522739697'>Amnezia VPN</a>\n"
                    f"2. Нажми <b>+</b> → <b>Добавить конфигурацию</b>\n"
                    f"3. Выбери этот файл\n"
                    f"4. Нажми подключиться\n\n"
                    f"❓ Проблемы? Напиши в поддержку."
                ),
                parse_mode="HTML"
            )
            await message.answer(
                "Главное меню <b>Nether VPN</b>",
                reply_markup=main_menu_kb(),
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "⚠️ Что-то пошло не так при создании конфига. Напиши в поддержку.",
                parse_mode="HTML"
            )
    else:
        await message.answer(
            f"👋 С возвращением, <b>{user.full_name}</b>!\n\n"
            f"Используй меню ниже для управления подпиской.",
            reply_markup=main_menu_kb(),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery):
    await safe_edit(
        callback.message,
        "Главное меню <b>Nether VPN</b>",
        reply_markup=main_menu_kb()
    )


@router.callback_query(F.data == "howto")
async def howto(callback: CallbackQuery):
    text = (
        "📱 <b>Как подключиться:</b>\n\n"
        "<b>iOS:</b>\n"
        "1. Скачай <a href='https://apps.apple.com/app/amnezia-vpn/id1522739697'>Amnezia VPN</a>\n"
        "2. Нажми + → Добавить конфигурацию\n"
        "3. Выбери файл из бота\n\n"
        "<b>Android:</b>\n"
        "1. Скачай <a href='https://play.google.com/store/apps/details?id=org.amnezia.vpn'>Amnezia VPN</a>\n"
        "2. Нажми + → Добавить конфигурацию\n"
        "3. Выбери файл из бота\n\n"
        "<b>Windows/macOS:</b>\n"
        "1. Скачай <a href='https://amnezia.org'>Amnezia VPN</a>\n"
        "2. Добавь конфигурацию из файла\n\n"
        "❓ Проблемы? Напиши в поддержку."
    )
    await safe_edit(callback.message, text, reply_markup=back_main_kb())