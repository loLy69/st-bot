import asyncio
import logging

from aiogram import Bot

from database.db import execute, fetchall

logger = logging.getLogger(__name__)


async def reminder_worker(bot: Bot) -> None:
    while True:
        try:
            rows = await fetchall("""SELECT b.id booking_id,u.telegram_id,u.full_name,c.title,l.starts_at
                FROM bookings b JOIN users u ON u.id=b.student_id JOIN lessons l ON l.id=b.lesson_id
                JOIN courses c ON c.id=l.course_id LEFT JOIN sent_notifications n ON n.booking_id=b.id AND n.kind='one_hour'
                WHERE b.status='confirmed' AND l.status='scheduled' AND n.booking_id IS NULL
                AND datetime(l.starts_at) BETWEEN datetime('now','+45 minutes') AND datetime('now','+75 minutes')""")
            for row in rows:
                try:
                    await bot.send_message(row['telegram_id'], f"⏰ Через час занятие <b>{row['title']}</b>. Начало: {row['starts_at']}")
                    await execute("INSERT OR IGNORE INTO sent_notifications(booking_id,kind) VALUES(?,'one_hour')", (row['booking_id'],))
                except Exception:
                    logger.exception('Не удалось отправить напоминание booking=%s', row['booking_id'])
        except Exception:
            logger.exception('Ошибка цикла напоминаний')
        await asyncio.sleep(60)
