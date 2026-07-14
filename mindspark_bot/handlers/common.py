import html

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove

from config import config
from database.db import ensure_user, get_user, set_user_fields
from keyboards.menus import back, buttons, main_menu
from states.fsm import Registration

router = Router(name='common')


async def show_menu(target: Message, telegram_id: int) -> None:
    user = await get_user(telegram_id)
    if not user or user['role'] == 'pending':
        await target.answer(
            f'Добро пожаловать в <b>{html.escape(config.school_name)}</b>!\n\n'
            'Здесь можно выбрать курс, записаться на занятие и следить за обучением.',
            reply_markup=buttons([[('Начать регистрацию', 'register')]]),
        )
        return
    await target.answer(
        f'<b>{html.escape(config.school_name)}</b> · Главное меню',
        reply_markup=main_menu(user['role'], bool(user['is_approved'])),
    )


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    tg = message.from_user
    await ensure_user(tg.id, tg.full_name or 'Пользователь', tg.username or '')
    if tg.id in config.admin_ids:
        await set_user_fields(tg.id, role='admin', is_approved=1)
    await show_menu(message, tg.id)


@router.message(Command('menu'))
async def menu_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await show_menu(message, message.from_user.id)


@router.callback_query(F.data == 'menu')
async def menu_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    await show_menu(callback.message, callback.from_user.id)


@router.callback_query(F.data == 'register')
async def register(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Registration.role)
    await callback.answer()
    await callback.message.answer('Кто вы?', reply_markup=buttons([
        [('🎓 Ученик', 'reg_role:student'), ('👨‍👩‍👧 Родитель', 'reg_role:parent')],
        [('👨‍🏫 Преподаватель', 'reg_role:teacher')],
    ]))


@router.callback_query(Registration.role, F.data.startswith('reg_role:'))
async def registration_role(callback: CallbackQuery, state: FSMContext) -> None:
    role = callback.data.split(':', 1)[1]
    if role not in {'student', 'parent', 'teacher'}:
        await callback.answer('Неизвестная роль', show_alert=True)
        return
    await state.update_data(role=role)
    await state.set_state(Registration.name)
    await callback.answer()
    await callback.message.answer('Введите имя и фамилию:')


@router.message(Registration.name, F.text)
async def registration_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if len(name) < 2 or len(name) > 100:
        await message.answer('Введите имя длиной от 2 до 100 символов.')
        return
    await state.update_data(full_name=name)
    await state.set_state(Registration.phone)
    await message.answer(
        'Отправьте номер телефона или нажмите «Пропустить».',
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text='📱 Отправить телефон', request_contact=True)], [KeyboardButton(text='Пропустить')]],
            resize_keyboard=True, one_time_keyboard=True,
        ),
    )


@router.message(Registration.phone)
async def registration_phone(message: Message, state: FSMContext) -> None:
    phone = message.contact.phone_number if message.contact else ('' if message.text == 'Пропустить' else (message.text or '').strip())
    if phone and (len(phone) < 7 or len(phone) > 25):
        await message.answer('Проверьте номер или нажмите «Пропустить».')
        return
    data = await state.get_data()
    role = data['role']
    approved = 0 if role == 'teacher' else 1
    await set_user_fields(message.from_user.id, full_name=data['full_name'], phone=phone, role=role, is_approved=approved)
    await state.clear()
    await message.answer('Регистрация завершена.' if approved else 'Заявка преподавателя отправлена администратору.', reply_markup=ReplyKeyboardRemove())
    await show_menu(message, message.from_user.id)


@router.callback_query(F.data == 'profile')
async def profile(callback: CallbackQuery) -> None:
    user = await get_user(callback.from_user.id)
    await callback.answer()
    if not user:
        return
    roles = {'student': 'Ученик', 'parent': 'Родитель', 'teacher': 'Преподаватель', 'admin': 'Администратор'}
    await callback.message.answer(
        f"<b>Профиль</b>\nИмя: {html.escape(user['full_name'])}\n"
        f"Роль: {roles.get(user['role'], user['role'])}\nТелефон: {html.escape(user['phone'] or 'не указан')}",
        reply_markup=back(),
    )


@router.callback_query(F.data == 'support')
async def support(callback: CallbackQuery) -> None:
    await callback.answer()
    text = f'Поддержка: @{config.support_username}' if config.support_username else 'Контакт поддержки пока не настроен.'
    await callback.message.answer(text, reply_markup=back())


@router.message(Command('cancel'))
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer('Действие отменено.', reply_markup=ReplyKeyboardRemove())
    await show_menu(message, message.from_user.id)
