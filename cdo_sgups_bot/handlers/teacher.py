from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram import F
from utils.formatters import format_section

router = Router()

@router.callback_query(F.data.in_(['groups','homework','schedule','progress','materials','message_group','ai_chat','main_menu']))
async def teacher_stub(callback: CallbackQuery):
    await callback.message.answer(format_section('Раздел', 'Раздел в разработке'))
    await callback.answer()
