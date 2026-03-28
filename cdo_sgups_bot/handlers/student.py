from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.filters import Text
from utils.formatters import format_section

router = Router()

@router.callback_query(Text(['enroll','cabinet','homework','payment','news','trial','ai_chat','profile']))
async def student_stub(callback: CallbackQuery):
    await callback.message.answer(format_section('Раздел', 'Раздел в разработке'))
    await callback.answer()
