from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import Message
import asyncio

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit=10, time_window=10):
        self.rate_limit = rate_limit
        self.time_window = time_window
        self._users = {}

    async def __call__(self, handler, event, data):
        if not isinstance(event, Message):
            return await handler(event, data)

        user_id = event.from_user.id
        now = asyncio.get_event_loop().time()
        window = self._users.get(user_id, [])
        window = [t for t in window if now - t < self.time_window]
        if len(window) >= self.rate_limit:
            return await event.answer('Слишком часто, попробуйте чуть позже.')
        window.append(now)
        self._users[user_id] = window

        return await handler(event, data)
