import html
from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import config
from database.db import execute, fetchall, fetchone, get_user
from keyboards.menus import back, buttons
from states.fsm import PaymentFlow

router = Router(name='student')


def money(cents: int) -> str:
    return f'{cents / 100:,.2f} ₽'.replace(',', ' ').replace('.00', '')


def dt(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime('%d.%m.%Y %H:%M')
    except ValueError:
        return value


@router.callback_query(F.data == 'courses')
async def courses(callback: CallbackQuery) -> None:
    rows = await fetchall('SELECT * FROM courses WHERE is_active=1 ORDER BY title')
    await callback.answer()
    if not rows:
        await callback.message.answer('Курсы скоро появятся.', reply_markup=back())
        return
    kb = [[(f"{row['title']} · {money(row['price_cents'])}", f"course:{row['id']}")] for row in rows]
    kb.append([('← Главное меню', 'menu')])
    await callback.message.answer('<b>Курсы MindSpark</b>', reply_markup=buttons(kb))


@router.callback_query(F.data.startswith('course:'))
async def course_details(callback: CallbackQuery) -> None:
    course_id = int(callback.data.split(':')[1])
    course = await fetchone('SELECT * FROM courses WHERE id=? AND is_active=1', (course_id,))
    await callback.answer()
    if not course:
        await callback.message.answer('Курс больше недоступен.', reply_markup=back())
        return
    formats = {'group': 'групповой', 'individual': 'индивидуальный', 'mixed': 'групповой и индивидуальный'}
    text = (
        f"<b>{html.escape(course['title'])}</b>\n\n{html.escape(course['description'])}\n\n"
        f"Формат: {formats[course['format']]}\nРазовое занятие: {money(course['price_cents'])}\n"
        f"Абонемент: {money(course['subscription_price_cents']) if course['subscription_price_cents'] else 'не предусмотрен'}"
    )
    rows = [[('📅 Выбрать занятие', f"lessons:{course_id}")], [('💳 Разовая оплата', f"pay:{course_id}:one_time")]]
    if course['subscription_price_cents']:
        rows.append([('🔁 Купить абонемент', f"pay:{course_id}:subscription")])
    rows.append([('← К курсам', 'courses')])
    await callback.message.answer(text, reply_markup=buttons(rows))


@router.callback_query(F.data.startswith('lessons:'))
async def lessons(callback: CallbackQuery) -> None:
    course_id = int(callback.data.split(':')[1])
    rows = await fetchall(
        """SELECT l.*, c.title, COUNT(CASE WHEN b.status='confirmed' THEN 1 END) booked
        FROM lessons l JOIN courses c ON c.id=l.course_id LEFT JOIN bookings b ON b.lesson_id=l.id
        WHERE l.course_id=? AND l.status='scheduled' AND l.starts_at > CURRENT_TIMESTAMP
        GROUP BY l.id ORDER BY l.starts_at LIMIT 30""", (course_id,),
    )
    await callback.answer()
    kb = [[(f"{dt(row['starts_at'])} · {row['capacity']-row['booked']} мест", f"book:{row['id']}")] for row in rows if row['booked'] < row['capacity']]
    kb.append([('← К курсу', f'course:{course_id}')])
    await callback.message.answer('Выберите свободное занятие:' if len(kb) > 1 else 'Свободных занятий пока нет.', reply_markup=buttons(kb))


@router.callback_query(F.data.startswith('book:'))
async def book(callback: CallbackQuery, db_user: dict) -> None:
    lesson_id = int(callback.data.split(':')[1])
    lesson = await fetchone(
        """SELECT l.*, COUNT(CASE WHEN b.status='confirmed' THEN 1 END) booked
        FROM lessons l LEFT JOIN bookings b ON b.lesson_id=l.id WHERE l.id=? GROUP BY l.id""", (lesson_id,),
    )
    if not lesson or lesson['status'] != 'scheduled' or lesson['booked'] >= lesson['capacity']:
        await callback.answer('Мест уже нет', show_alert=True)
        return
    try:
        await execute("INSERT INTO bookings(lesson_id,student_id) VALUES(?,?)", (lesson_id, db_user['id']))
    except Exception:
        await callback.answer('Вы уже записаны на это занятие', show_alert=True)
        return
    await callback.answer('Запись подтверждена', show_alert=True)
    await callback.message.answer(f"Вы записаны на {dt(lesson['starts_at'])}.", reply_markup=back())


@router.callback_query(F.data.in_({'my_schedule', 'my_bookings'}))
async def my_bookings(callback: CallbackQuery, db_user: dict) -> None:
    rows = await fetchall(
        """SELECT b.id, b.status, l.starts_at, c.title FROM bookings b
        JOIN lessons l ON l.id=b.lesson_id JOIN courses c ON c.id=l.course_id
        WHERE b.student_id=? AND b.status='confirmed' AND l.starts_at > CURRENT_TIMESTAMP ORDER BY l.starts_at""", (db_user['id'],),
    )
    await callback.answer()
    if not rows:
        await callback.message.answer('Предстоящих записей нет.', reply_markup=back())
        return
    text = '<b>Ваши занятия</b>\n\n' + '\n'.join(f"• {html.escape(row['title'])} — {dt(row['starts_at'])}" for row in rows)
    kb = [[(f"Отменить: {dt(row['starts_at'])}", f"cancel_booking:{row['id']}")] for row in rows]
    kb.append([('← Главное меню', 'menu')])
    await callback.message.answer(text, reply_markup=buttons(kb))


@router.callback_query(F.data.startswith('cancel_booking:'))
async def cancel_booking(callback: CallbackQuery, db_user: dict) -> None:
    booking_id = int(callback.data.split(':')[1])
    await execute("UPDATE bookings SET status='cancelled' WHERE id=? AND student_id=? AND status='confirmed'", (booking_id, db_user['id']))
    await callback.answer('Запись отменена', show_alert=True)
    await callback.message.answer('Запись отменена. Место снова доступно.', reply_markup=back())


@router.callback_query(F.data == 'payments')
async def payments(callback: CallbackQuery, db_user: dict) -> None:
    rows = await fetchall('SELECT * FROM payments WHERE user_id=? ORDER BY id DESC LIMIT 10', (db_user['id'],))
    await callback.answer()
    labels = {'awaiting_receipt':'ожидает чек','review':'на проверке','paid':'оплачено','rejected':'отклонено','cancelled':'отменено'}
    text = '<b>Мои платежи</b>\n\n' + ('\n'.join(f"№{r['id']} · {money(r['amount_cents'])} · {labels[r['status']]}" for r in rows) if rows else 'Платежей пока нет.')
    await callback.message.answer(text, reply_markup=buttons([[('📚 Выбрать курс', 'courses')], [('← Главное меню', 'menu')]]))


@router.callback_query(F.data.startswith('pay:'))
async def create_payment(callback: CallbackQuery, state: FSMContext, db_user: dict) -> None:
    _, course_id_raw, kind = callback.data.split(':')
    course = await fetchone('SELECT * FROM courses WHERE id=? AND is_active=1', (int(course_id_raw),))
    if not course or kind not in {'one_time', 'subscription'}:
        await callback.answer('Предложение недоступно', show_alert=True)
        return
    amount = course['price_cents'] if kind == 'one_time' else course['subscription_price_cents']
    if amount <= 0:
        await callback.answer('Цена не настроена', show_alert=True)
        return
    payment_id = await execute('INSERT INTO payments(user_id,course_id,kind,amount_cents) VALUES(?,?,?,?)', (db_user['id'], course['id'], kind, amount))
    await state.set_state(PaymentFlow.receipt)
    await state.update_data(payment_id=payment_id)
    await callback.answer()
    await callback.message.answer(
        f"<b>Счёт №{payment_id}</b> на {money(amount)}\n\n{html.escape(config.payment_details)}\n\nОтправьте сюда фотографию или файл чека. Для отмены: /cancel"
    )


@router.message(PaymentFlow.receipt, F.photo | F.document)
async def receipt(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    file_id = message.photo[-1].file_id if message.photo else message.document.file_id
    await execute("UPDATE payments SET receipt_file_id=?, status='review' WHERE id=?", (file_id, data['payment_id']))
    await state.clear()
    await message.answer('Чек принят и отправлен администратору на проверку.')
    for admin_id in config.admin_ids:
        try:
            await message.bot.send_message(admin_id, f"Новый чек по платежу №{data['payment_id']}")
        except Exception:
            pass


@router.message(PaymentFlow.receipt)
async def receipt_invalid(message: Message) -> None:
    await message.answer('Отправьте чек фотографией или документом.')


@router.callback_query(F.data == 'homework')
async def homework(callback: CallbackQuery, db_user: dict) -> None:
    rows = await fetchall(
        """SELECT h.* , c.title course_title FROM homework h JOIN courses c ON c.id=h.course_id
        JOIN enrollments e ON e.course_id=h.course_id WHERE e.student_id=? AND e.status='active'
        ORDER BY h.id DESC LIMIT 20""", (db_user['id'],),
    )
    await callback.answer()
    text = '<b>Домашние задания</b>\n\n' + ('\n\n'.join(f"<b>{html.escape(r['title'])}</b> · {html.escape(r['course_title'])}\n{html.escape(r['description'])}" for r in rows) if rows else 'Новых заданий нет.')
    await callback.message.answer(text, reply_markup=back())
