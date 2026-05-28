
from aiogram.exceptions import TelegramBadRequest

async def safe_edit(message, text, reply_markup=None, parse_mode="HTML"):
    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode, disable_web_page_preview=True)
    except TelegramBadRequest:
        pass