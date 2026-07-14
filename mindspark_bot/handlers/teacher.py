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
    await callback.answer()
    await callback.message.answer('Создание и проверка домашних заданий будет подключено к вашим назначенным курсам администратором.', reply_markup=back())
