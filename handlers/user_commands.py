from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.database import async_session_factory
from db.models import User, Request
from keyboards.reply import main_kb
from keyboards.inline import get_my_requests_kb
from config import GROUP_ID
from utils.dashboard_updater import update_dashboard, get_dashboard_kb, format_number

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = (f"Здравствуйте, {message.from_user.first_name}!\n\n"
                    "Я бот для создания заявок на обмен валют.\n\n"
                    "Используйте кнопки ниже для навигации.")
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if user is None:
            new_user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name)
            session.add(new_user)
            await session.commit()
    await message.answer(welcome_text, reply_markup=main_kb)


@router.message(Command("list"))
async def list_active_requests(message: types.Message):
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
        await message.answer("На данный момент нет активных заявок.")
        return

    text_parts = ["<b>Актуальные заявки</b>"]
    for req in requests:
        author_mention = f"@{req.user.username}" if req.user.username else req.user.first_name

        # Собираем основной текст
        line = f"— {author_mention} {req.message_text}."

        # --- ТАКАЯ ЖЕ КРАСИВАЯ ЛОГИКА ---
        if req.group_message_id and GROUP_ID:
            chat_id_for_link = str(GROUP_ID).replace("-100", "")
            link = f"https://t.me/c/{chat_id_for_link}/{req.group_message_id}"
            line += f' <a href="{link}">*тык*</a>'
        # --- КОНЕЦ ЛОГИКИ ---

        if req.comment:
            line += f"\n<i>Комментарий: {req.comment}</i>"

        text_parts.append(line)

    text = "\n\n".join(text_parts)
    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)


@router.message(F.text == "📋 Актуальные заявки")
async def handle_list_requests(message: types.Message):
    await list_active_requests(message)


@router.message(Command("my"))
async def my_active_requests(message: types.Message):
    async with async_session_factory() as session:
        query = select(Request).where(
            Request.user_id == message.from_user.id,
            Request.status == 'ACTIVE'
        ).order_by(Request.created_at.desc())
        result = await session.execute(query)
        requests = result.scalars().all()

    if not requests:
        await message.answer("У вас нет активных заявок.")
        return

    text = "<b>Ваши активные заявки:</b>\n\n"
    for req in requests:

        text += (
            f"<b>Заявка номер {req.id}</b>\n"
            f"{req.message_text}\n\n")

    await message.answer(text, parse_mode="HTML", reply_markup=get_my_requests_kb(requests))


@router.message(F.text == "⚙️ Мои заявки")
async def handle_my_requests(message: types.Message):
    await my_active_requests(message)


@router.callback_query(F.data.startswith("close_req_"))
async def close_request(callback: types.CallbackQuery, bot: Bot):
    request_id = int(callback.data.split('_')[-1])

    async with async_session_factory() as session:
        result = await session.execute(
            select(Request)
            .where(Request.id == request_id)
            .options(selectinload(Request.user)))
        request_to_close = result.scalar_one_or_none()

        if not request_to_close or request_to_close.user_id != callback.from_user.id:
            return await callback.answer("Это не ваша заявка или она не найдена.", show_alert=True)

        if request_to_close.status == 'CLOSED':
            await callback.message.delete()
            return await callback.answer("Эта заявка уже закрыта.", show_alert=True)

        request_to_close.status = 'CLOSED'
        await session.commit()

    if request_to_close and request_to_close.group_message_id:
        try:
            req = request_to_close
            author_mention = f"@{req.user.username}" if req.user.username else req.user.first_name

            original_body = f"👤 {author_mention} {req.message_text}"
            if req.comment:
                original_body += f"\n<b>Комментарий:</b> {req.comment}"

            final_text = (
                f"<s>{original_body}</s>\n\n"
                f"<b>--- Не актуально ---</b>")

            await bot.edit_message_text(
                text=final_text,
                chat_id=GROUP_ID,
                message_id=request_to_close.group_message_id,
                parse_mode="HTML")
        except Exception as e:
            print(f"Could not edit group message for closed request #{request_id}: {e}")

    await update_dashboard(bot)
    await callback.message.delete()
    await callback.message.answer(f"✅ Заявка #{request_id} успешно закрыта.")
    await callback.answer()


@router.message(Command("post_dashboard"))
async def post_dashboard_command(message: types.Message, bot: Bot):
    try:
        sent_message = await bot.send_message(
            chat_id=GROUP_ID,
            text="Загрузка данных...",
            reply_markup=get_dashboard_kb())
        await message.answer(f"Сообщение для дашборда отправлено.\n"
                             f"ID Сообщения: `{sent_message.message_id}`\n"
                             f"Теперь закрепите его и впишите ID в .env файл.",
                             parse_mode="Markdown")
        await update_dashboard(bot)
    except Exception as e:
        await message.answer(f"Ошибка при отправке дашборда: {e}")


@router.callback_query(F.data == "refresh_dashboard")
async def refresh_dashboard_callback(callback: types.CallbackQuery, bot: Bot):
    await update_dashboard(bot)
    await callback.answer("Дашборд обновлен!")
