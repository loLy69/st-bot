from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from database.db import get_user_by_telegram_id, create_user, update_user

class RoleCheckMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id

        if user_id is None:
            return await handler(event, data)

        user = await get_user_by_telegram_id(user_id)
        if not user:
            await create_user(telegram_id=user_id, role='pending', full_name=event.from_user.full_name or '')
            # пропускаем /start, остальные команды приведут к запросу регистрации
            if isinstance(event, Message) and event.text and event.text.strip().startswith('/start'):
                return await handler(event, data)
            if isinstance(event, Message):
                await event.answer('Привет! Для работы с ботом зарегистрируйтесь через /start')
            elif isinstance(event, CallbackQuery):
                await event.message.answer('Вы не зарегистрированы. Нажмите /start.')
            return

        if user.get('is_blocked', 0) == 1:
            msg = 'Ваш аккаунт заблокирован. Обратитесь к администратору.'
            if isinstance(event, Message):
                await event.answer(msg)
            elif isinstance(event, CallbackQuery):
                await event.message.answer(msg)
            return

        data['user_db'] = user
        data['user_role'] = user.get('role', 'pending')
        await update_user(user_id, last_active='CURRENT_TIMESTAMP')

        return await handler(event, data)
