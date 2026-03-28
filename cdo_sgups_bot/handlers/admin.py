from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.filters import Text
from utils.formatters import format_section

router = Router()

@router.callback_query(Text(['broadcast','students','courses','schedule','payments','news','stats','main_menu']))
async def admin_stub(callback: CallbackQuery):
    await callback.message.answer(format_section('Раздел', 'Раздел в разработке'))
    await callback.answer()
