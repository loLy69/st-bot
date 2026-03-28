import aiosqlite
from pathlib import Path
from config import config

DB_PATH = Path(config.db_path)

async def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('PRAGMA foreign_keys = ON')
        with open(Path(__file__).parent / 'models.py', 'r', encoding='utf-8') as f:
            schema = f.read()
        await db.executescript(schema)
        await db.commit()

async def get_user_by_telegram_id(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        row = await cursor.fetchone()
        await cursor.close()
        return dict(row) if row else None

async def create_user(telegram_id: int, role: str = 'pending', full_name: str = '', phone: str = '', grade_or_group: str = '', is_approved: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT OR IGNORE INTO users (telegram_id, role, full_name, phone, grade_or_group, is_approved) VALUES (?, ?, ?, ?, ?, ?)',
            (telegram_id, role, full_name, phone, grade_or_group, is_approved)
        )
        await db.commit()
    return await get_user_by_telegram_id(telegram_id)

async def update_user(telegram_id: int, **kwargs):
    if not kwargs:
        return
    fields = ', '.join(f"{k} = ?" for k in kwargs.keys())
    values = list(kwargs.values())
    values.append(telegram_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f'UPDATE users SET {fields} WHERE telegram_id = ?', values)
        await db.commit()

async def update_last_active(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE telegram_id = ?', (telegram_id,))
        await db.commit()

async def get_admins():
    return config.admin_ids or []
