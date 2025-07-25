from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from .fsm import CreateRequest
from keyboards.inline import get_request_type_kb, get_currency_kb, get_currency_type_kb, get_confirm_kb
from db.database import async_session_factory
from db.models import Request
from config import GROUP_ID

fsm_router = Router()


# Шаг 1: Начало
@fsm_router.message(Command("create"))
async def create_request_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Выберите тип заявки:", reply_markup=get_request_type_kb())
    await state.set_state(CreateRequest.request_type)


# Шаг 2: Тип заявки -> Выбор основной валюты
@fsm_router.callback_query(F.data.in_(['req_type_BUY', 'req_type_SELL']), CreateRequest.request_type)
async def process_request_type(callback: types.CallbackQuery, state: FSMContext):
    request_type = callback.data.split('_')[-1]
    await state.update_data(request_type=request_type)
    action_text = "купить" if request_type == 'BUY' else "продать"

    await callback.message.edit_text(f"Вы выбрали: {'Покупка' if request_type == 'BUY' else 'Продажа'}")
    await callback.message.answer(f"Какую валюту вы хотите {action_text}?", reply_markup=get_currency_kb())
    await state.set_state(CreateRequest.main_currency)
    await callback.answer()


# Шаг 3: Основная валюта -> Выбор типа основной валюты
@fsm_router.callback_query(F.data.startswith('cur_'), CreateRequest.main_currency)
async def process_main_currency(callback: types.CallbackQuery, state: FSMContext):
    currency = callback.data.split('_')[1]
    await state.update_data(main_currency=currency)

    await callback.message.edit_text(f"Основная валюта: {currency}")
    await callback.message.answer(f"Выберите тип для {currency}:", reply_markup=get_currency_type_kb())
    await state.set_state(CreateRequest.main_currency_type)
    await callback.answer()


# Шаг 4: Тип основной валюты -> Ввод суммы
@fsm_router.callback_query(F.data.startswith('cur_type_'), CreateRequest.main_currency_type)
async def process_main_currency_type(callback: types.CallbackQuery, state: FSMContext):
    currency_type = callback.data.split('_')[-1]
    type_text = "Наличные" if currency_type == 'CASH' else "Электронные"
    await state.update_data(main_currency_type=type_text)
    user_data = await state.get_data()

    await callback.message.edit_text(f"Тип основной валюты: {type_text}")
    await callback.message.answer(f"Какую сумму в {user_data['main_currency']} ({type_text}) вы хотите указать?")
    await state.set_state(CreateRequest.amount)
    await callback.answer()


# Шаг 5: Сумма -> Выбор второй валюты
@fsm_router.message(CreateRequest.amount)
async def process_amount(message: types.Message, state: FSMContext):
    # Проверка на число
    try:
        amount = float(message.text.replace(',', '.'))
        await state.update_data(amount=amount)
    except ValueError:
        return await message.answer("❗️Неверный формат. Введите только число.")

    user_data = await state.get_data()
    await message.answer("Выберите вторую валюту для обмена:",
                         reply_markup=get_currency_kb(exclude_currency=user_data['main_currency']))
    await state.set_state(CreateRequest.second_currency)


# Шаг 6: Вторая валюта -> Выбор типа второй валюты
@fsm_router.callback_query(F.data.startswith('cur_'), CreateRequest.second_currency)
async def process_second_currency(callback: types.CallbackQuery, state: FSMContext):
    currency = callback.data.split('_')[1]
    await state.update_data(second_currency=currency)

    await callback.message.edit_text(f"Валюта для обмена: {currency}")
    await callback.message.answer(f"Выберите тип для {currency}:", reply_markup=get_currency_type_kb())
    await state.set_state(CreateRequest.second_currency_type)
    await callback.answer()


# Шаг 7: Тип второй валюты -> Комментарий
@fsm_router.callback_query(F.data.startswith('cur_type_'), CreateRequest.second_currency_type)
async def process_second_currency_type(callback: types.CallbackQuery, state: FSMContext):
    currency_type = callback.data.split('_')[-1]
    type_text = "Наличные" if currency_type == 'CASH' else "Электронные"
    await state.update_data(second_currency_type=type_text)

    await callback.message.edit_text(f"Тип второй валюты: {type_text}")
    await callback.message.answer("Добавьте комментарий (курс, условия и т.д.)\nЕсли нет, напишите `-`")
    await state.set_state(CreateRequest.comment)
    await callback.answer()


# Шаг 8: Комментарий -> Подтверждение
@fsm_router.message(CreateRequest.comment)
async def process_comment_and_confirm(message: types.Message, state: FSMContext):
    await state.update_data(comment=message.text if message.text != '-' else None)

    data = await state.get_data()

    # Собираем полные названия валют
    main_full = f"{data['main_currency']} ({data['main_currency_type']})"
    second_full = f"{data['second_currency']} ({data['second_currency_type']})"

    if data['request_type'] == 'BUY':
        req_type_text, line1, line2 = 'Покупка', f"<b>Покупаю:</b> <code>{data['amount']} {main_full}</code>", f"<b>В обмен на:</b> <code>{second_full}</code>"
        await state.update_data(final_from=second_full, final_to=main_full, final_amount=data['amount'])
    else:  # SELL
        req_type_text, line1, line2 = 'Продажа', f"<b>Продаю:</b> <code>{data['amount']} {main_full}</code>", f"<b>Хочу получить:</b> <code>{second_full}</code>"
        await state.update_data(final_from=main_full, final_to=second_full, final_amount=data['amount'])

    text = (f"<b>Проверьте вашу заявку:</b>\n\n<b>Тип:</b> {req_type_text}\n{line1}\n{line2}\n"
            f"<b>Комментарий:</b> {data['comment'] or 'Нет'}")

    await message.answer(text, parse_mode="HTML", reply_markup=get_confirm_kb())
    await state.set_state(CreateRequest.confirm)


# Шаг 9: Сохранение и отправка
@fsm_router.callback_query(F.data == "req_confirm", CreateRequest.confirm)
async def process_final_confirm(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()

    async with async_session_factory() as session:
        new_request = Request(
            user_id=callback.from_user.id,
            request_type=data['request_type'],
            currency_from=data['final_from'],
            amount_from=data['final_amount'],
            currency_to=data['final_to'],
            comment=data.get('comment')
        )
        session.add(new_request)
        await session.commit()
        request_id = new_request.id

    group_text = callback.message.text.replace("Проверьте вашу заявку:", f"НОВАЯ ЗАЯВКА #{request_id}")
    group_text += f"\n\n<b>Автор:</b> @{callback.from_user.username or callback.from_user.first_name}"

    try:
        sent_message = await bot.send_message(chat_id=GROUP_ID, text=group_text, parse_mode="HTML")
    except Exception as e:
        print(f"Error sending to group: {e}")

    await callback.message.edit_text("✅ Ваша заявка успешно создана!")
    await state.clear()
    await callback.answer()


@fsm_router.callback_query(F.data == "req_cancel")
async def process_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Действие отменено.")
    await callback.answer()