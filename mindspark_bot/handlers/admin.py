import html
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.db import execute, fetchall, fetchone
from keyboards.menus import back, buttons
from states.fsm import AdminCourse, AdminLesson, AnnouncementFlow

router = Router(name='admin')


@router.message(Command('admin_help'))
async def admin_help(message: Message, db_user: dict) -> None:
    if not is_admin(db_user): return
    await message.answer(
        '<b>Служебные команды</b>\n'
        '/link_parent ID_родителя ID_ученика\n'
        '/assign_teacher ID_курса Telegram_ID\n'
        '/new_homework ID_курса | Заголовок | Описание | ДД.ММ.ГГГГ\n\n'
        'Числовые ID пользователей видны в разделе «Пользователи».'
    )


@router.callback_query(F.data == 'admin_help')
async def admin_help_callback(callback: CallbackQuery, db_user: dict) -> None:
    if await deny(callback, db_user): return
    await callback.answer()
    await callback.message.answer(
        '<b>Управление школой</b>\n\n'
        'Связать родителя: <code>/link_parent ID_родителя ID_ученика</code>\n'
        'Назначить преподавателя: <code>/assign_teacher ID_курса Telegram_ID</code>\n'
        'Создать ДЗ: <code>/new_homework ID_курса | Заголовок | Описание | ДД.ММ.ГГГГ</code>',
        reply_markup=back(),
    )


@router.message(Command('link_parent'))
async def link_parent(message: Message, db_user: dict) -> None:
    if not is_admin(db_user): return
    try:
        _, parent_id, student_id = message.text.split()
        parent = await fetchone("SELECT * FROM users WHERE id=? AND role='parent'", (int(parent_id),))
        student = await fetchone("SELECT * FROM users WHERE id=? AND role='student'", (int(student_id),))
        if not parent or not student: raise ValueError
        await execute('INSERT OR IGNORE INTO parent_students(parent_id,student_id) VALUES(?,?)', (parent['id'],student['id']))
        await message.answer('Родитель и ученик связаны ✅')
    except (ValueError, IndexError):
        await message.answer('Формат: /link_parent ID_родителя ID_ученика')


@router.message(Command('assign_teacher'))
async def assign_teacher(message: Message, db_user: dict) -> None:
    if not is_admin(db_user): return
    try:
        _, course_id, telegram_id = message.text.split()
        teacher = await fetchone("SELECT * FROM users WHERE telegram_id=? AND role='teacher' AND is_approved=1", (int(telegram_id),))
        course = await fetchone('SELECT * FROM courses WHERE id=?', (int(course_id),))
        if not teacher or not course: raise ValueError
        await execute('UPDATE courses SET teacher_id=? WHERE id=?', (teacher['id'],course['id']))
        await message.answer('Преподаватель назначен ✅')
    except (ValueError, IndexError):
        await message.answer('Формат: /assign_teacher ID_курса Telegram_ID')


@router.message(Command('new_homework'))
async def new_homework(message: Message, db_user: dict) -> None:
    if not is_admin(db_user): return
    try:
        payload = message.text.split(maxsplit=1)[1]
        course_raw, title, description, deadline_raw = [part.strip() for part in payload.split('|', 3)]
        deadline = datetime.strptime(deadline_raw, '%d.%m.%Y').date().isoformat()
        course = await fetchone('SELECT * FROM courses WHERE id=?', (int(course_raw),))
        if not course: raise ValueError
        await execute('INSERT INTO homework(course_id,teacher_id,title,description,deadline) VALUES(?,?,?,?,?)', (course['id'],course['teacher_id'],title[:100],description[:2000],deadline))
        await message.answer('Домашнее задание опубликовано ✅')
    except (ValueError, IndexError):
        await message.answer('Формат: /new_homework ID_курса | Заголовок | Описание | ДД.ММ.ГГГГ')


def is_admin(user: dict) -> bool:
    return user.get('role') == 'admin' and bool(user.get('is_approved'))


async def deny(callback: CallbackQuery, user: dict) -> bool:
    if is_admin(user):
        return False
    await callback.answer('Доступ запрещён', show_alert=True)
    return True


