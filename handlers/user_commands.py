from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.database import async_session_factory
from db.models import User, Request
from keyboards.reply import main_kb
from keyboards.inline import get_my_requests_kb
from config import GROUP_ID
from .request_handlers import start_creation
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
            .order_by(Request.created_at.desc()))
        result = await session.execute(query)
        requests = result.scalars().all()

    if not requests:
        await message.answer("На данный момент нет активных заявок.")
        return

    text = "<b>Актуальные заявки:</b>\n\n"
    for req in requests:
        req_type_text = 'Покупка' if req.request_type == 'BUY' else 'Продажа'
        username = f"@{req.user.username}" if req.user.username else req.user.first_name
        formatted_amount = format_number(req.amount_from) # <-- ФОРМАТИРУЕМ

        preview_line_1 = f"<b>Покупает:</b> <code>{formatted_amount} {req.currency_to}</code>" if req.request_type == 'BUY' else f"<b>Продает:</b> <code>{req.amount_from} {formatted_amount}</code>"
        preview_line_2 = f"<b>В обмен на:</b> <code>{formatted_amount}</code>" if req.request_type == 'BUY' else f"<b>Хочет получить:</b> <code>{req.currency_to}</code>"

        text += (
            f"<b>Заявка #{req.id}</b> от {username}\n"
            f"<b>Тип:</b> {req_type_text}\n"
            f"{preview_line_1}\n"
            f"{preview_line_2}\n"
            f"<b>Комментарий:</b> {req.comment or 'Нет'}\n"
            "--------------------\n")
    await message.answer(text, parse_mode="HTML")


@router.message(Command("my"))
async def my_active_requests(message: types.Message):
    async with async_session_factory() as session:
        query = select(Request).where(
            Request.user_id == message.from_user.id,
            Request.status == 'ACTIVE').order_by(Request.created_at.desc())
        result = await session.execute(query)
        requests = result.scalars().all()

    if not requests:
        await message.answer("У вас нет активных заявок.")
        return

    text = "<b>Ваши активные заявки:</b>\n\n"
    for req in requests:
        preview_line_1 = f"Покупаю: {req.amount_from} {req.currency_to}" if req.request_type == 'BUY' else f"Продаю: {req.amount_from} {req.currency_from}"
        text += (
            f"<b>Заявка #{req.id}</b>\n"
            f"{preview_line_1}\n"
            "--------------------\n")
    await message.answer(text, parse_mode="HTML", reply_markup=get_my_requests_kb(requests))


@router.message(F.text == "➕ Создать заявку")
async def handle_create_request(message: types.Message, state: FSMContext):
    await start_creation(message, state)


@router.message(F.text == "📋 Актуальные заявки")
async def handle_list_requests(message: types.Message):
    await list_active_requests(message)


@router.message(F.text == "⚙️ Мои заявки")
async def handle_my_requests(message: types.Message):
    await my_active_requests(message)


@router.callback_query(F.data.startswith("close_req_"))
async def close_request(callback: types.CallbackQuery, bot: Bot):
    request_id = int(callback.data.split('_')[-1])

    request_to_close = None

    # Блок 1: Работа с базой данных
    async with async_session_factory() as session:
        result = await session.execute(
            select(Request)
            .where(Request.id == request_id)
            .options(selectinload(Request.user))
        )
        request_to_close = result.scalar_one_or_none()

        if not request_to_close or request_to_close.user_id != callback.from_user.id:
            return await callback.answer("Это не ваша заявка или она не найдена.", show_alert=True)

        if request_to_close.status == 'CLOSED':
            await callback.message.delete()  # Удаляем кнопки, если заявка уже закрыта
            return await callback.answer("Эта заявка уже закрыта.", show_alert=True)

        request_to_close.status = 'CLOSED'
        await session.commit()

    if request_to_close and request_to_close.group_message_id:
        try:
            original_message = await bot.get_chat_member(GROUP_ID, bot.id)

            req = request_to_close
            author_mention = f"@{req.user.username}" if req.user.username else req.user.first_name
            comment_text = f"\n<b>Комментарий:</b> {req.comment}" if req.comment else ""

            if req.request_type == 'EXCHANGE':
                flow_name_for_msg = "обмен валюты"
                action_text = f"обменять <b>{req.amount_from} {req.currency_from}</b> на <b>{req.currency_to}</b>"
            else:
                from_clean = req.currency_from.replace('"', '')
                to_clean = req.currency_to.replace('"', '')
                flow_name_for_msg = "перевод денег"
                action_text = f"перевести <b>{req.amount_from}</b> из <b>{from_clean}</b> в <b>{to_clean}</b>"

            original_body = (f"👤 {author_mention} хочет {action_text}.{comment_text}")

            final_text = (
                f"<s><b>Новая заявка на {flow_name_for_msg}</b>\n\n"
                f"{original_body}</s>\n\n"
                f"<b>--- СДЕЛКА ЗАВЕРШЕНА ---</b>")

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
