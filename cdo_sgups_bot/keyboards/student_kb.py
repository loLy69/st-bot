from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def student_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📅 Записаться на курс", callback_data="enroll"))
    builder.row(
        InlineKeyboardButton(text="🗂 Кабинет", callback_data="cabinet"),
        InlineKeyboardButton(text="📚 ДЗ", callback_data="homework")
    )
    builder.row(
        InlineKeyboardButton(text="💳 Оплата", callback_data="payment"),
        InlineKeyboardButton(text="📰 Новости", callback_data="news")
    )
    builder.row(
        InlineKeyboardButton(text="✍️ Пробный урок", callback_data="trial"),
        InlineKeyboardButton(text="🤖 ИИ", callback_data="ai_chat")
    )
    builder.row(InlineKeyboardButton(text="🎓 Мой профиль", callback_data="profile"))
    return builder.as_markup()

def back_button() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="← Главное меню", callback_data="main_menu"))
    return builder.as_markup()