@router.callback_query(F.data == 'admin_stats')
async def stats(callback: CallbackQuery, db_user: dict) -> None:
    if await deny(callback, db_user): return
    user_count = await fetchone('SELECT COUNT(*) total FROM users')
    course_count = await fetchone('SELECT COUNT(*) total FROM courses WHERE is_active=1')
    lesson_count = await fetchone("SELECT COUNT(*) total FROM lessons WHERE status='scheduled' AND starts_at>CURRENT_TIMESTAMP")
    revenue = await fetchone("SELECT COALESCE(SUM(amount_cents),0) total FROM payments WHERE status='paid'")
    await callback.answer()
    await callback.message.answer(
        f"<b>Статистика</b>\n\nПользователей: {user_count['total']}\nАктивных курсов: {course_count['total']}\n"
        f"Предстоящих занятий: {lesson_count['total']}\nПодтверждено оплат: {revenue['total']/100:,.0f} ₽".replace(',', ' '), reply_markup=back())


@router.callback_query(F.data == 'admin_users')
async def users(callback: CallbackQuery, db_user: dict) -> None:
    if await deny(callback, db_user): return
    rows = await fetchall("SELECT * FROM users ORDER BY CASE WHEN role='teacher' AND is_approved=0 THEN 0 ELSE 1 END, id DESC LIMIT 30")
    await callback.answer()
    text = '<b>Пользователи</b>\n\n' + '\n'.join(
        f"№{r['id']} {html.escape(r['full_name'])} · {r['role']} {'✅' if r['is_approved'] else '⏳'}" for r in rows
    )
    kb = [[(f"✅ Одобрить {r['full_name'][:20]}", f"approve_user:{r['id']}")] for r in rows if not r['is_approved']]
    kb.append([('← Главное меню', 'menu')])
    await callback.message.answer(text, reply_markup=buttons(kb))


@router.callback_query(F.data.startswith('approve_user:'))
async def approve_user(callback: CallbackQuery, db_user: dict) -> None:
    if await deny(callback, db_user): return
    user_id = int(callback.data.split(':')[1])
    user = await fetchone('SELECT * FROM users WHERE id=?', (user_id,))
    await execute('UPDATE users SET is_approved=1 WHERE id=?', (user_id,))
    await callback.answer('Пользователь одобрен', show_alert=True)
    if user:
        try: await callback.bot.send_message(user['telegram_id'], 'Ваша заявка одобрена. Откройте /menu.')
        except Exception: pass


@router.callback_query(F.data == 'admin_courses')
async def admin_courses(callback: CallbackQuery, db_user: dict) -> None:
    if await deny(callback, db_user): return
    rows = await fetchall('SELECT * FROM courses ORDER BY is_active DESC, id DESC')
    await callback.answer()
    text = '<b>Курсы</b>\n\n' + ('\n'.join(f"№{r['id']} {html.escape(r['title'])} · {r['price_cents']/100:g} ₽ {'✅' if r['is_active'] else '⛔'}" for r in rows) if rows else 'Курсов пока нет.')
    await callback.message.answer(text, reply_markup=buttons([[('➕ Создать курс', 'admin_course_new')], [('← Главное меню', 'menu')]]))


@router.callback_query(F.data == 'admin_course_new')
async def course_new(callback: CallbackQuery, state: FSMContext, db_user: dict) -> None:
    if await deny(callback, db_user): return
    await state.set_state(AdminCourse.title)
    await callback.answer()
    await callback.message.answer('Название курса:')


@router.message(AdminCourse.title, F.text)
async def course_title(message: Message, state: FSMContext, db_user: dict) -> None:
    if not is_admin(db_user): return
    await state.update_data(title=message.text.strip()[:100])
    await state.set_state(AdminCourse.description)
    await message.answer('Короткое описание курса:')


@router.message(AdminCourse.description, F.text)
async def course_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=message.text.strip()[:1500])
    await state.set_state(AdminCourse.price)
    await message.answer('Цена одного занятия в рублях, например 1500:')


