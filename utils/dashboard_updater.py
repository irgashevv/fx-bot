from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.database import async_session_factory
from db.models import Request
from config import GROUP_ID, DASHBOARD_MESSAGE_ID

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_dashboard_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_dashboard")]
    ])


async def update_dashboard(bot: Bot):
    async with async_session_factory() as session:
        query = (
            select(Request)
            .where(Request.status == 'ACTIVE')
            .options(selectinload(Request.user))
            .order_by(Request.created_at.desc()))
        result = await session.execute(query)
        requests = result.scalars().all()

    if not requests:
        text = "<b>📊 Актуальные заявки</b>\n\nНа данный момент активных заявок нет."
    else:
        text = "<b>📊 Актуальные заявки:</b>\n\n"
        for req in requests:
            req_type_text = 'Покупка' if req.request_type == 'BUY' else 'Продажа'
            username = f"@{req.user.username}" if req.user.username else req.user.first_name

            if req.request_type == 'BUY':
                line = f"<b>Покупает:</b> <code>{req.amount_from} {req.currency_to}</code> за <code>{req.currency_from}</code>"
            else:
                line = f"<b>Продает:</b> <code>{req.amount_from} {req.currency_from}</code> за <code>{req.currency_to}</code>"

            text += (
                f"<b>#{req.id}</b> от {username}\n"
                f"   {line}\n"
                f"   <i>Комментарий:</i> {req.comment or 'Нет'}\n"
                "--------------------\n"
            )

    try:
        await bot.edit_message_text(
            text=text,
            chat_id=GROUP_ID,
            message_id=DASHBOARD_MESSAGE_ID,
            parse_mode="HTML",
            reply_markup=get_dashboard_kb())
    except Exception as e:
        print(f"Failed to update dashboard: {e}")
