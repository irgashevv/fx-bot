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


# Вспомогательная функция, чтобы не дублировать код
def parse_description(desc_str):
    try:
        parts = desc_str.replace('(', '').replace(')', '').split()
        return {'currency': parts[0], 'type': parts[1], 'location': parts[2]}
    except IndexError:
        return {'currency': '', 'type': '', 'location': ''}


async def update_dashboard(bot: Bot):
    async with async_session_factory() as session:
        query = (
            select(Request)
            .where(Request.status == 'ACTIVE')
            .options(selectinload(Request.user))
            .order_by(Request.created_at.desc())
        )
        result = await session.execute(query)
        requests = result.scalars().all()

    if not requests:
        text = "<b>Актуальные заявки</b>\n\nНа данный момент активных заявок нет."
    else:
        text_parts = ["<b>Актуальные заявки</b>"]
        for req in requests:
            author_mention = f"@{req.user.username}" if req.user.username else req.user.first_name
            formatted_amount = format_number(req.amount_from)

            op_type = req.operation_type
            action_text = ""

            # --- НАЧАЛО ИСПРАВЛЕНИЙ ---
            if op_type == 'buy':
                action = "хочет <b>КУПИТЬ</b>"
                action_text = f"{formatted_amount} {req.currency_to} в обмен на {req.currency_from}"
            elif op_type == 'sell':
                action = "хочет <b>ПРОДАТЬ</b>"
                action_text = f"{formatted_amount} {req.currency_from} в обмен на {req.currency_to}"
            else:  # transfer
                action = "хочет <b>ПЕРЕВЕСТИ</b>"
                from_details = parse_description(req.currency_from)
                to_details = parse_description(req.currency_to)

                # Собираем фразу в правильном порядке
                action_text = (f"<b>{formatted_amount} {from_details['currency']}</b> "
                               f"из г. <b>{from_details['location']}</b> ({from_details['type'].lower()}) "
                               f"в г. <b>{to_details['location']}</b> ({to_details['type'].lower()})")

            line = f"— {author_mention} {action} {action_text}."

            if req.comment:
                line += f"\n<i>Комментарий: {req.comment}</i>"
            # --- КОНЕЦ ИСПРАВЛЕНИЙ ---

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