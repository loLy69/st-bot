import html
from aiogram import F, Router
from aiogram.types import CallbackQuery
from database.db import fetchall
from keyboards.menus import back

router = Router(name='parent')


@router.callback_query(F.data == 'children')
async def children(callback: CallbackQuery, db_user: dict) -> None:
    rows = await fetchall("SELECT u.* FROM users u JOIN parent_students ps ON ps.student_id=u.id WHERE ps.parent_id=?", (db_user['id'],))
    await callback.answer()
    text = '<b>Мои дети</b>\n\n' + ('\n'.join(f"• {html.escape(r['full_name'])}" for r in rows) if rows else 'Связанных учеников пока нет. Обратитесь к администратору.')
    await callback.message.answer(text, reply_markup=back())


@router.callback_query(F.data == 'family_schedule')
async def family_schedule(callback: CallbackQuery, db_user: dict) -> None:
    rows = await fetchall("""SELECT u.full_name,c.title,l.starts_at FROM parent_students ps JOIN users u ON u.id=ps.student_id
        JOIN bookings b ON b.student_id=u.id JOIN lessons l ON l.id=b.lesson_id JOIN courses c ON c.id=l.course_id
        WHERE ps.parent_id=? AND b.status='confirmed' AND l.starts_at>CURRENT_TIMESTAMP ORDER BY l.starts_at""", (db_user['id'],))
    await callback.answer()
    text = '<b>Семейное расписание</b>\n\n' + ('\n'.join(f"• {html.escape(r['full_name'])}: {html.escape(r['title'])} — {r['starts_at']}" for r in rows) if rows else 'Предстоящих занятий нет.')
    await callback.message.answer(text, reply_markup=back())


@router.callback_query(F.data.in_({'news'}))
async def news(callback: CallbackQuery) -> None:
    rows = await fetchall('SELECT text,created_at FROM announcements ORDER BY id DESC LIMIT 10')
    await callback.answer()
    text = '<b>Новости MindSpark</b>\n\n' + ('\n\n'.join(f"{html.escape(r['text'])}\n<i>{r['created_at']}</i>" for r in rows) if rows else 'Новостей пока нет.')
    await callback.message.answer(text, reply_markup=back())
