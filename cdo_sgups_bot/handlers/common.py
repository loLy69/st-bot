from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram import F
from aiogram.fsm.context import FSMContext

from database.db import get_user_by_telegram_id, create_user, update_user
from keyboards.student_kb import student_main_menu
from keyboards.parent_kb import parent_main_menu
from keyboards.teacher_kb import teacher_main_menu
from keyboards.admin_kb import admin_main_menu
from states.fsm import Registration
from utils.formatters import format_section
from config import config

router = Router()

@router.message(Command('start'))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user_by_telegram_id(message.from_user.id)
    if user and user.get('is_approved') == 1:
        return await message.answer(format_section('Меню', 'У вас уже есть доступ. Выберите раздел:'),
                                    reply_markup=select_menu_by_role(user.get('role', 'pending')))

    if user and user.get('is_approved') == 0:
        return await message.answer(format_section('Ожидание', 'Ваша заявка на рассмотрении, ожидайте'))

    await state.set_state(Registration.choose_role)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🎓 Я ученик', callback_data='role_student')],
        [InlineKeyboardButton(text='👨‍👩‍👧 Я родитель', callback_data='role_parent')],
        [InlineKeyboardButton(text='👨‍🏫 Я преподаватель', callback_data='role_teacher')]
    ])
    await message.answer(format_section('Регистрация', 'Выберите роль:'), reply_markup=keyboard)

@router.callback_query(F.data.startswith('role_'))
async def choose_role(query: CallbackQuery, state: FSMContext):
    role = query.data.split('_', 1)[1]
    await state.update_data(role=role)
    await state.set_state(Registration.enter_name)
    await query.message.answer(format_section('Регистрация', 'Введи своё полное имя (ФИО)'))
    await query.answer()

@router.message(Registration.enter_name)
async def enter_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await state.set_state(Registration.enter_phone)
    await message.answer(format_section('Регистрация', 'Введи номер телефона (или /skip)'))

@router.message(Command('skip'), Registration.enter_phone)
async def skip_phone(message: Message, state: FSMContext):
    await state.update_data(phone='')
    data = await state.get_data()
    if data.get('role') == 'student':
        await state.set_state(Registration.enter_grade)
        return await message.answer(format_section('Регистрация', 'Введи свой класс или группу (например: 9А или ИС-23)'))
    await state.set_state(Registration.confirm)
    await message.answer(format_section('Регистрация', 'Подтвердите данные: /yes или /no'))

@router.message(Registration.enter_phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    data = await state.get_data()
    if data.get('role') == 'student':
        await state.set_state(Registration.enter_grade)
        return await message.answer(format_section('Регистрация', 'Введи свой класс или группу (например: 9А или ИС-23)'))
    await state.set_state(Registration.confirm)
    await message.answer(format_section('Регистрация', 'Подтвердите данные: /yes или /no'))

@router.message(Registration.enter_grade)
async def process_grade(message: Message, state: FSMContext):
    await state.update_data(grade_or_group=message.text)
    await state.set_state(Registration.confirm)
    await message.answer(format_section('Регистрация', 'Подтвердите данные: /yes или /no'))

@router.message(Command('yes'), Registration.confirm)
async def confirm_registration(message: Message, state: FSMContext):
    data = await state.get_data()
    role = data.get('role', 'pending')
    is_approved = 1 if role in ('student', 'parent') else 0
    await create_user(
        telegram_id=message.from_user.id,
        role=role,
        full_name=data.get('full_name', ''),
        phone=data.get('phone', ''),
        grade_or_group=data.get('grade_or_group', ''),
        is_approved=is_approved
    )

    if role == 'teacher':
        text = f"Новый преподаватель ожидает подтверждения: {data.get('full_name', '')}"
        for admin_id in config.admin_ids or []:
            try:
                await message.bot.send_message(admin_id, text)
            except Exception:
                pass

    await state.clear()
    if is_approved == 1:
        await message.answer(format_section('Меню', f"Добро пожаловать, {data.get('full_name', '')}. Выберите раздел:"),
                             reply_markup=select_menu_by_role(role))
    else:
        await message.answer(format_section('Ожидание', 'Ваша заявка отправлена на проверку.'))

@router.message(Command('no'), Registration.confirm)
async def cancel_registration(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(format_section('Регистрация', 'Начните заново: /start'))

@router.message(Command('menu'))
async def menu(message: Message):
    user = await get_user_by_telegram_id(message.from_user.id)
    if not user:
        return await message.answer(format_section('Регистрация', 'Нажмите /start'))
    if user.get('is_approved', 0) == 0:
        return await message.answer(format_section('Ожидание', 'Ваша заявка на рассмотрении, ожидайте'))
    await message.answer(format_section('Меню', 'Выберите раздел:'), reply_markup=select_menu_by_role(user.get('role', 'pending')))

@router.callback_query(F.data == 'main_menu')
async def callback_main_menu(query: CallbackQuery):
    user = await get_user_by_telegram_id(query.from_user.id)
    if not user or user.get('is_approved', 0) == 0:
        await query.message.answer(format_section('Ожидание', 'Ваша заявка на рассмотрении, ожидайте'))
        await query.answer()
        return
    await query.message.answer(format_section('Меню', 'Выберите раздел:'), reply_markup=select_menu_by_role(user.get('role', 'pending')))
    await query.answer()


def select_menu_by_role(role: str):
    if role == 'student':
        return student_main_menu()
    if role == 'parent':
        return parent_main_menu()
    if role == 'teacher':
        return teacher_main_menu()
    if role == 'admin':
        return admin_main_menu()
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Регистрация', callback_data='role_student')]])
