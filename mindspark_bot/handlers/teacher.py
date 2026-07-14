import html
from aiogram import F, Router
from aiogram.types import CallbackQuery
from database.db import fetchall
from keyboards.menus import back

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
    text = '<b>Работы учеников</b>\n\n' + ('\n\n'.join(f"№{r['id']} <b>{html.escape(r['full_name'])}</b>\n{html.escape(r['title'])}: {html.escape(r['answer'] or 'приложен файл')}" for r in rows) if rows else 'Новых работ нет.')
    await callback.message.answer(text, reply_markup=back())
