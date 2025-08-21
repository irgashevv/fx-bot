from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from aiogram.exceptions import TelegramBadRequest

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
            .order_by(Request.created_at.asc())
        )
        result = await session.execute(query)
        requests = result.scalars().all()

    if not requests:
        text = "<b>Актуальные заявки</b>\n\nНа данный момент активных заявок нет."
    else:
        text_parts = ["<b>Актуальные заявки</b>"]
        for req in requests:
            author_mention = f"@{req.user.username}" if req.user.username else req.user.first_name

            # Собираем основной текст заявки
            line = f"— {author_mention} {req.message_text}."

            # --- НОВАЯ КРАСИВАЯ ЛОГИКА ---
            if req.group_message_id and GROUP_ID:
                chat_id_for_link = str(GROUP_ID).replace("-100", "")
                link = f"https://t.me/c/{chat_id_for_link}/{req.group_message_id}"
                # Добавляем в конец строки маленькую, аккуратную ссылку
                line += f' <a href="{link}">*тык*</a>'
            # --- КОНЕЦ НОВОЙ ЛОГИКИ ---

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
            reply_markup=get_dashboard_kb(),
            disable_web_page_preview=True
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            print(f"Failed to update dashboard: {e}")
    except Exception as e:
        print(f"Failed to update dashboard: {e}")
