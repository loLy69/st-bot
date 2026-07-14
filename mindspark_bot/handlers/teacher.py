import html
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from database.db import execute, fetchall, fetchone
from keyboards.menus import back, buttons
from states.fsm import GradeSubmissionFlow

router = Router(name='teacher')


async def allowed(callback: CallbackQuery, user: dict) -> bool:
    if user.get('role') == 'teacher' and user.get('is_approved'):
        return True
    await callback.answer('Ваш профиль преподавателя ещё не одобрен.', show_alert=True)
    return False


@router.callback_query(F.data == 'teacher_schedule')
async def schedule(callback: CallbackQuery, db_user: dict) -> None:
    if not await allowed(callback, db_user): return
    rows = await fetchall("""SELECT l.*,c.title FROM lessons l JOIN courses c ON c.id=l.course_id
        WHERE l.teacher_id=? AND l.status='scheduled' AND l.starts_at>CURRENT_TIMESTAMP ORDER BY l.starts_at""", (db_user['id'],))
    await callback.answer()
    text = '<b>Мои занятия</b>\n\n' + ('\n'.join(f"• {html.escape(r['title'])} — {r['starts_at']}" for r in rows) if rows else 'Предстоящих занятий нет.')
    await callback.message.answer(text, reply_markup=back())


@router.callback_query(F.data == 'teacher_students')
async def students(callback: CallbackQuery, db_user: dict) -> None:
    if not await allowed(callback, db_user): return
    rows = await fetchall("""SELECT DISTINCT u.full_name,c.title FROM users u JOIN enrollments e ON e.student_id=u.id
        JOIN courses c ON c.id=e.course_id WHERE c.teacher_id=? AND e.status='active' ORDER BY c.title,u.full_name""", (db_user['id'],))
    await callback.answer()
    text = '<b>Мои ученики</b>\n\n' + ('\n'.join(f"• {html.escape(r['full_name'])} · {html.escape(r['title'])}" for r in rows) if rows else 'Учеников пока нет.')
    await callback.message.answer(text, reply_markup=back())


@router.callback_query(F.data == 'teacher_homework')
async def homework(callback: CallbackQuery, db_user: dict) -> None:
    if not await allowed(callback, db_user): return
    rows = await fetchall("""SELECT s.id,u.full_name,h.title,s.answer,s.file_id,s.submitted_at
        FROM homework_submissions s JOIN homework h ON h.id=s.homework_id JOIN users u ON u.id=s.student_id
        JOIN courses c ON c.id=h.course_id WHERE c.teacher_id=? ORDER BY s.submitted_at DESC LIMIT 30""", (db_user['id'],))
    await callback.answer()
    text = '<b>Работы учеников</b>\n\n' + ('\n'.join(f"№{r['id']} <b>{html.escape(r['full_name'])}</b> · {html.escape(r['title'])}" for r in rows) if rows else 'Новых работ нет.')
    kb = [[(f"Проверить №{r['id']} · {r['full_name'][:20]}", f"submission_view:{r['id']}")] for r in rows]
    kb.append([('← Главное меню', 'menu')])
    await callback.message.answer(text, reply_markup=buttons(kb))


@router.callback_query(F.data.startswith('submission_view:'))
async def submission_view(callback: CallbackQuery, db_user: dict) -> None:
    if not await allowed(callback, db_user): return
    submission_id = int(callback.data.split(':')[1])
    row = await fetchone("""SELECT s.*,u.full_name,u.telegram_id,h.title,c.teacher_id FROM homework_submissions s
        JOIN homework h ON h.id=s.homework_id JOIN courses c ON c.id=h.course_id JOIN users u ON u.id=s.student_id
        WHERE s.id=? AND c.teacher_id=?""", (submission_id,db_user['id']))
    await callback.answer()
    if not row: return await callback.message.answer('Работа недоступна.', reply_markup=back())
    text = f"<b>{html.escape(row['title'])}</b>\nУченик: {html.escape(row['full_name'])}\n\n{html.escape(row['answer'] or 'Ответ приложен файлом.')}"
    await callback.message.answer(text, reply_markup=buttons([[('✅ Оценить', f"submission_grade:{row['id']}")], [('← К работам', 'teacher_homework')]]))
    if row['file_id']:
        try: await callback.bot.send_document(callback.from_user.id, row['file_id'])
        except Exception:
            try: await callback.bot.send_photo(callback.from_user.id, row['file_id'])
            except Exception: await callback.message.answer('Не удалось открыть приложенный файл.')


@router.callback_query(F.data.startswith('submission_grade:'))
async def submission_grade(callback: CallbackQuery, state: FSMContext, db_user: dict) -> None:
    if not await allowed(callback, db_user): return
    await state.set_state(GradeSubmissionFlow.result)
    await state.update_data(submission_id=int(callback.data.split(':')[1]))
    await callback.answer(); await callback.message.answer('Введите результат: <code>оценка | комментарий</code>\nНапример: <code>5 | Отличная работа</code>')


@router.message(GradeSubmissionFlow.result, F.text)
async def save_grade(message: Message, state: FSMContext, db_user: dict) -> None:
    if not (db_user.get('role') == 'teacher' and db_user.get('is_approved')): return
    parts = [part.strip() for part in message.text.split('|', 1)]
    grade, feedback = parts[0][:30], (parts[1][:1000] if len(parts) > 1 else '')
    if not grade: return await message.answer('Укажите оценку.')
    data = await state.get_data()
    row = await fetchone("""SELECT s.id,u.telegram_id,h.title FROM homework_submissions s JOIN homework h ON h.id=s.homework_id
        JOIN courses c ON c.id=h.course_id JOIN users u ON u.id=s.student_id WHERE s.id=? AND c.teacher_id=?""", (data['submission_id'],db_user['id']))
    if not row:
        await state.clear(); return await message.answer('Работа больше недоступна.')
    await execute('UPDATE homework_submissions SET grade=?,feedback=? WHERE id=?', (grade,feedback,row['id']))
    await state.clear(); await message.answer('Оценка сохранена ✅', reply_markup=back())
    try:
        await message.bot.send_message(row['telegram_id'], f"Ваша работа «{html.escape(row['title'])}» проверена.\nОценка: <b>{html.escape(grade)}</b>\n{html.escape(feedback)}")
    except Exception: pass