@router.message(AdminCourse.price, F.text)
async def course_price(message: Message, state: FSMContext) -> None:
    try: price = int(float(message.text.replace(',', '.')) * 100)
    except ValueError:
        await message.answer('Введите число, например 1500.')
        return
    if price < 0: return await message.answer('Цена не может быть отрицательной.')
    await state.update_data(price=price)
    await state.set_state(AdminCourse.subscription)
    await message.answer('Цена абонемента в рублях или 0, если его нет:')


@router.message(AdminCourse.subscription, F.text)
async def course_subscription(message: Message, state: FSMContext) -> None:
    try: value = int(float(message.text.replace(',', '.')) * 100)
    except ValueError:
        await message.answer('Введите число.')
        return
    await state.update_data(subscription=max(value, 0))
    await state.set_state(AdminCourse.format)
    await message.answer('Выберите формат:', reply_markup=buttons([[('Группа', 'course_format:group'), ('Индивидуально', 'course_format:individual')], [('Оба', 'course_format:mixed')]]))


@router.callback_query(AdminCourse.format, F.data.startswith('course_format:'))
async def course_format(callback: CallbackQuery, state: FSMContext, db_user: dict) -> None:
    if await deny(callback, db_user): return
    fmt = callback.data.split(':')[1]
    if fmt not in {'group','individual','mixed'}: return
    data = await state.get_data()
    course_id = await execute(
        'INSERT INTO courses(title,description,format,price_cents,subscription_price_cents) VALUES(?,?,?,?,?)',
        (data['title'], data['description'], fmt, data['price'], data['subscription']),
    )
    await state.clear(); await callback.answer('Курс создан', show_alert=True)
    await callback.message.answer(f'Курс №{course_id} создан.', reply_markup=back())


@router.callback_query(F.data == 'admin_lessons')
async def admin_lessons(callback: CallbackQuery, db_user: dict) -> None:
    if await deny(callback, db_user): return
    rows = await fetchall("SELECT l.*,c.title FROM lessons l JOIN courses c ON c.id=l.course_id WHERE l.starts_at>CURRENT_TIMESTAMP ORDER BY l.starts_at LIMIT 30")
    await callback.answer()
    text = '<b>Предстоящие занятия</b>\n\n' + ('\n'.join(f"№{r['id']} {html.escape(r['title'])} · {r['starts_at']}" for r in rows) if rows else 'Занятий пока нет.')
    await callback.message.answer(text, reply_markup=buttons([[('➕ Создать занятие', 'admin_lesson_new')], [('← Главное меню', 'menu')]]))


@router.callback_query(F.data == 'admin_lesson_new')
async def lesson_new(callback: CallbackQuery, state: FSMContext, db_user: dict) -> None:
    if await deny(callback, db_user): return
    courses = await fetchall('SELECT id,title FROM courses WHERE is_active=1 ORDER BY title')
    if not courses:
        await callback.answer('Сначала создайте курс', show_alert=True); return
    await state.set_state(AdminLesson.course); await callback.answer()
    await callback.message.answer('Выберите курс:', reply_markup=buttons([[(r['title'], f"lesson_course:{r['id']}")] for r in courses]))


