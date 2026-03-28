from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def parent_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="👶 Мой ребёнок", callback_data="child"))
    builder.row(
        InlineKeyboardButton(text="📅 Расписание", callback_data="schedule"),
        InlineKeyboardButton(text="💳 Платежи", callback_data="payments")
    )
    builder.row(
        InlineKeyboardButton(text="📰 Новости", callback_data="news"),
        InlineKeyboardButton(text="🤖 ИИ-помощник", callback_data="ai_chat")
    )
    builder.row(InlineKeyboardButton(text="← Главное меню", callback_data="main_menu"))
    return builder.as_markup()
