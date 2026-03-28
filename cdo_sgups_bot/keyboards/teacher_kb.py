from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def teacher_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="👥 Мои группы", callback_data="groups"))
    builder.row(
        InlineKeyboardButton(text="📝 ДЗ", callback_data="homework"),
        InlineKeyboardButton(text="📅 Расписание", callback_data="schedule")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Успеваемость", callback_data="progress"),
        InlineKeyboardButton(text="📤 Материалы", callback_data="materials")
    )
    builder.row(
        InlineKeyboardButton(text="💬 Написать группе", callback_data="message_group"),
        InlineKeyboardButton(text="🤖 ИИ", callback_data="ai_chat")
    )
    builder.row(InlineKeyboardButton(text="← Главное меню", callback_data="main_menu"))
    return builder.as_markup()