@router.callback_query(AdminLesson.course, F.data.startswith('lesson_course:'))
async def lesson_course(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(course_id=int(callback.data.split(':')[1])); await state.set_state(AdminLesson.starts_at)
    await callback.answer(); await callback.message.answer('Дата и время занятия: ДД.ММ.ГГГГ ЧЧ:ММ')


@router.message(AdminLesson.starts_at, F.text)
async def lesson_date(message: Message, state: FSMContext) -> None:
    try: starts = datetime.strptime(message.text.strip(), '%d.%m.%Y %H:%M')
    except ValueError:
        await message.answer('Нужен формат ДД.ММ.ГГГГ ЧЧ:ММ, например 20.07.2026 17:30.'); return
    if starts < datetime.now():
        await message.answer('Дата должна быть в будущем.'); return
    await state.update_data(starts=starts.isoformat(sep=' ', timespec='minutes'))
    await state.set_state(AdminLesson.capacity); await message.answer('Количество мест:')


@router.message(AdminLesson.capacity, F.text)
async def lesson_capacity(message: Message, state: FSMContext, db_user: dict) -> None:
    try: capacity = int(message.text)
    except ValueError: return await message.answer('Введите целое число.')
    if not 1 <= capacity <= 100: return await message.answer('Допустимо от 1 до 100 мест.')
    data = await state.get_data(); starts = datetime.fromisoformat(data['starts']); ends = starts + timedelta(minutes=60)
    lesson_id = await execute('INSERT INTO lessons(course_id,starts_at,ends_at,capacity) VALUES(?,?,?,?)', (data['course_id'], data['starts'], ends.isoformat(sep=' ', timespec='minutes'), capacity))
    await state.clear(); await message.answer(f'Занятие №{lesson_id} создано.', reply_markup=back())


@router.callback_query(F.data == 'admin_payments')
async def admin_payments(callback: CallbackQuery, db_user: dict) -> None:
    if await deny(callback, db_user): return
    rows = await fetchall("SELECT p.*,u.full_name FROM payments p JOIN users u ON u.id=p.user_id WHERE p.status='review' ORDER BY p.id")
    await callback.answer()
    text = '<b>Чеки на проверке</b>\n\n' + ('\n'.join(f"№{r['id']} {html.escape(r['full_name'])} · {r['amount_cents']/100:g} ₽" for r in rows) if rows else 'Новых чеков нет.')
    kb = []
    for r in rows: kb.append([(f"✅ №{r['id']}", f"payment_paid:{r['id']}"), (f"❌ №{r['id']}", f"payment_reject:{r['id']}")])
    kb.append([('← Главное меню', 'menu')]); await callback.message.answer(text, reply_markup=buttons(kb))


@router.callback_query(F.data.startswith(('payment_paid:', 'payment_reject:')))
async def payment_decision(callback: CallbackQuery, db_user: dict) -> None:
    if await deny(callback, db_user): return
    action, payment_id_raw = callback.data.split(':'); payment_id = int(payment_id_raw)
    payment = await fetchone('SELECT p.*,u.telegram_id FROM payments p JOIN users u ON u.id=p.user_id WHERE p.id=?', (payment_id,))
    status = 'paid' if action == 'payment_paid' else 'rejected'
    await execute("UPDATE payments SET status=?, confirmed_at=CASE WHEN ?='paid' THEN CURRENT_TIMESTAMP ELSE NULL END WHERE id=? AND status='review'", (status,status,payment_id))
    if payment and status == 'paid' and payment['course_id']:
        await execute("INSERT INTO enrollments(student_id,course_id,status) VALUES(?,?,'active') ON CONFLICT(student_id,course_id) DO UPDATE SET status='active'", (payment['user_id'],payment['course_id']))
    await callback.answer('Решение сохранено', show_alert=True)
    if payment:
        try: await callback.bot.send_message(payment['telegram_id'], f"Платёж №{payment_id}: {'подтверждён ✅' if status=='paid' else 'отклонён ❌'}")
        except Exception: pass


@router.callback_query(F.data == 'admin_broadcast')
async def broadcast(callback: CallbackQuery, state: FSMContext, db_user: dict) -> None:
    if await deny(callback, db_user): return
    await state.set_state(AnnouncementFlow.text); await callback.answer(); await callback.message.answer('Введите текст рассылки. Для отмены: /cancel')


@router.message(AnnouncementFlow.text, F.text)
async def broadcast_send(message: Message, state: FSMContext, db_user: dict) -> None:
    if not is_admin(db_user): return
    recipients = await fetchall('SELECT telegram_id FROM users WHERE is_blocked=0 AND role != \'pending\'')
    sent = 0
    for recipient in recipients:
        try: await message.bot.send_message(recipient['telegram_id'], f"<b>Новости MindSpark</b>\n\n{html.escape(message.text)}"); sent += 1
        except Exception: pass
    await execute('INSERT INTO announcements(author_id,text) VALUES(?,?)', (db_user['id'],message.text))
    await state.clear(); await message.answer(f'Рассылка завершена. Доставлено: {sent} из {len(recipients)}.', reply_markup=back())
