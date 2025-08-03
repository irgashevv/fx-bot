import asyncio
from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from config import ADMIN_ID
from db.database import async_session_factory
from db.models import User
from .fsm import AdminBroadcast
from keyboards.inline import get_confirm_kb

admin_router = Router()

@admin_router.message(Command("send_update"), F.from_user.id == ADMIN_ID)
async def start_broadcast(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Введите текст сообщения для рассылки.\n"
        "Вы можете использовать HTML-теги для форматирования.")
    await state.set_state(AdminBroadcast.message_text)


# Шаг 2: Получаем текст и просим подтверждение
# Добавляем фильтр прямо в декоратор
@admin_router.message(AdminBroadcast.message_text, F.from_user.id == ADMIN_ID)
async def get_broadcast_message(message: types.Message, state: FSMContext):
    await state.update_data(message_text=message.text)

    await message.answer("Вот так будет выглядеть ваше сообщение:")
    try:
        await message.answer(message.text, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❗️Ошибка форматирования: {e}\n\nПопробуйте исправить HTML-теги.")
        return

    await message.answer(
        "Начать рассылку?",
        reply_markup=get_confirm_kb()
    )
    await state.set_state(AdminBroadcast.confirm)


# Шаг 3: Подтверждение и запуск рассылки
# Добавляем фильтр прямо в декоратор
@admin_router.callback_query(F.data == "req_confirm", AdminBroadcast.confirm, F.from_user.id == ADMIN_ID)
async def confirm_broadcast(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    text_to_send = data['message_text']

    await callback.message.edit_text("⏳ Начинаю рассылку...")

    async with async_session_factory() as session:
        result = await session.execute(select(User.telegram_id))
        user_ids = result.scalars().all()

    sent_count = 0
    failed_count = 0

    for user_id in user_ids:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=text_to_send,
                parse_mode="HTML",
                disable_notification=False
            )
            sent_count += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            failed_count += 1
            print(f"Failed to send message to {user_id}: {e}")

    await callback.message.answer(
        f"✅ Рассылка завершена!\n\n"
        f"Успешно отправлено: {sent_count}\n"
        f"Не удалось отправить: {failed_count}"
    )
    await state.clear()
    await callback.answer()


@admin_router.callback_query(F.data == "req_cancel", AdminBroadcast.confirm, F.from_user.id == ADMIN_ID)
async def cancel_broadcast(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Рассылка отменена.")
    await callback.answer()
