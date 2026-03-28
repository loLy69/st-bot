from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def admin_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📢 Рассылка", callback_data="broadcast"))
    builder.row(
        InlineKeyboardButton(text="👥 Ученики", callback_data="students"),
        InlineKeyboardButton(text="🎓 Курсы", callback_data="courses")
    )
    builder.row(
        InlineKeyboardButton(text="📅 Расписание", callback_data="schedule"),
        InlineKeyboardButton(text="💰 Платежи", callback_data="payments")
    )
    builder.row(
        InlineKeyboardButton(text="📰 Новости", callback_data="news"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="stats")
    )
    builder.row(InlineKeyboardButton(text="← Главное меню", callback_data="main_menu"))
    return builder.as_markup()
