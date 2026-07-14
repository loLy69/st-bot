import asyncio
import os
import tempfile
import unittest
from pathlib import Path

tmp = tempfile.TemporaryDirectory()
os.environ.setdefault('BOT_TOKEN', '123456:TEST_TOKEN_FOR_UNIT_TESTS_ONLY')
os.environ.setdefault('ADMIN_IDS', '1')
os.environ['DB_PATH'] = str(Path(tmp.name) / 'test.db')

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mindspark_bot'))

from database.db import ensure_user, execute, fetchall, fetchone, init_db, set_user_fields


class DatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await init_db()

    async def test_user_registration(self):
        user = await ensure_user(100, 'Иван Иванов', 'ivan')
        self.assertEqual(user['role'], 'pending')
        await set_user_fields(100, role='student', is_approved=1, phone='+79990000000')
        saved = await fetchone('SELECT * FROM users WHERE telegram_id=?', (100,))
        self.assertEqual(saved['role'], 'student')
        self.assertEqual(saved['phone'], '+79990000000')

    async def test_course_lesson_booking_and_capacity_query(self):
        await ensure_user(101, 'Ученик')
        await set_user_fields(101, role='student', is_approved=1)
        student = await fetchone('SELECT * FROM users WHERE telegram_id=101')
        course_id = await execute("INSERT INTO courses(title,price_cents) VALUES('Математика',150000)")
        lesson_id = await execute("INSERT INTO lessons(course_id,starts_at,ends_at,capacity) VALUES(?,?,?,1)", (course_id,'2099-01-01 10:00','2099-01-01 11:00'))
        await execute('INSERT INTO bookings(lesson_id,student_id) VALUES(?,?)', (lesson_id,student['id']))
        row = await fetchone("SELECT COUNT(*) total FROM bookings WHERE lesson_id=? AND status='confirmed'", (lesson_id,))
        self.assertEqual(row['total'], 1)

    async def test_payment_activates_enrollment(self):
        await ensure_user(102, 'Плательщик')
        user = await fetchone('SELECT * FROM users WHERE telegram_id=102')
        course_id = await execute("INSERT INTO courses(title,subscription_price_cents) VALUES('Физика',500000)")
        payment_id = await execute("INSERT INTO payments(user_id,course_id,kind,amount_cents,status) VALUES(?,?, 'subscription',500000,'review')", (user['id'],course_id))
        await execute("UPDATE payments SET status='paid' WHERE id=?", (payment_id,))
        await execute("INSERT INTO enrollments(student_id,course_id,status) VALUES(?,?,'active')", (user['id'],course_id))
        enrollment = await fetchone('SELECT * FROM enrollments WHERE student_id=? AND course_id=?', (user['id'],course_id))
        self.assertEqual(enrollment['status'], 'active')


if __name__ == '__main__':
    unittest.main()
