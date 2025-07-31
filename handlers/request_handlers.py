from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import update, select, func, desc

from .fsm import CreateRequest
from keyboards.inline import (get_flow_type_kb, get_operation_type_kb, get_currency_kb, get_money_type_kb,
                              get_location_kb, get_confirm_kb, get_amount_kb)
from db.database import async_session_factory
from db.models import Request
from config import GROUP_ID
from utils.dashboard_updater import update_dashboard, format_number

fsm_router = Router()

LOCATIONS = {'dushanbe': 'Душанбе', 'tashkent': 'Ташкент', 'moscow': 'Москва'}
MONEY_TYPES = {'cash': 'наличные', 'online': 'электронные'}


def build_description(data, prefix, include_currency=True):
    currency = data.get(f'{prefix}_currency', '')

    money_type_key = data.get(f'{prefix}_money_type')
    money_type_text = MONEY_TYPES.get(money_type_key, '')

    location_key = data.get(f'{prefix}_location')
    location_text = LOCATIONS.get(location_key, '')

    parts = []
    if include_currency and currency:
        parts.append(currency)
    if money_type_text:
        parts.append(money_type_text)
    if location_text:
        parts.append(f"({location_text})")

    return " ".join(parts)


@fsm_router.message(Command("create"))
async def start_creation(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Какую операцию вы хотите совершить?", reply_markup=get_flow_type_kb())
    await state.set_state(CreateRequest.flow_type)


@fsm_router.callback_query(F.data.startswith("flow_"), CreateRequest.flow_type)
async def process_flow_type(callback: types.CallbackQuery, state: FSMContext):
    flow = callback.data.split('_')[1]
    await state.update_data(flow_type=flow)

    if flow == 'exchange':
        await callback.message.edit_text("Вы хотите купить или продать валюту?", reply_markup=get_operation_type_kb())
        await state.set_state(CreateRequest.operation_type)
    else:
        await callback.message.edit_text("Вы выбрали: Перевод денег")
        await callback.message.answer("Какую валюту вы ОТПРАВЛЯЕТЕ?", reply_markup=get_currency_kb())
        await state.set_state(CreateRequest.main_currency)
    await callback.answer()


# === ШАГ 2 (ТОЛЬКО ДЛЯ ОБМЕНА): ВЫБОР ПОКУПКИ/ПРОДАЖИ ===
@fsm_router.callback_query(F.data.startswith("op_"), CreateRequest.operation_type)
async def process_op_type(callback: types.CallbackQuery, state: FSMContext):
    op = callback.data.split('_')[1]
    await state.update_data(operation_type=op)
    action_text = "КУПИТЬ" if op == 'buy' else "ПРОДАТЬ"
    await callback.message.edit_text(f"Вы выбрали: {action_text}")
    await callback.message.answer(f"Какую валюту вы хотите {action_text}?", reply_markup=get_currency_kb())
    await state.set_state(CreateRequest.main_currency)
    await callback.answer()


# === ШАГ 3: ВВОД ДАННЫХ ОСНОВНОЙ ВАЛЮТЫ ===
@fsm_router.callback_query(F.data.startswith("cur_"), CreateRequest.main_currency)
async def process_main_currency(callback: types.CallbackQuery, state: FSMContext):
    curr = callback.data.split('_')[1]
    await state.update_data(main_currency=curr)
    await callback.message.edit_text(f"Основная валюта: {curr}")
    async with async_session_factory() as session:
        subquery = select(Request.amount_from, func.max(Request.id).label('max_id')) \
            .group_by(Request.amount_from).alias('subquery')
        query = select(subquery.c.amount_from).order_by(desc(subquery.c.max_id)).limit(4)
        result = await session.execute(query)
        amounts = [int(a) for a in result.scalars().all()]

    if not amounts:
        amounts = [100, 500, 1000, 5000]

    amount_kb = get_amount_kb(amounts)
    await callback.message.answer(
        "ВВЕДИТЕ сумму или ВЫБЕРИТЕ из популярных вариантов:",
        reply_markup=amount_kb)
    await state.set_state(CreateRequest.main_amount)
    await callback.answer()


@fsm_router.callback_query(F.data.startswith("amount_"), CreateRequest.main_amount)
async def process_main_amount_button(callback: types.CallbackQuery, state: FSMContext):
    amount = float(callback.data.split('_')[1])
    await state.update_data(main_amount=amount)

    await callback.message.edit_text(f"Сумма: {format_number(amount)}")

    await callback.message.answer("Тип денег (для этой валюты):", reply_markup=get_money_type_kb())
    await state.set_state(CreateRequest.main_money_type)
    await callback.answer()


@fsm_router.message(CreateRequest.main_amount)
async def process_main_amount_manual(message: types.Message, state: FSMContext):
    if not message.text.replace('.', '', 1).isdigit():
        return await message.answer("Пожалуйста, введите сумму только цифрами.")
    await state.update_data(main_amount=float(message.text))
    await message.answer("Тип денег (для этой валюты):", reply_markup=get_money_type_kb())
    await state.set_state(CreateRequest.main_money_type)


@fsm_router.callback_query(F.data.startswith("type_"), CreateRequest.main_money_type)
async def process_main_type(callback: types.CallbackQuery, state: FSMContext):
    m_type = callback.data.split('_')[1]
    await state.update_data(main_money_type=m_type)
    await callback.message.edit_text(f"Тип денег: {MONEY_TYPES.get(m_type)}")
    await callback.message.answer("Город (для этой валюты):", reply_markup=get_location_kb())
    await state.set_state(CreateRequest.main_location)
    await callback.answer()


# === ШАГ 4: ПЕРЕХОД К ВВОДУ ВТОРОЙ ЧАСТИ ЗАЯВКИ ===
@fsm_router.callback_query(F.data.startswith("loc_"), CreateRequest.main_location)
async def process_main_location(callback: types.CallbackQuery, state: FSMContext):
    loc = callback.data.split('_')[1]
    await state.update_data(main_location=loc)
    data = await state.get_data()

    full_desc = build_description(data, 'main')

    if data.get('flow_type') == 'exchange':
        question_text = "Теперь выберите вторую валюту для обмена:"
    else:
        question_text = "Теперь укажите тип денег для ПОЛУЧЕНИЯ:"

    await callback.message.edit_text(f"Детали: {full_desc}")

    if data.get('flow_type') == 'exchange':
        exclude_curr = data.get('main_currency')
        await callback.message.answer(question_text, reply_markup=get_currency_kb(exclude_currency=exclude_curr))
        await state.set_state(CreateRequest.secondary_currency)
    else:
        await callback.message.answer(question_text, reply_markup=get_money_type_kb())
        await state.set_state(CreateRequest.secondary_money_type)

    await callback.answer()


# === ШАГ 5: ВВОД ДАННЫХ ВТОРИЧНОЙ ВАЛЮТЫ/ЛОКАЦИИ ===
@fsm_router.callback_query(F.data.startswith("cur_"), CreateRequest.secondary_currency)
async def process_sec_currency(callback: types.CallbackQuery, state: FSMContext):
    curr = callback.data.split('_')[1]
    await state.update_data(secondary_currency=curr)
    await callback.message.edit_text(f"Вторая валюта: {curr}")
    await callback.message.answer("Тип денег (для второй валюты):", reply_markup=get_money_type_kb())
    await state.set_state(CreateRequest.secondary_money_type)
    await callback.answer()


@fsm_router.callback_query(F.data.startswith("type_"), CreateRequest.secondary_money_type)
async def process_sec_type(callback: types.CallbackQuery, state: FSMContext):
    m_type = callback.data.split('_')[1]
    await state.update_data(secondary_money_type=m_type)
    await callback.message.edit_text(f"Тип денег: {MONEY_TYPES.get(m_type)}")
    await callback.message.answer("Город (для второй валюты/локации):", reply_markup=get_location_kb())
    await state.set_state(CreateRequest.secondary_location)
    await callback.answer()


# === ШАГ 6: КОММЕНТАРИЙ И ПРЕДПРОСМОТР ===
@fsm_router.callback_query(F.data.startswith("loc_"), CreateRequest.secondary_location)
async def process_sec_location_and_ask_comment(callback: types.CallbackQuery, state: FSMContext):
    loc = callback.data.split('_')[1]
    await state.update_data(secondary_location=loc)
    data = await state.get_data()

    # Для перевода, где валюта не меняется
    if data.get('flow_type') == 'transfer':
        data['secondary_currency'] = data['main_currency']
        await state.update_data(secondary_currency=data['main_currency'])

    full_desc = build_description(data, 'secondary')
    await callback.message.edit_text(f"Детали: {full_desc}")

    await callback.message.answer("Добавьте комментарий (или отправьте `-` если его нет):")
    await state.set_state(CreateRequest.comment)
    await callback.answer()


@fsm_router.message(CreateRequest.comment)
async def process_comment_and_show_preview(message: types.Message, state: FSMContext):
    await state.update_data(comment=message.text if message.text != '-' else None)
    data = await state.get_data()
    amount = data.get('main_amount')
    formatted_amount = format_number(amount)
    main_desc = build_description(data, 'main')
    secondary_desc = build_description(data, 'secondary')

    if data.get('operation_type') == 'buy':
        # Если ПОКУПАЕМ, то основная валюта - это то, что ПОЛУЧАЕМ (TO).
        final_from = secondary_desc
        final_to = main_desc
        line1 = f"<b>Хочу купить:</b> <code>{formatted_amount} {final_to}</code>"
        line2 = f"<b>В обмен на:</b> <code>{final_from}</code>"
    else:
        # Если ПРОДАЕМ или ПЕРЕВОДИМ, то основная валюта - то, что ОТДАЕМ (FROM).
        final_from = main_desc

        if data.get('flow_type') == 'transfer':
            data['secondary_currency'] = data['main_currency']
            final_to = build_description(data, 'secondary')
            line1 = f"<b>Отправляю:</b> <code>{formatted_amount} {final_from}</code>"
            line2 = f"<b>Получаю:</b> <code>{formatted_amount} {final_to}</code>"
        else:
            final_to = secondary_desc
            line1 = f"<b>Продаю:</b> <code>{formatted_amount} {final_from}</code>"
            line2 = f"<b>Хочу получить:</b> <code>{final_to}</code>"

    await state.update_data(final_from=final_from, final_to=final_to, final_amount=amount)

    text = f"<b>Проверьте вашу заявку:</b>\n\n{line1}\n{line2}\n\n<b>Комментарий:</b> {data['comment'] or 'Нет'}"
    await message.answer(text, parse_mode="HTML", reply_markup=get_confirm_kb())
    await state.set_state(CreateRequest.confirm)


# === ШАГ 7: ПОДТВЕРЖДЕНИЕ И ПУБЛИКАЦИЯ ===
@fsm_router.callback_query(F.data == "req_confirm", CreateRequest.confirm)
async def process_final_confirm(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user = callback.from_user

    async with async_session_factory() as session:
        new_request = Request(
            user_id=user.id,
            request_type=data['flow_type'].upper(),
            currency_from=data['final_from'],
            amount_from=data['final_amount'],
            currency_to=data['final_to'],
            comment=data.get('comment'))
        session.add(new_request)
        await session.commit()
        request_id = new_request.id

    author_mention = f"@{user.username}" if user.username else user.first_name
    comment_text = f"\n<b>Комментарий:</b> {data['comment']}" if data.get('comment') else ""
    formatted_amount = format_number(data['final_amount'])

    if data['flow_type'] == 'exchange':
        flow_name_for_msg = "обмен валюты"

        if data.get('operation_type') == 'buy':
            action_text = f"купить <b>{formatted_amount} {data['final_to']}</b> в обмен на <b>{data['final_from']}</b>"
        else:
            action_text = f"продать <b>{formatted_amount} {data['final_from']}</b> в обмен на <b>{data['final_to']}</b>"

    else:
        flow_name_for_msg = "перевод денег"
        from_desc_short = build_description(data, 'main', include_currency=False)
        to_desc_short = build_description(data, 'secondary', include_currency=False)
        action_text = f"перевести <b>{formatted_amount} {data['main_currency']}</b> из <i>{from_desc_short}</i> в <i>{to_desc_short}</i>"

    group_text = (
        f"<b>Новая заявка #{request_id} на {flow_name_for_msg}</b>\n\n"
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
