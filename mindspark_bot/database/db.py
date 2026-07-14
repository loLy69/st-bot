from pathlib import Path
from typing import Any

import aiosqlite

from config import config
from database.models import SCHEMA


def _path() -> Path:
    path = Path(config.db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


async def connect() -> aiosqlite.Connection:
    db = await aiosqlite.connect(_path())
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    await db.execute("PRAGMA busy_timeout = 5000")
    return db


async def init_db() -> None:
    db = await connect()
    try:
        await db.executescript(SCHEMA)
        await db.commit()
    finally:
        await db.close()


async def fetchone(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    db = await connect()
    try:
        cursor = await db.execute(query, params)
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def fetchall(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    db = await connect()
    try:
        cursor = await db.execute(query, params)
        return [dict(row) for row in await cursor.fetchall()]
    finally:
        await db.close()


async def execute(query: str, params: tuple[Any, ...] = ()) -> int:
    db = await connect()
    try:
        cursor = await db.execute(query, params)
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def get_user(telegram_id: int) -> dict[str, Any] | None:
    return await fetchone("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))


async def ensure_user(telegram_id: int, full_name: str, username: str = "") -> dict[str, Any]:
    await execute(
        """INSERT INTO users(telegram_id, full_name, username) VALUES(?,?,?)
        ON CONFLICT(telegram_id) DO UPDATE SET full_name=excluded.full_name,
        username=excluded.username, updated_at=CURRENT_TIMESTAMP""",
        (telegram_id, full_name, username),
    )
    user = await get_user(telegram_id)
    assert user is not None
    return user


async def set_user_fields(telegram_id: int, **fields: Any) -> None:
    allowed = {"full_name", "phone", "role", "is_approved", "is_blocked"}
    clean = {key: value for key, value in fields.items() if key in allowed}
    if not clean:
        return
    values = list(clean.values()) + [telegram_id]
    setters = ", ".join(f"{key} = ?" for key in clean)
    await execute(f"UPDATE users SET {setters}, updated_at=CURRENT_TIMESTAMP WHERE telegram_id = ?", tuple(values))
