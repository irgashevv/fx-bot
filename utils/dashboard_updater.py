from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.database import async_session_factory
from db.models import Request
from config import GROUP_ID, DASHBOARD_MESSAGE_ID
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def format_number(num):
    try:
        return f"{int(float(num)):,}".replace(",", " ")
    except (ValueError, TypeError):
        return str(num)


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
        )
        result = await session.execute(query)
        requests = result.scalars().all()

    if not requests:
        text = "<b>Актуальные заявки</b>\n\nНа данный момент активных заявок нет."
    else:
        text_parts = ["<b>Актуальные заявки</b>"]
        for req in requests:
            author_mention = f"@{req.user.username}" if req.user.username else req.user.first_name

            line = f"— {author_mention} {req.message_text}."

            if req.comment:
                line += f"\n<i>Комментарий: {req.comment}</i>"

            text_parts.append(line)

        text = "\n\n".join(text_parts)

    try:
        await bot.edit_message_text(
            text=text,
            chat_id=GROUP_ID,
            message_id=DASHBOARD_MESSAGE_ID,
            parse_mode="HTML",
            reply_markup=get_dashboard_kb()
        )
    except Exception as e:
        print(f"Failed to update dashboard: {e}")