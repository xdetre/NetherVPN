from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💳 Купить подписку", callback_data="buy"))
    builder.row(InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile"))
    builder.row(InlineKeyboardButton(text="🔗 Реферальная ссылка", callback_data="referral"))
    builder.row(InlineKeyboardButton(text="📱 Как подключиться", callback_data="howto"))
    return builder.as_markup()


def trial_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🎁 Начать пробный период (30 дней)", callback_data="start_trial"))
    builder.row(InlineKeyboardButton(text="💳 Купить подписку", callback_data="buy"))
    return builder.as_markup()


def buy_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="1 месяц — $1", callback_data="buy_1"))
    builder.row(InlineKeyboardButton(text="3 месяца — $2.5", callback_data="buy_3"))
    builder.row(InlineKeyboardButton(text="6 месяцев — $5", callback_data="buy_6"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_main"))
    return builder.as_markup()


def payment_kb(months: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⭐ Telegram Stars", callback_data=f"pay_stars_{months}"))
    builder.row(InlineKeyboardButton(text="💳 Банковская карта (ЮКасса)", callback_data=f"pay_yukassa_{months}"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="buy"))
    return builder.as_markup()


def profile_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📥 Получить конфиг", callback_data="config"))
    builder.row(InlineKeyboardButton(text="◀️ Главное меню", callback_data="back_main"))
    return builder.as_markup()


def back_main_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Главное меню", callback_data="back_main"))
    return builder.as_markup()
