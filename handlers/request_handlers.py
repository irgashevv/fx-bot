from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import update

from .fsm import CreateRequest
from keyboards.inline import get_request_type_kb, get_currency_kb, get_confirm_kb
from db.database import async_session_factory
from db.models import Request
from config import GROUP_ID
from utils.dashboard_updater import update_dashboard

fsm_router = Router()


@fsm_router.message(Command("create"))
async def create_request_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Выберите тип вашей заявки:", reply_markup=get_request_type_kb())
    await state.set_state(CreateRequest.request_type)


@fsm_router.callback_query(F.data.in_(['req_type_BUY', 'req_type_SELL']), CreateRequest.request_type)
async def process_request_type(callback: types.CallbackQuery, state: FSMContext):
    request_type = callback.data.split('_')[-1]
    await state.update_data(request_type=request_type)

    action_text = "купить" if request_type == 'BUY' else "продать"

    await callback.message.edit_text(f"Вы выбрали: {'Покупка' if request_type == 'BUY' else 'Продажа'}")
    await callback.message.answer(f"Какую валюту вы хотите {action_text}?", reply_markup=get_currency_kb())
    await state.set_state(CreateRequest.currency_from)  # Состояние теперь означает "основная валюта"
    await callback.answer()


@fsm_router.callback_query(F.data.startswith('cur_'), CreateRequest.currency_from)
async def process_main_currency(callback: types.CallbackQuery, state: FSMContext):
    currency_text = [btn.text for row in callback.message.reply_markup.inline_keyboard for btn in row if
                     btn.callback_data == callback.data][0]
    await state.update_data(main_currency=currency_text, main_currency_callback=callback.data)

    await callback.message.edit_text(f"Основная валюта: {currency_text}")
    await callback.message.answer(f"Какую сумму в {currency_text} вы хотите указать?")
    await state.set_state(CreateRequest.amount_from)  # Состояние теперь означает "сумма основной валюты"
    await callback.answer()


@fsm_router.message(CreateRequest.amount_from)
async def process_main_amount(message: types.Message, state: FSMContext):
    if not message.text or not all(c.isdigit() or c in '.,' for c in message.text) or message.text.count(
            '.') > 1 or message.text.count(',') > 1:
        await message.answer("❗️Неверный формат суммы. Введите только число.")
        return
    try:
        amount = float(message.text.replace(',', '.'))
        await state.update_data(main_amount=amount)
    except ValueError:
        await message.answer("❗️Неверный формат суммы. Введите только число.")
        return
    user_data = await state.get_data()
    exclude_cb = user_data.get('main_currency_callback')
    reply_markup = get_currency_kb(exclude_callback=exclude_cb)
    await message.answer("Выберите вторую валюту для обмена:", reply_markup=reply_markup)

    await state.set_state(CreateRequest.currency_to)


@fsm_router.callback_query(F.data.startswith('cur_'), CreateRequest.currency_to)
async def process_second_currency(callback: types.CallbackQuery, state: FSMContext):
    currency_text = [btn.text for row in callback.message.reply_markup.inline_keyboard for btn in row if
                     btn.callback_data == callback.data][0]
    await state.update_data(second_currency=currency_text)

    await callback.message.edit_text(f"Валюта для обмена: {currency_text}")
    await callback.message.answer("Добавьте комментарий (курс, условия и т.д.)\nЕсли комментария нет, напишите `-`")
    await state.set_state(CreateRequest.comment)
    await callback.answer()


@fsm_router.message(CreateRequest.comment)
async def process_comment_and_confirm(message: types.Message, state: FSMContext):
    await state.update_data(comment=message.text if message.text != '-' else None)

    data = await state.get_data()

    if data['request_type'] == 'BUY':
        currency_from = data['second_currency']
        amount_from = '???'
        currency_to = data['main_currency']
        amount_to = data['main_amount']
        req_type_text = 'Покупка'
        preview_line_1 = f"<b>Хочу купить:</b> <code>{amount_to} {currency_to}</code>"
        preview_line_2 = f"<b>В обмен на:</b> <code>{currency_from}</code>"
    else:
        currency_from = data['main_currency']
        amount_from = data['main_amount']
        currency_to = data['second_currency']
        preview_line_1 = f"<b>Продаю:</b> <code>{amount_from} {currency_from}</code>"
        preview_line_2 = f"<b>Хочу получить:</b> <code>{currency_to}</code>"
        req_type_text = 'Продажа'

    await state.update_data(
        final_currency_from=currency_from,
        final_amount_from=amount_from if isinstance(amount_from, (int, float)) else 0,  # Для БД нужен float
        final_currency_to=currency_to)

    text = (
        f"<b>Проверьте вашу заявку:</b>\n\n"
        f"<b>Тип:</b> {req_type_text}\n"
        f"{preview_line_1}\n"
        f"{preview_line_2}\n"
        f"<b>Комментарий:</b> {data['comment'] or 'Нет'}")

    await message.answer(text, parse_mode="HTML", reply_markup=get_confirm_kb())
    await state.set_state(CreateRequest.confirm)


@fsm_router.callback_query(F.data == "req_confirm", CreateRequest.confirm)
async def process_final_confirm(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()

    async with async_session_factory() as session:
        new_request = Request(
            user_id=callback.from_user.id,
            request_type=data['request_type'],
            currency_from=data['final_currency_from'],
            amount_from=data['final_amount_from'],
            currency_to=data['final_currency_to'],
            comment=data.get('comment'))
        session.add(new_request)
        await session.commit()
        request_id = new_request.id

    group_text = callback.message.text.replace("Проверьте вашу заявку:", f"НОВАЯ ЗАЯВКА #{request_id}")
    group_text += f"\n\n<b>Автор:</b> @{callback.from_user.username or callback.from_user.first_name}"

    try:
        sent_message = await bot.send_message(chat_id=GROUP_ID, text=group_text, parse_mode="HTML")
        async with async_session_factory() as session:
            await session.execute(
                update(Request).where(Request.id == request_id).values(group_message_id=sent_message.message_id))
            await session.commit()
        await update_dashboard(bot)
    except Exception as e:
        print(f"Error sending to group: {e}")

    await callback.message.edit_text("✅ Ваша заявка успешно создана и опубликована!")
    await state.clear()
    await callback.answer()


@fsm_router.callback_query(F.data == "req_cancel", CreateRequest.confirm)
async def process_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Действие отменено.")
    await callback.answer()
