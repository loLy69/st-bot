from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def buttons(rows: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data=data) for text, data in row]
        for row in rows
    ])


def main_menu(role: str, approved: bool = True) -> InlineKeyboardMarkup:
    if not approved and role in {"teacher", "admin"}:
        return buttons([[('⏳ Обновить статус', 'menu')], [('🆘 Поддержка', 'support')]])
    menus = {
        'student': [
            [('📚 Курсы', 'courses'), ('📅 Расписание', 'my_schedule')],
            [('✅ Мои записи', 'my_bookings'), ('💳 Оплата', 'payments')],
            [('📝 Домашние задания', 'homework'), ('👤 Профиль', 'profile')],
        ],
        'parent': [
            [('👨‍👩‍👧 Мои дети', 'children'), ('📅 Расписание', 'family_schedule')],
            [('💳 Оплата', 'payments'), ('📢 Новости', 'news')],
        ],
        'teacher': [
            [('📅 Мои занятия', 'teacher_schedule'), ('👥 Ученики', 'teacher_students')],
            [('📝 Домашние задания', 'teacher_homework'), ('📢 Новости', 'news')],
        ],
        'admin': [
            [('👥 Пользователи', 'admin_users'), ('📚 Курсы', 'admin_courses')],
            [('📅 Занятия', 'admin_lessons'), ('💳 Платежи', 'admin_payments')],
            [('📊 Статистика', 'admin_stats'), ('📢 Рассылка', 'admin_broadcast')],
            [('🛠 Управление школой', 'admin_help')],
        ],
    }
    rows = menus.get(role, [[('📝 Регистрация', 'register')]])
    rows.append([('🆘 Поддержка', 'support')])
    return buttons(rows)


def back() -> InlineKeyboardMarkup:
    return buttons([[('← Главное меню', 'menu')]])
