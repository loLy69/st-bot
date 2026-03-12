import os
import asyncio
import sqlite3
import random
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from groq import Groq

# ===== КОНФИГУРАЦИЯ =====
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
ADMIN_ID = 1081321560

# ===== ИНИЦИАЛИЗАЦИЯ =====
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# ===== СОСТОЯНИЯ FSM =====
class BookingStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_date = State()
    waiting_for_time = State()

class TrialStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_time = State()

class NewsletterStates(StatesGroup):
    waiting_for_text = State()

class HomeworkSubmitStates(StatesGroup):
    waiting_for_answer = State()

class PaymentStates(StatesGroup):
    waiting_for_receipt = State()

class ReviewStates(StatesGroup):
    waiting_for_text = State()

class AIStates(StatesGroup):
    waiting_for_question = State()

class AdminStates(StatesGroup):
    waiting_for_hw = State()
    waiting_for_newsletter_filter = State()
    waiting_for_newsletter_text = State()

# ===== БАЗА ДАННЫХ =====
def init_db():
    conn = sqlite3.connect('mindspark.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            name TEXT,
            day TEXT,
            time TEXT,
            date TEXT,
            reminder_sent INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Добавляем колонку date если она не существует
    try:
        cursor.execute("ALTER TABLE bookings ADD COLUMN date TEXT")
    except sqlite3.OperationalError:
        pass  # Колонка уже существует

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            name TEXT,
            lessons_completed INTEGER DEFAULT 0,
            coffee_beans INTEGER DEFAULT 0,
            progress_percentage INTEGER DEFAULT 0,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS homework (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS homework_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            homework_id INTEGER,
            content TEXT,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            tariff TEXT,
            status TEXT DEFAULT 'pending',
            receipt_file_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            confirmed_at TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            review_text TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ БД =====
def register_student(user_id, username, name):
    conn = sqlite3.connect('mindspark.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO students (user_id, username, name)
        VALUES (?, ?, ?)
    ''', (user_id, username, name))
    conn.commit()
    conn.close()

def save_booking(user_id, username, name, date, time):
    conn = sqlite3.connect('mindspark.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO bookings (user_id, username, name, date, time)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, username, name, date, time))
    conn.commit()
    conn.close()

def get_bookings_for_days(days=3):
    conn = sqlite3.connect('mindspark.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT name, date, time, created_at FROM bookings
        ORDER BY created_at DESC LIMIT 20
    ''')
    result = cursor.fetchall()
    conn.close()
    return result

def get_student_progress(user_id):
    conn = sqlite3.connect('mindspark.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT lessons_completed, coffee_beans, progress_percentage
        FROM students WHERE user_id = ?
    ''', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result or (0, 0, 0)

def add_coffee_bean(user_id):
    conn = sqlite3.connect('mindspark.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE students SET coffee_beans = coffee_beans + 1
        WHERE user_id = ?
    ''', (user_id,))
    conn.commit()
    conn.close()

def get_active_homework():
    conn = sqlite3.connect('mindspark.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, description FROM homework
        WHERE is_active = 1 ORDER BY created_at DESC LIMIT 1
    ''')
    result = cursor.fetchone()
    conn.close()
    return result

def get_user_materials(user_id):
    conn = sqlite3.connect('mindspark.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, content FROM materials
        WHERE user_id = ? ORDER BY created_at DESC
    ''', (user_id,))
    result = cursor.fetchall()
    conn.close()
    return result

def get_all_students():
    conn = sqlite3.connect('mindspark.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT user_id, name, lessons_completed, coffee_beans FROM students
    ''')
    result = cursor.fetchall()
    conn.close()
    return result

def get_monthly_stats():
    conn = sqlite3.connect('mindspark.db')
    cursor = conn.cursor()
    month = datetime.now().strftime('%Y-%m')
    cursor.execute('''
        SELECT COUNT(*) FROM bookings
        WHERE strftime('%Y-%m', created_at) = ?
    ''', (month,))
    lessons = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM students')
    students = cursor.fetchone()[0]
    conn.close()
    return lessons, students

def create_payment(user_id, amount, tariff):
    conn = sqlite3.connect('mindspark.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO payments (user_id, amount, tariff)
        VALUES (?, ?, ?)
    ''', (user_id, amount, tariff))
    conn.commit()
    pid = cursor.lastrowid
    conn.close()
    return pid

def save_receipt(payment_id, file_id):
    conn = sqlite3.connect('mindspark.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE payments SET receipt_file_id = ?, status = 'receipt_sent'
        WHERE id = ?
    ''', (file_id, payment_id))
    conn.commit()
    conn.close()

def get_last_payment(user_id):
    conn = sqlite3.connect('mindspark.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, amount, tariff FROM payments
        WHERE user_id = ? ORDER BY created_at DESC LIMIT 1
    ''', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def confirm_payment_db(payment_id):
    conn = sqlite3.connect('mindspark.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE payments SET status = 'confirmed', confirmed_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (payment_id,))
    conn.commit()
    conn.close()

def save_review(user_id, name, text):
    conn = sqlite3.connect('mindspark.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO reviews (user_id, name, review_text)
        VALUES (?, ?, ?)
    ''', (user_id, name, text))
    conn.commit()
    rid = cursor.lastrowid
    conn.close()
    return rid

def get_approved_reviews():
    conn = sqlite3.connect('mindspark.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT name, review_text FROM reviews
        WHERE status = 'approved' ORDER BY created_at DESC LIMIT 5
    ''')
    result = cursor.fetchall()
    conn.close()
    return result

def approve_review_db(review_id):
    conn = sqlite3.connect('mindspark.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE reviews SET status = 'approved' WHERE id = ?
    ''', (review_id,))
    conn.commit()
    conn.close()

# ===== КЛАВИАТУРЫ =====
def main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="� Записаться на урок"))
    builder.add(KeyboardButton(text="✨ Пробный урок"))
    builder.add(KeyboardButton(text="🌿 Мой кабинет"))
    builder.add(KeyboardButton(text="🪙 Оплата"))
    builder.add(KeyboardButton(text="� Вопросы и ответы"))
    builder.add(KeyboardButton(text="📜 Отзывы"))
    builder.add(KeyboardButton(text="💡 Спросить ИИ"))
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup(resize_keyboard=True)

MENU_BUTTONS = [
    "� Записаться на урок", "✨ Пробный урок", "🕯 Вопросы и ответы",
    "🌿 Мой кабинет", "🪙 Оплата", "📜 Отзывы", "💡 Спросить ИИ"
]

# ===== СТАРТ =====
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    register_student(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.first_name or "Ученик"
    )
    text = (
        "🌿 Добро пожаловать в MindSpark!\n\n"
        "Здесь знания растут как дерево —\n"
        "корень за корнем, лист за листом 🌱\n\n"
        "Устраивайся поудобнее ☕\n"
        "С чего начнём?"
    )
    try:
        photo = FSInputFile("welcome.png")
        await message.answer_photo(
            photo=photo,
            caption=text,
            reply_markup=main_keyboard()
        )
    except Exception as e:
        print(f"Ошибка отправки фото: {e}")
        await message.answer(text, reply_markup=main_keyboard())

# ===== ЗАПИСЬ НА УРОК =====
@dp.message(F.text == "� Записаться на урок")
async def booking_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(BookingStates.waiting_for_name)
    await message.answer("📝 Как тебя зовут?")

@dp.message(BookingStates.waiting_for_name)
async def booking_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(BookingStates.waiting_for_date)
    await message.answer("📅 Напиши дату урока в формате ДД.ММ.ГГГГ\nНапример: 25.03.2026")

@dp.message(BookingStates.waiting_for_date)
async def booking_date(message: Message, state: FSMContext):
    try:
        # Проверяем формат даты
        datetime.strptime(message.text, "%d.%m.%Y")
        await state.update_data(date=message.text)
        await state.set_state(BookingStates.waiting_for_time)
        
        builder = InlineKeyboardBuilder()
        for time in ["10:00", "12:00", "14:00", "16:00", "18:00"]:
            builder.add(InlineKeyboardButton(text=time, callback_data=f"time_{time}"))
        builder.adjust(3)
        await message.answer("� Выбери удобное время:", reply_markup=builder.as_markup())
        
    except ValueError:
        await message.answer("❌ Неверный формат. Напиши например: 25.03.2026")

@dp.callback_query(BookingStates.waiting_for_time, F.data.startswith("time_"))
async def booking_time(callback: CallbackQuery, state: FSMContext):
    time = callback.data.replace("time_", "")
    data = await state.get_data()
    name = data['name']
    date = data['date']
    await state.clear()

    save_booking(
        callback.from_user.id,
        callback.from_user.username or "",
        name, date, time
    )

    await callback.message.edit_text(
        f"✅ <b>Готово!</b>\n\n"
        f"Ждём тебя <b>{date}</b> в <b>{time}</b> ☕\n"
        f"Не забудь тетрадку!"
    )

    await bot.send_message(
        ADMIN_ID,
        f"☕ <b>Новая запись!</b>\n\n"
        f"👤 Имя: {name}\n"
        f"📅 Дата: {date}\n"
        f"🕐 Время: {time}\n"
        f"🆔 ID: {callback.from_user.id}"
    )

# ===== ПРОБНЫЙ УРОК =====
@dp.message(F.text == "✨ Пробный урок")
async def trial_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(TrialStates.waiting_for_name)
    await message.answer("👋 Отлично! Как тебя зовут?")

@dp.message(TrialStates.waiting_for_name)
async def trial_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(TrialStates.waiting_for_time)
    await message.answer("🕐 В какое время тебе удобно? Напиши, например: вторник в 15:00")

@dp.message(TrialStates.waiting_for_time)
async def trial_time(message: Message, state: FSMContext):
    data = await state.get_data()
    name = data['name']
    time = message.text
    await state.clear()

    await message.answer(
        "🌟 <b>Заявка принята!</b>\n\n"
        "Напишу тебе лично чтобы согласовать детали ✨"
    )

    await bot.send_message(
        ADMIN_ID,
        f"🌟 <b>Заявка на пробный урок!</b>\n\n"
        f"👤 Имя: {name}\n"
        f"🕐 Время: {time}\n"
        f"🆔 ID: {message.from_user.id}"
    )

# ===== FAQ =====
@dp.message(F.text == "🕯 Вопросы и ответы")
async def faq_menu(message: Message, state: FSMContext):
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="💰 Сколько стоит урок?", callback_data="faq_price"))
    builder.add(InlineKeyboardButton(text="💻 Как проходят уроки?", callback_data="faq_format"))
    builder.add(InlineKeyboardButton(text="💳 Как оплатить?", callback_data="faq_payment"))
    builder.adjust(1)
    await message.answer("❓ <b>Частые вопросы:</b>", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "faq_price")
async def faq_price(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="faq_back"))
    await callback.message.edit_text(
        "💰 <b>Стоимость:</b>\n\n"
        "⚡ Разовый урок — 1500₽\n"
        "📚 Абонемент 4 урока — 5500₽\n"
        "🔥 Абонемент 8 уроков — 10000₽",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data == "faq_format")
async def faq_format(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="faq_back"))
    await callback.message.edit_text(
        "💻 <b>Формат уроков:</b>\n\n"
        "Онлайн в Zoom или Google Meet\n"
        "Длительность: 60 минут\n"
        "Все материалы остаются у тебя ☕",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data == "faq_payment")
async def faq_payment_info(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="faq_back"))
    await callback.message.edit_text(
        "💳 <b>Оплата:</b>\n\n"
        "Переводом на карту или СБП\n"
        "После урока или по абонементу 📲",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data == "faq_back")
async def faq_back(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="💰 Сколько стоит урок?", callback_data="faq_price"))
    builder.add(InlineKeyboardButton(text="💻 Как проходят уроки?", callback_data="faq_format"))
    builder.add(InlineKeyboardButton(text="💳 Как оплатить?", callback_data="faq_payment"))
    builder.adjust(1)
    await callback.message.edit_text("❓ <b>Частые вопросы:</b>", reply_markup=builder.as_markup())

# ===== МОЙ КАБИНЕТ =====
@dp.message(F.text == "🌿 Мой кабинет")
async def cabinet_menu(message: Message, state: FSMContext):
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📖 Мои материалы", callback_data="cab_materials"))
    builder.add(InlineKeyboardButton(text="📝 Домашнее задание", callback_data="cab_hw"))
    builder.add(InlineKeyboardButton(text="📈 Мой прогресс", callback_data="cab_progress"))
    builder.add(InlineKeyboardButton(text="☕ Уютный уголок", callback_data="cab_cozy"))
    builder.adjust(2)
    await message.answer("📚 <b>Личный кабинет</b>\n\nЧто открываем?", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "cab_materials")
async def cab_materials(callback: CallbackQuery):
    materials = get_user_materials(callback.from_user.id)
    if not materials:
        text = "📖 <b>Мои материалы</b>\n\nПока пусто — материалы появятся после уроков ☕"
    else:
        text = "📖 <b>Мои материалы:</b>\n\n"
        for mid, title, content in materials:
            text += f"• <b>{title}</b>\n  {content}\n\n"
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="cab_back"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup())

@dp.callback_query(F.data == "cab_hw")
async def cab_hw(callback: CallbackQuery, state: FSMContext):
    hw = get_active_homework()
    if not hw:
        text = "📝 <b>Домашнее задание</b>\n\nПока заданий нет ☕"
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="cab_back"))
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        return

    hw_id, title, description = hw
    await state.update_data(hw_id=hw_id)
    await state.set_state(HomeworkSubmitStates.waiting_for_answer)

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔙 Отмена", callback_data="cab_back"))
    await callback.message.edit_text(
        f"📝 <b>{title}</b>\n\n{description}\n\n"
        "Отправь своё решение текстом или фото 👇",
        reply_markup=builder.as_markup()
    )

@dp.message(HomeworkSubmitStates.waiting_for_answer)
async def hw_submit(message: Message, state: FSMContext):
    data = await state.get_data()
    hw_id = data.get('hw_id', 0)
    await state.clear()

    if message.photo:
        content = message.photo[-1].file_id
        content_type = "фото"
    else:
        content = message.text
        content_type = "текст"

    add_coffee_bean(message.from_user.id)
    lessons, coffee, percentage = get_student_progress(message.from_user.id)

    await message.answer(
        f"✅ <b>ДЗ принято!</b>\n\n"
        f"Ты заработал +1 кофейное зерно ☕\n"
        f"Всего зёрен: {coffee + 1}",
        reply_markup=main_keyboard()
    )

    await bot.send_message(
        ADMIN_ID,
        f"📝 <b>Сдано ДЗ!</b>\n\n"
        f"👤 {message.from_user.full_name}\n"
        f"🆔 {message.from_user.id}\n"
        f"📄 Тип: {content_type}"
    )

    if message.photo:
        await bot.send_photo(ADMIN_ID, message.photo[-1].file_id)

@dp.callback_query(F.data == "cab_progress")
async def cab_progress(callback: CallbackQuery):
    lessons, coffee, percentage = get_student_progress(callback.from_user.id)
    filled = int(percentage / 10)
    bar = "▓" * filled + "░" * (10 - filled)
    bonus = "\n\n🎉 <b>Поздравляем! Ты заработал бонус!</b>" if coffee >= 10 else ""
    text = (
        f"📈 <b>Мой прогресс</b>\n\n"
        f"{bar} {percentage}%\n\n"
        f"📚 Уроков пройдено: {lessons}\n"
        f"☕ Кофейных зёрен: {coffee}{bonus}"
    )
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="cab_back"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup())

@dp.callback_query(F.data == "cab_cozy")
async def cab_cozy(callback: CallbackQuery):
    quotes = [
        "💡 «Учись так, словно тебе не хватает времени»",
        "☕ «Отдых так же важен, как и работа»",
        "🎯 «Фокус на цели, наслаждайся процессом»",
        "🌈 «Ошибка — это просто шаг к успеху»",
        "⭐ «Ты способен на большее, чем думаешь»",
        "🚀 «Начни с того, что у тебя уже есть»",
        "💪 «Сила — в последовательности»",
    ]
    playlists = [
        "🎵 <a href='https://youtube.com/playlist?list=PLbpi6ZahtOH6Ar_3GPy3workUGBCF-PoS'>Lo-fi для учёбы</a>",
        "🎵 <a href='https://youtube.com/watch?v=jfKfPfyJRdk'>Lofi Hip Hop Radio</a>",
        "🎵 <a href='https://youtube.com/watch?v=5qap5aO4i9A'>Lofi Girl — Chill</a>",
    ]
    quote = random.choice(quotes)
    playlist_text = "\n".join(playlists)
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="⏱ Помодоро 25 мин", callback_data="timer_25"))
    builder.add(InlineKeyboardButton(text="⏱ Перерыв 5 мин", callback_data="timer_5"))
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="cab_back"))
    builder.adjust(2)
    await callback.message.edit_text(
        f"☕ <b>Уютный уголок</b>\n\n"
        f"{quote}\n\n"
        f"<b>Плейлисты для учёбы:</b>\n{playlist_text}",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data.startswith("timer_"))
async def timer_start(callback: CallbackQuery):
    minutes = int(callback.data.replace("timer_", ""))
    await callback.answer(f"⏱ Таймер на {minutes} минут запущен!")
    await callback.message.edit_text(
        f"⏱ <b>Таймер запущен!</b>\n\n"
        f"Фокусируйся {minutes} минут ⚡\n"
        f"Я напомню когда время выйдет!"
    )
    asyncio.create_task(timer_task(callback.from_user.id, minutes))

async def timer_task(user_id, minutes):
    await asyncio.sleep(minutes * 60)
    await bot.send_message(
        user_id,
        f"⏰ <b>Время вышло!</b>\n\nМолодец! Заслужил перерыв ☕",
        reply_markup=main_keyboard()
    )

@dp.callback_query(F.data == "cab_back")
async def cab_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📖 Мои материалы", callback_data="cab_materials"))
    builder.add(InlineKeyboardButton(text="📝 Домашнее задание", callback_data="cab_hw"))
    builder.add(InlineKeyboardButton(text="📈 Мой прогресс", callback_data="cab_progress"))
    builder.add(InlineKeyboardButton(text="☕ Уютный уголок", callback_data="cab_cozy"))
    builder.adjust(2)
    await callback.message.edit_text(
        "📚 <b>Личный кабинет</b>\n\nЧто открываем?",
        reply_markup=builder.as_markup()
    )

# ===== ОПЛАТА =====
@dp.message(F.text == "🪙 Оплата")
async def payment_menu(message: Message, state: FSMContext):
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="⚡ Разовый — 1500₽", callback_data="pay_1500_разовый"))
    builder.add(InlineKeyboardButton(text="📚 Абонемент 4 — 5500₽", callback_data="pay_5500_абонемент4"))
    builder.add(InlineKeyboardButton(text="🔥 Абонемент 8 — 10000₽", callback_data="pay_10000_абонемент8"))
    builder.adjust(1)
    await message.answer(
        "💳 <b>Выбери тариф:</b>\n\n"
        "⚡ Разовый урок — 1500₽\n"
        "📚 Абонемент 4 урока — 5500₽ (экономия 500₽)\n"
        "🔥 Абонемент 8 уроков — 10000₽ (экономия 2000₽)",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data.startswith("pay_"))
async def payment_selected(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.replace("pay_", "").split("_")
    amount = int(parts[0])
    tariff = parts[1]
    payment_id = create_payment(callback.from_user.id, amount, tariff)
    await state.update_data(payment_id=payment_id)
    await state.set_state(PaymentStates.waiting_for_receipt)

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="pay_cancel"))
    await callback.message.edit_text(
        f"💳 <b>Оплата {amount}₽</b>\n\n"
        f"Переведи на номер карты:\n"
        f"<code>2200 0000 0000 0000</code>\n\n"
        f"После оплаты отправь скриншот чека 👇",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data == "pay_cancel")
async def pay_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Оплата отменена")

@dp.message(PaymentStates.waiting_for_receipt, F.photo)
async def payment_receipt(message: Message, state: FSMContext):
    data = await state.get_data()
    payment_id = data.get('payment_id')
    file_id = message.photo[-1].file_id
    save_receipt(payment_id, file_id)
    await state.clear()

    await message.answer(
        "✅ <b>Чек получен!</b>\n\nОжидай подтверждения от администратора ☕",
        reply_markup=main_keyboard()
    )

    await bot.send_message(
        ADMIN_ID,
        f"💳 <b>Новый чек об оплате!</b>\n\n"
        f"👤 {message.from_user.full_name}\n"
        f"🆔 ID: {message.from_user.id}\n"
        f"💰 ID оплаты: {payment_id}\n\n"
        f"Для подтверждения: /confirm {payment_id} {message.from_user.id}"
    )
    await bot.send_photo(ADMIN_ID, file_id)

# ===== ИИ АССИСТЕНТ =====
@dp.message(F.text == "💡 Спросить ИИ")
async def ai_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(AIStates.waiting_for_question)
    await message.answer("🤖 <b>Задай свой вопрос!</b>\n\nЯ помогу с учёбой, объясню сложные темы и дам советы ☕")

@dp.message(AIStates.waiting_for_question)
async def ai_answer(message: Message, state: FSMContext):
    await state.clear()
    
    # Отправляем сообщение о загрузке
    thinking_msg = await message.answer("⏳ <b>Думаю...</b>")
    
    try:
        # Создаем клиент Groq
        client = Groq(api_key=GROQ_API_KEY)
        
        # Делаем запрос к API
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Ты помощник репетитора MindSpark. Отвечай кратко, по-русски, дружелюбно. Помогаешь ученикам с учёбой."},
                {"role": "user", "content": message.text}
            ],
            max_tokens=500
        )
        
        # Получаем ответ
        response_text = completion.choices[0].message.content
        
        # Удаляем сообщение о загрузке
        await thinking_msg.delete()
        
        # Отправляем ответ ИИ
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="🔄 Задать ещё вопрос", callback_data="ai_again"))
        builder.add(InlineKeyboardButton(text="🏠 Главное меню", callback_data="ai_main"))
        builder.adjust(1)
        
        await message.answer(
            f"🤖 <b>Ответ ИИ:</b>\n\n{response_text}",
            reply_markup=builder.as_markup()
        )
        
    except Exception as e:
        print(f"Ошибка Groq API: {e}")
        # Удаляем сообщение о загрузке
        await thinking_msg.delete()
        
        # Отправляем сообщение об ошибке
        await message.answer(
            "❌ <b>Не удалось получить ответ</b>\n\nПопробуй позже или переформулируй вопрос ☕",
            reply_markup=main_keyboard()
        )

@dp.callback_query(F.data == "ai_again")
async def ai_again(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AIStates.waiting_for_question)
    await callback.message.edit_text("🤖 <b>Задай следующий вопрос!</b>\n\nЧто интересует? ☕")

@dp.callback_query(F.data == "ai_main")
async def ai_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    welcome_text = (
        "🌿 Добро пожаловать в MindSpark!\n\n"
        "Здесь знания растут как дерево —\n"
        "корень за корнем, лист за листом 🌱\n\n"
        "Устраивайся поудобнее ☕\n"
        "С чего начнём?"
    )
    await callback.message.edit_text(welcome_text, reply_markup=main_keyboard())

# ===== ОТЗЫВЫ =====
@dp.message(F.text == "📜 Отзывы")
async def reviews_menu(message: Message, state: FSMContext):
    await state.clear()
    reviews = get_approved_reviews()
    default = [
        ("Анна, 16 лет", "За 3 месяца подняла оценку с 3 до 5 ⭐⭐⭐⭐⭐"),
        ("Максим, 14 лет", "Наконец понял алгебру, спасибо! ⭐⭐⭐⭐⭐"),
        ("Дарья, 17 лет", "Поступила в вуз мечты после курса ⭐⭐⭐⭐⭐"),
    ]
    text = "⭐ <b>Отзывы учеников:</b>\n\n"
    for name, review in (reviews if reviews else default):
        text += f"👤 <b>{name}</b>\n{review}\n\n"

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✍️ Оставить отзыв", callback_data="write_review"))
    await message.answer(text, reply_markup=builder.as_markup())

@dp.callback_query(F.data == "write_review")
async def write_review_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ReviewStates.waiting_for_text)
    await callback.message.edit_text(
        "✍️ Напиши свой отзыв!\n\nОн появится после проверки ☕"
    )

@dp.message(ReviewStates.waiting_for_text)
async def review_submit(message: Message, state: FSMContext):
    name = message.from_user.first_name
    review_id = save_review(message.from_user.id, name, message.text)
    await state.clear()

    await message.answer(
        "✅ <b>Спасибо за отзыв!</b>\n\nОн появится после проверки ☕",
        reply_markup=main_keyboard()
    )
    await bot.send_message(
        ADMIN_ID,
        f"📝 <b>Новый отзыв!</b>\n\n"
        f"👤 {name}\n"
        f"📄 {message.text}\n\n"
        f"Одобрить: /approve {review_id}"
    )

# ===== АДМИН КОМАНДЫ =====
@dp.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.clear()
    lessons, students = get_monthly_stats()
    bookings = get_bookings_for_days()
    text = (
        f"📊 <b>Админ панель MindSpark</b>\n\n"
        f"📚 Уроков за месяц: {lessons}\n"
        f"👥 Всего учеников: {students}\n\n"
        f"<b>Последние записи:</b>\n"
    )
    for name, date, time, created in bookings[:5]:
        text += f"• {name} — {date} {time}\n"

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="� Ученики", callback_data="admin_students"))
    builder.add(InlineKeyboardButton(text="📅 Все записи", callback_data="admin_bookings"))
    builder.add(InlineKeyboardButton(text="💰 Статистика оплат", callback_data="admin_payments"))
    builder.add(InlineKeyboardButton(text="✏️ Управление ДЗ", callback_data="admin_hw_manage"))
    builder.add(InlineKeyboardButton(text="� Умная рассылка", callback_data="admin_smart_newsletter"))
    builder.add(InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_newsletter"))
    builder.adjust(2)
    await message.answer(text, reply_markup=builder.as_markup())

@dp.callback_query(F.data == "admin_newsletter")
async def admin_newsletter(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    await state.set_state(NewsletterStates.waiting_for_text)
    await callback.message.edit_text("📢 Напиши текст рассылки:")

@dp.message(NewsletterStates.waiting_for_text)
async def newsletter_send(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.clear()
    students = get_all_students()
    sent = 0
    for user_id, name, _, _ in students:
        try:
            await bot.send_message(user_id, f"📢 <b>Сообщение от MindSpark:</b>\n\n{message.text}")
            sent += 1
        except:
            pass
    await message.answer(f"✅ Рассылка отправлена {sent} ученикам!", reply_markup=main_keyboard())

@dp.callback_query(F.data == "admin_students")
async def admin_students(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    students = get_all_students()
    text = f"👥 <b>Ученики ({len(students)}):</b>\n\n"
    for user_id, name, lessons, coffee in students:
        text += f"• {name} — {lessons} уроков, {coffee} ☕\n"
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back"))
    await callback.message.edit_text(text or "Пока нет учеников", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    lessons, students = get_monthly_stats()
    bookings = get_bookings_for_days()
    text = (
        f"📊 <b>Админ панель MindSpark</b>\n\n"
        f"📚 Уроков за месяц: {lessons}\n"
        f"👥 Всего учеников: {students}\n\n"
        f"<b>Последние записи:</b>\n"
    )
    for name, date, time, created in bookings[:5]:
        text += f"• {name} — {date} {time}\n"

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="👥 Ученики", callback_data="admin_students"))
    builder.add(InlineKeyboardButton(text="📅 Все записи", callback_data="admin_bookings"))
    builder.add(InlineKeyboardButton(text="� Статистика оплат", callback_data="admin_payments"))
    builder.add(InlineKeyboardButton(text="✏️ Управление ДЗ", callback_data="admin_hw_manage"))
    builder.add(InlineKeyboardButton(text="📢 Умная рассылка", callback_data="admin_smart_newsletter"))
    builder.add(InlineKeyboardButton(text="�� Рассылка", callback_data="admin_newsletter"))
    builder.adjust(2)
    await callback.message.edit_text(text, reply_markup=builder.as_markup())

@dp.callback_query(F.data == "admin_bookings")
async def admin_bookings(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    
    conn = sqlite3.connect('mindspark.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT name, date, time, user_id FROM bookings
        ORDER BY date DESC LIMIT 20
    ''')
    bookings = cursor.fetchall()
    conn.close()
    
    text = "📅 <b>Все записи на уроки:</b>\n\n"
    for name, date, time, user_id in bookings:
        text += f"👤 {name}\n📅 {date} в {time}\n🆔 {user_id}\n\n"
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="� Назад", callback_data="admin_back"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup())

@dp.callback_query(F.data == "admin_payments")
async def admin_payments(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    
    conn = sqlite3.connect('mindspark.db')
    cursor = conn.cursor()
    
    # Статистика
    cursor.execute("SELECT COUNT(*) FROM payments")
    total_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM payments WHERE status = 'confirmed'")
    confirmed_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM payments WHERE status = 'receipt_sent'")
    pending_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(amount) FROM payments WHERE status = 'confirmed'")
    total_sum = cursor.fetchone()[0] or 0
    
    # Последние платежи
    cursor.execute('''
        SELECT amount, tariff, status, created_at FROM payments
        ORDER BY created_at DESC LIMIT 5
    ''')
    recent_payments = cursor.fetchall()
    conn.close()
    
    text = (
        f"💰 <b>Статистика оплат:</b>\n\n"
        f"✅ Подтверждено: {confirmed_count} на {total_sum}₽\n"
        f"⏳ Ожидают подтверждения: {pending_count}\n"
        f"📊 Всего платежей: {total_count}\n\n"
        f"<b>Последние платежи:</b>\n"
    )
    
    for amount, tariff, status, created in recent_payments:
        status_icon = "✅" if status == 'confirmed' else "⏳"
        text += f"{status_icon} {amount}₽ - {tariff}\n"
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup())

@dp.callback_query(F.data == "admin_hw_manage")
async def admin_hw_manage(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    
    hw = get_active_homework()
    if hw:
        hw_id, title, description = hw
        text = f"✏️ <b>Текущее ДЗ:</b>\n\n<b>{title}</b>\n{description}"
    else:
        text = "✏️ <b>Управление ДЗ</b>\n\nАктивных заданий нет"
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✏️ Новое задание", callback_data="admin_hw_new"))
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back"))
    builder.adjust(1)
    await callback.message.edit_text(text, reply_markup=builder.as_markup())

@dp.callback_query(F.data == "admin_hw_new")
async def admin_hw_new(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_hw)
    await callback.message.edit_text("✏️ Напиши текст нового домашнего задания:")

@dp.message(AdminStates.waiting_for_hw)
async def admin_hw_create(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.clear()
    
    hw_text = message.text
    
    # Деактивируем старые ДЗ
    conn = sqlite3.connect('mindspark.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE homework SET is_active = 0")
    
    # Создаем новое ДЗ
    cursor.execute('''
        INSERT INTO homework (title, description, is_active)
        VALUES (?, ?, 1)
    ''', ("Домашнее задание", hw_text))
    conn.commit()
    
    # Получаем всех учеников
    cursor.execute("SELECT user_id FROM students")
    students = cursor.fetchall()
    conn.close()
    
    sent = 0
    for (user_id,) in students:
        try:
            await bot.send_message(
                user_id,
                f"� <b>Новое домашнее задание!</b>\n\n{hw_text}\n\n"
                f"Открой 🌿 Мой кабинет → � Домашнее задание чтобы сдать работу"
            )
            sent += 1
        except:
            pass
    
    await message.answer(f"✅ ДЗ обновлено и разослано {sent} ученикам!", reply_markup=main_keyboard())

@dp.callback_query(F.data == "admin_smart_newsletter")
async def admin_smart_newsletter(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    
    text = "📢 <b>Умная рассылка</b>\n\nВыбери получателей:"
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="👥 Всем ученикам", callback_data="nl_all"))
    builder.add(InlineKeyboardButton(text="📅 У кого урок сегодня", callback_data="nl_today"))
    builder.add(InlineKeyboardButton(text="⏳ Кто не сдал ДЗ", callback_data="nl_no_hw"))
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back"))
    builder.adjust(1)
    await callback.message.edit_text(text, reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("nl_"))
async def admin_newsletter_filter(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    
    filter_type = callback.data.replace("nl_", "")
    await state.update_data(filter=filter_type)
    await state.set_state(AdminStates.waiting_for_newsletter_text)
    
    if filter_type == "all":
        text = "📢 Напиши текст рассылки для всех учеников:"
    elif filter_type == "today":
        text = "📢 Напиши текст рассылки для тех, у кого урок сегодня:"
    elif filter_type == "no_hw":
        text = "📢 Напиши текст рассылки для тех, кто не сдавал ДЗ:"
    
    await callback.message.edit_text(text)

@dp.message(AdminStates.waiting_for_newsletter_text)
async def admin_smart_newsletter_send(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    data = await state.get_data()
    filter_type = data.get('filter', 'all')
    await state.clear()
    
    conn = sqlite3.connect('mindspark.db')
    cursor = conn.cursor()
    
    if filter_type == "all":
        cursor.execute("SELECT user_id FROM students")
        recipients = [row[0] for row in cursor.fetchall()]
    
    elif filter_type == "today":
        today = datetime.now().strftime("%d.%m.%Y")
        cursor.execute("SELECT user_id FROM bookings WHERE date = ?", (today,))
        recipients = [row[0] for row in cursor.fetchall()]
    
    elif filter_type == "no_hw":
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        cursor.execute('''
            SELECT DISTINCT user_id FROM students s
            WHERE s.user_id NOT IN (
                SELECT DISTINCT user_id FROM homework_submissions 
                WHERE submitted_at >= ?
            )
        ''', (week_ago,))
        recipients = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    sent = 0
    newsletter_text = f"📢 <b>Сообщение от MindSpark:</b>\n\n{message.text}"
    
    for user_id in recipients:
        try:
            await bot.send_message(user_id, newsletter_text)
            sent += 1
        except:
            pass
    
    await message.answer(f"✅ Разослано {sent} ученикам!", reply_markup=main_keyboard())

@dp.message(Command("confirm"))
async def cmd_confirm(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        parts = message.text.split()
        payment_id = int(parts[1])
        user_id = int(parts[2])
        confirm_payment_db(payment_id)
        await message.answer(f"✅ Оплата {payment_id} подтверждена!")
        await bot.send_message(
            user_id,
            "✅ <b>Оплата подтверждена!</b>\n\nДобро пожаловать в MindSpark ⚡",
            reply_markup=main_keyboard()
        )
    except Exception as e:
        await message.answer(f"Ошибка: {e}\nФормат: /confirm [payment_id] [user_id]")

@dp.message(Command("approve"))
async def cmd_approve(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        review_id = int(message.text.split()[1])
        approve_review_db(review_id)
        await message.answer(f"✅ Отзыв {review_id} одобрен!")
    except Exception as e:
        await message.answer(f"Ошибка: {e}\nФормат: /approve [review_id]")

@dp.message(Command("add_material"))
async def cmd_add_material(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        parts = message.text.split(None, 3)
        user_id = int(parts[1])
        title = parts[2]
        content = parts[3]
        conn = sqlite3.connect('mindspark.db')
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO materials (user_id, title, content) VALUES (?, ?, ?)',
            (user_id, title, content)
        )
        conn.commit()
        conn.close()
        await message.answer(f"✅ Материал добавлен ученику {user_id}")
    except Exception as e:
        await message.answer(f"Ошибка: {e}\nФормат: /add_material [user_id] [название] [ссылка]")

@dp.message(Command("set_hw"))
async def cmd_set_hw(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        text = message.text.split(None, 1)[1]
        conn = sqlite3.connect('mindspark.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE homework SET is_active = 0')
        cursor.execute(
            'INSERT INTO homework (title, description) VALUES (?, ?)',
            ("Домашнее задание", text)
        )
        conn.commit()
        conn.close()
        await message.answer("✅ Домашнее задание обновлено!")
    except Exception as e:
        await message.answer(f"Ошибка: {e}\nФормат: /set_hw [текст задания]")

@dp.message(Command("set_progress"))
async def cmd_set_progress(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        parts = message.text.split()
        user_id = int(parts[1])
        percentage = int(parts[2])
        lessons = int(parts[3]) if len(parts) > 3 else None
        conn = sqlite3.connect('mindspark.db')
        cursor = conn.cursor()
        if lessons:
            cursor.execute(
                'UPDATE students SET progress_percentage = ?, lessons_completed = ? WHERE user_id = ?',
                (percentage, lessons, user_id)
            )
        else:
            cursor.execute(
                'UPDATE students SET progress_percentage = ? WHERE user_id = ?',
                (percentage, user_id)
            )
        conn.commit()
        conn.close()
        await message.answer(f"✅ Прогресс ученика {user_id} обновлён: {percentage}%")
    except Exception as e:
        await message.answer(f"Ошибка: {e}\nФормат: /set_progress [user_id] [%] [уроков]")

# ===== НАПОМИНАНИЯ =====
async def check_reminders():
    while True:
        try:
            conn = sqlite3.connect('mindspark.db')
            cursor = conn.cursor()
            
            # Получаем все записи без напоминаний
            cursor.execute('''
                SELECT user_id, name, date, time FROM bookings
                WHERE reminder_sent = 0
            ''')
            bookings = cursor.fetchall()
            
            current_time = datetime.now()
            
            for user_id, name, date, time in bookings:
                try:
                    # Парсим дату и время
                    lesson_datetime = datetime.strptime(f"{date} {time}", "%d.%m.%Y %H:%M")
                    
                    # Проверяем время до урока
                    time_diff = lesson_datetime - current_time
                    
                    # Если до урока меньше 60 минут и больше 0 минут
                    if 0 < time_diff.total_seconds() < 3600:
                        reminder_text = (
                            f"⏰ <b>Напоминание!</b>\n\n"
                            f"Твой урок MindSpark через час!\n"
                            f"📅 {date} в {time} ☕\n"
                            f"Будь готов!"
                        )
                        
                        try:
                            await bot.send_message(user_id, reminder_text)
                            
                            # Отмечаем что напоминание отправлено
                            cursor.execute('''
                                UPDATE bookings SET reminder_sent = 1
                                WHERE user_id = ? AND date = ? AND time = ?
                            ''', (user_id, date, time))
                            conn.commit()
                            
                        except Exception as e:
                            print(f"Ошибка отправки напоминания пользователю {user_id}: {e}")
                            
                except ValueError as e:
                    print(f"Ошибка парсинга даты {date} {time}: {e}")
                    
            conn.close()
            
        except Exception as e:
            print(f"Ошибка в check_reminders: {e}")
        
        # Проверяем каждые 60 секунд
        await asyncio.sleep(60)

# ===== ЗАПУСК =====
async def main():
    init_db()
    
    # Запуск фоновой задачи для напоминаний
    asyncio.create_task(check_reminders())
    
    print("MindSpark бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
