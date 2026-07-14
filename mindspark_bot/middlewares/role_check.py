from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from config import config
from database.db import ensure_user, set_user_fields


class RoleCheckMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: dict[str, Any]) -> Any:
        sender = data.get('event_from_user')
        if sender:
            user = await ensure_user(sender.id, sender.full_name or 'Пользователь', sender.username or '')
            if sender.id in config.admin_ids and (user['role'] != 'admin' or not user['is_approved']):
                await set_user_fields(sender.id, role='admin', is_approved=1)
                user['role'], user['is_approved'] = 'admin', 1
            data['db_user'] = user
        return await handler(event, data)
