from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, update, desc, func

from .fsm import CreateRequest
from keyboards.inline import (get_flow_type_kb, get_currency_kb, get_money_type_kb,
                              get_location_kb, get_confirm_kb, get_amount_kb)
from db.database import async_session_factory
from db.models import Request
from config import GROUP_ID
from utils.dashboard_updater import update_dashboard

fsm_router = Router()
LOCATIONS = {
    'dushanbe': 'Душанбе',
    'tashkent': 'Ташкент',
    'moscow': 'Москва'
}
MONEY_TYPES = {
    'cash': 'наличные',
    'online': 'электронные'
}


def build_description(data, prefix):
    currency = data.get(f'{prefix}_currency')

    money_type_key = data.get(f'{prefix}_type')
    money_type_text = MONEY_TYPES.get(money_type_key, money_type_key)

    location_key = data.get(f'{prefix}_location')
    location_text = LOCATIONS.get(location_key, location_key.capitalize() if location_key else "")

    return f"{currency} {money_type_text} ({location_text})"


@fsm_router.message(Command("create"))
async def start_creation(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Какую операцию вы хотите совершить?", reply_markup=get_flow_type_kb())
    await state.set_state(CreateRequest.flow_type)


@fsm_router.callback_query(F.data.startswith("flow_"), CreateRequest.flow_type)
async def process_flow_type(callback: types.CallbackQuery, state: FSMContext):
    flow = callback.data.split('_')[1]
    await state.update_data(flow_type=flow)
    await callback.message.edit_text(f"Вы выбрали: {'Обмен валют' if flow == 'exchange' else 'Перевод денег'}")
    await callback.message.answer("Выберите валюту, которую ОТДАЕТЕ:", reply_markup=get_currency_kb())
    await state.set_state(CreateRequest.from_currency)
    await callback.answer()


@fsm_router.callback_query(F.data.startswith("cur_"), CreateRequest.from_currency)
async def process_from_currency(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(from_currency=callback.data.split('_')[1])
    await callback.message.edit_text(f"Валюта, которую отдаете: {callback.data.split('_')[1]}")
    await callback.message.answer("Тип денег:", reply_markup=get_money_type_kb())
    await state.set_state(CreateRequest.from_type)
    await callback.answer()


@fsm_router.callback_query(F.data.startswith("type_"), CreateRequest.from_type)
async def process_from_type(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(from_type=callback.data.split('_')[1])
    data = await state.get_data()
    await callback.message.edit_text(
        f"Отдаю: {data['from_currency']} {'Наличные' if data['from_type'] == 'cash' else 'Электронные'}")
    await callback.message.answer("Где находятся деньги?", reply_markup=get_location_kb())
    await state.set_state(CreateRequest.from_location)
    await callback.answer()


@fsm_router.callback_query(F.data.startswith("loc_"), CreateRequest.from_location)
async def process_from_location(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(from_location=callback.data.split('_')[1])
    data = await state.get_data()
    full_description = build_description(data, 'from')
    await callback.message.edit_text(f"Отдаю: {full_description}")

    # --- НОВАЯ ЛОГИКА С КНОПКАМИ СУММ ---
    async with async_session_factory() as session:
        subquery = select(Request.amount_from, func.max(Request.id).label('max_id')).group_by(
            Request.amount_from).alias('subquery')
        query = select(subquery.c.amount_from).order_by(desc(subquery.c.max_id)).limit(4)
        result = await session.execute(query)
        amounts = [int(a) for a in result.scalars().all()]

    if not amounts:
        amounts = [1000, 2000, 5000, 10000]

    amount_kb = get_amount_kb(amounts)
    await callback.message.answer(
        "Введите сумму или выберите из предложенных вариантов:",
        reply_markup=amount_kb)

    await state.set_state(CreateRequest.from_amount)
    await callback.answer()


@fsm_router.callback_query(F.data.startswith("amount_"), CreateRequest.from_amount)
async def process_from_amount_button(callback: types.CallbackQuery, state: FSMContext):
    amount = float(callback.data.split('_')[1])
    await state.update_data(from_amount=amount)
    await callback.message.edit_text(f"Сумма: {int(amount)}")

    data = await state.get_data()
    if data['flow_type'] == 'exchange':
        await callback.message.answer("Выберите валюту, которую хотите ПОЛУЧИТЬ:", reply_markup=get_currency_kb())
        await state.set_state(CreateRequest.to_currency)
    else:
        await callback.message.answer("Тип денег для получения:", reply_markup=get_money_type_kb())
        await state.set_state(CreateRequest.to_type)
    await callback.answer()


@fsm_router.message(CreateRequest.from_amount)
async def process_from_amount_manual(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Пожалуйста, введите сумму только цифрами.")

    await state.update_data(from_amount=float(message.text))

    data = await state.get_data()
    if data['flow_type'] == 'exchange':
        await message.answer("Выберите валюту, которую хотите ПОЛУЧИТЬ:", reply_markup=get_currency_kb())
        await state.set_state(CreateRequest.to_currency)
    else:
        await message.answer("Тип денег для получения:", reply_markup=get_money_type_kb())
        await state.set_state(CreateRequest.to_type)


@fsm_router.callback_query(F.data.startswith("cur_"), CreateRequest.to_currency)
async def process_to_currency_exchange(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(to_currency=callback.data.split('_')[1])
    await callback.message.edit_text(f"Валюта для получения: {callback.data.split('_')[1]}")
    await callback.message.answer("Тип денег для получения:", reply_markup=get_money_type_kb())
    await state.set_state(CreateRequest.to_type)
    await callback.answer()


@fsm_router.callback_query(F.data.startswith("type_"), CreateRequest.to_type)
async def process_to_type(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(to_type=callback.data.split('_')[1])
    data = await state.get_data()
    to_curr = data.get('to_currency') or data['from_currency']
    await callback.message.edit_text(
        f"Тип для получения: {'Наличные' if callback.data.split('_')[1] == 'cash' else 'Электронные'}")
    await callback.message.answer("Где нужны деньги?", reply_markup=get_location_kb())
    await state.set_state(CreateRequest.to_location)
    await callback.answer()


@fsm_router.callback_query(F.data.startswith("loc_"), CreateRequest.to_location)
async def process_to_location_and_prepare_confirm(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(to_location=callback.data.split('_')[1])
    await callback.message.answer("Добавьте комментарий (или `-` если нет):")
    await state.set_state(CreateRequest.comment)
    await callback.answer()


@fsm_router.message(CreateRequest.comment)
async def process_comment_and_show_preview(message: types.Message, state: FSMContext):
    await state.update_data(comment=message.text if message.text != '-' else None)
    data = await state.get_data()

    from_desc = build_description(data, 'from')
    amount = data['from_amount']

    if data['flow_type'] == 'exchange':
        flow_name = "Обмен валют"
        to_desc = build_description(data, 'to')
        line1 = f"<b>Отдаю:</b> <code>{amount} {from_desc}</code>"
        line2 = f"<b>Получаю:</b> <code>{to_desc}</code>"
    else:
        flow_name = "Перевод денег"
        data['to_currency'] = data['from_currency']
        to_desc = build_description(data, 'to')
        line1 = f"<b>Отправляю из:</b> <code>{from_desc}</code>"
        line2 = f"<b>Сумма:</b> <code>{amount} {data['from_currency']}</code>\n<b>Хочу получить в:</b> <code>{to_desc}</code>"

    text = (
        f"<b>Проверьте вашу заявку:</b>\n\n"
        f"<b>Тип операции:</b> {flow_name}\n"
        f"{line1}\n{line2}\n"
        f"<b>Комментарий:</b> {data['comment'] or 'Нет'}")

    await message.answer(text, parse_mode="HTML", reply_markup=get_confirm_kb())
    await state.set_state(CreateRequest.confirm)


@fsm_router.callback_query(F.data == "req_confirm", CreateRequest.confirm)
async def process_final_confirm(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user = callback.from_user

    from_desc = build_description(data, 'from')

    if data['flow_type'] == 'exchange':
        flow_name_for_db = "EXCHANGE"
        to_desc = build_description(data, 'to')
    else:
        flow_name_for_db = "TRANSFER"
        data['to_currency'] = data['from_currency']  # Валюта та же
        to_desc = build_description(data, 'to')

    async with async_session_factory() as session:
        new_request = Request(
            user_id=user.id,
            request_type=flow_name_for_db,
            currency_from=from_desc,
            amount_from=data['from_amount'],
            currency_to=to_desc,
            comment=data.get('comment'))
        session.add(new_request)
        await session.commit()
        request_id = new_request.id

    author_mention = f"@{user.username}" if user.username else user.first_name
    comment_text = f"\n<b>Комментарий:</b> {data['comment']}" if data.get('comment') else ""

    if data['flow_type'] == 'exchange':
        flow_name_for_msg = "Обмен Валюты"
        action_text = f"обменять <b>{data['from_amount']} {from_desc}</b> на <b>{to_desc}</b>"
    else:
        flow_name_for_msg = "Перевод Денег"
        from_type = data['from_type']
        to_type = data['to_type']
        from_location = data['from_location']
        to_location = data['to_location']

        from_type_text = MONEY_TYPES.get(from_type, from_type)
        to_type_text = MONEY_TYPES.get(to_type, to_type)
        from_location_text = LOCATIONS.get(from_location, from_location.capitalize())
        to_location_text = LOCATIONS.get(to_location, to_location.capitalize())

        action_text = (
            f"отправить <b>{data['from_amount']} {data['from_currency']}</b> ({from_type_text}) из г. {from_location_text} "
            f"и получить их как {to_type_text} в г. {to_location_text}")

    group_text = (
        f"<b>Новая заявка на {flow_name_for_msg}</b>\n\n"
        f"👤 {author_mention} хочет {action_text}.{comment_text}")

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
