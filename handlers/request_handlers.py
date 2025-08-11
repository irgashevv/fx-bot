from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, desc, func, update
from config import GROUP_ID

from db.database import async_session_factory
from db.models import Request
from handlers.fsm import CreateRequest
from keyboards.inline import (
    get_request_type_kb, get_constructor_amount_kb,
    get_currency_from_kb, get_location_from_kb, get_location_to_kb,
    get_money_type_from_kb, get_money_type_give_to_kb,
    get_currency_to_kb, get_money_type_take_to_kb,
    get_confirm_kb
)
from utils.dashboard_updater import update_dashboard, format_number

constructor_router = Router()

CURRENCY_SYMBOLS = {
    'USD': '$',
    'RUB': '₽',
    'TJS': 'смн',
    'UZS': 'сум'
}


@constructor_router.message(F.text == "➕ Создать заявку")
async def start_request(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Выберите необходимое действие: ", reply_markup=get_request_type_kb())
    await state.set_state(CreateRequest.request_type)


@constructor_router.callback_query(F.data.startswith("request_type_"), CreateRequest.request_type)
async def process_constructor_type(callback: types.CallbackQuery, state: FSMContext):
    request_type_key = callback.data.split('_')[-1]
    request_type_value = "Мне нужны " if request_type_key == 'take' else "Я отдам "
    user_id = callback.from_user.id

    await state.update_data(request_type_key=request_type_key)
    await state.update_data(request_type_value=request_type_value)
    await state.update_data(message_text=request_type_value)

    async with (async_session_factory() as session):
        subquery = select(Request.amount, func.max(Request.id).label('max_id')).where(
            Request.user_id == user_id).group_by(
            Request.amount).alias('subquery')
        query = select(subquery.c.amount).order_by(desc(subquery.c.max_id)).limit(4)
        result = await session.execute(query)
        amounts = [int(a) for a in result.scalars().all()]

    if not amounts:
        amounts = [100, 500, 1000, 5000]

    amount_kb = get_constructor_amount_kb(amounts)
    await callback.message.edit_text("Введите сумму или выберите из популярных вариантов:", reply_markup=amount_kb)

    await state.set_state(CreateRequest.amount)
    await callback.answer()


@constructor_router.callback_query(F.data.startswith("amount_"), CreateRequest.amount)
async def process_amount(callback: types.CallbackQuery, state: FSMContext):
    amount = format_number(callback.data.split('_')[1])
    data = await state.get_data()
    message_text = data.get("message_text")
    message_text += amount

    await state.update_data(amount=callback.data.split('_')[1])
    await state.update_data(message_text=message_text)

    await callback.message.edit_text(message_text, reply_markup=get_currency_from_kb())
    await state.set_state(CreateRequest.currency_from)
    await callback.answer()


@constructor_router.message(CreateRequest.amount)
async def process_amount_manual(message: types.Message, state: FSMContext):
    if not message.text.replace('.', '', 1).isdigit():
        return await message.answer("Пожалуйста, введите сумму только цифрами.")

    data = await state.get_data()
    amount = float(message.text)
    amount = format_number(amount)
    message_text = data.get("message_text")
    message_text += amount

    await state.update_data(amount=float(message.text))
    await state.update_data(message_text=message_text)

    await message.answer(message_text, reply_markup=get_currency_from_kb())
    await state.set_state(CreateRequest.currency_from)


@constructor_router.callback_query(F.data.startswith("currency_from_"), CreateRequest.currency_from)
async def process_currency_from(callback: types.CallbackQuery, state: FSMContext):
    currency_code = callback.data.split('_')[-1]
    data = await state.get_data()

    message_text_prefix = data.get("request_type_value")
    amount_formatted = format_number(data.get("amount"))
    symbol = CURRENCY_SYMBOLS.get(currency_code, currency_code)
    currency_from_value = [
        btn.text
        for row in callback.message.reply_markup.inline_keyboard
        for btn in row
        if btn.callback_data == callback.data
    ][0]
    currency_from_value = currency_from_value.replace(".", "")
    if currency_code == 'USD':
        new_message_text = f"{message_text_prefix}{symbol}{amount_formatted}"
    elif currency_code == 'RUB':
        new_message_text = f"{message_text_prefix}{amount_formatted}{symbol}"
    else:
        new_message_text = f"{message_text_prefix}{amount_formatted} {symbol}"

    await state.update_data(currency_from_value=currency_from_value)
    await state.update_data(currency_from_key=callback.data.split('_')[-1])
    await state.update_data(message_text=new_message_text)

    await callback.message.edit_text(new_message_text, reply_markup=get_money_type_from_kb())
    await state.set_state(CreateRequest.money_type_from)
    await callback.answer()


@constructor_router.callback_query(F.data.startswith("money_type_from_"), CreateRequest.money_type_from)
async def process_money_type_from(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    message_text = data.get("message_text")
    money_type_from_value = [
        btn.text
        for row in callback.message.reply_markup.inline_keyboard
        for btn in row
        if btn.callback_data == callback.data
    ][0]
    money_type_from_value = money_type_from_value.replace(".", "")
    message_text = message_text + " " + money_type_from_value

    await state.update_data(money_type_from_key=callback.data.split('_')[-1])
    await state.update_data(money_type_from_value=money_type_from_value)
    await state.update_data(message_text=message_text)

    await callback.message.edit_text(message_text, reply_markup=get_location_from_kb())
    await state.set_state(CreateRequest.location_from)
    await callback.answer()


@constructor_router.callback_query(F.data.startswith("location_"), CreateRequest.location_from)
async def process_location_from(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    message_text = data.get("message_text")
    main_location_value = [
        btn.text
        for row in callback.message.reply_markup.inline_keyboard
        for btn in row
        if btn.callback_data == callback.data
    ][0]
    request_type = data.get("request_type_key")
    main_location_value = main_location_value.replace(".", "")

    if request_type == "take":
        message_text = message_text + " " + main_location_value
    elif request_type == "give":
        message_text = message_text + " " + main_location_value

    await state.update_data(location_from_key=callback.data.split('_')[-1])
    await state.update_data(location_from_value=main_location_value)
    await state.update_data(message_text=message_text)

    if request_type == "take":
        await callback.message.edit_text(message_text, reply_markup=get_money_type_take_to_kb())
        await state.set_state(CreateRequest.money_type_to)
        await callback.answer()
    elif request_type == "give":
        await callback.message.edit_text(message_text, reply_markup=get_money_type_give_to_kb())
        await state.set_state(CreateRequest.money_type_to)
        await callback.answer()


@constructor_router.callback_query(F.data.startswith("money_type_to_"), CreateRequest.money_type_to)
async def process_secondary_money_type(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    message_text = data.get("message_text")
    money_type_to_value = [
        btn.text
        for row in callback.message.reply_markup.inline_keyboard
        for btn in row
        if btn.callback_data == callback.data
    ][0]

    money_type_to_value = money_type_to_value.replace(".", "")
    message_text = message_text + " " + money_type_to_value

    await state.update_data(money_type_to_key=callback.data.split('_')[-1])
    await state.update_data(money_type_to_value=money_type_to_value)
    await state.update_data(message_text=message_text)

    await callback.message.edit_text(message_text, reply_markup=get_currency_to_kb())
    await state.set_state(CreateRequest.currency_to)
    await callback.answer()


@constructor_router.callback_query(F.data.startswith("currency_to_"), CreateRequest.currency_to)
async def process_currency_to(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    message_text = data.get("message_text")
    currency_to_value = [
        btn.text
        for row in callback.message.reply_markup.inline_keyboard
        for btn in row
        if btn.callback_data == callback.data
    ][0]
    currency_to_value = currency_to_value.replace(".", "")
    message_text = message_text + " " + currency_to_value

    await state.update_data(currency_to_key=callback.data.split('_')[-1])
    await state.update_data(currency_to_value=currency_to_value)
    await state.update_data(message_text=message_text)

    await callback.message.edit_text(message_text, reply_markup=get_location_to_kb())
    await state.set_state(CreateRequest.location_to)
    await callback.answer()


@constructor_router.callback_query(F.data.startswith("location_"), CreateRequest.location_to)
async def process_location_to(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    message_text = data.get("message_text")
    location_to_value = [
        btn.text
        for row in callback.message.reply_markup.inline_keyboard
        for btn in row
        if btn.callback_data == callback.data
    ][0]
    location_to_value = location_to_value.replace(".", "")

    message_text = message_text + " " + location_to_value

    await state.update_data(location_to_key=callback.data.split('_')[-1])
    await state.update_data(location_to_value=location_to_value)
    await state.update_data(message_text=message_text)

    await callback.message.edit_text(
        f"<b>{message_text}</b>",
        reply_markup=get_confirm_kb(),
        parse_mode="HTML")

    await state.set_state(CreateRequest.confirm)
    await callback.answer()


@constructor_router.callback_query(F.data == "req_add_comment", CreateRequest.confirm)
async def process_add_comment(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        f"Отправьте текст комментария...",
        parse_mode="HTML")
    await state.set_state(CreateRequest.comment)


@constructor_router.message(CreateRequest.comment)
async def process_comment(message: types.Message, state: FSMContext):
    data = await state.get_data()
    message_text = data.get("message_text")
    comment = message.text

    await state.update_data(comment=comment)
    await state.update_data(message_text=message_text)

    await message.answer(
        f"<b>Проверьте вашу заявку:</b>\n\n<b>{message_text}\nКомментарий:</b> {comment}",
        parse_mode="HTML",
        reply_markup=get_confirm_kb())
    await state.set_state(CreateRequest.confirm)


@constructor_router.callback_query(F.data == "req_cancel", CreateRequest.confirm)
async def process_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Действие отменено.")
    await callback.answer()


@constructor_router.callback_query(F.data == "req_confirm", CreateRequest.confirm)
async def process_final_confirm(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()

    user = callback.from_user
    message_text = data.get("message_text")

    async with async_session_factory() as session:
        new_request = Request(
            user_id=user.id,
            request_type=data.get("request_type_key"),
            currency_from=data.get("currency_from_key"),
            money_type_from=data.get("money_type_from_key"),
            location_from=data.get("location_from_key"),
            amount=data.get("amount"),
            currency_to=data.get("currency_to_key"),
            money_type_to=data.get("money_type_to_key"),
            location_to=data.get("location_to_key"),
            comment=data.get('comment'),
            message_text=data.get("message_text"))
        session.add(new_request)
        await session.commit()
        request_id = new_request.id

    author_mention = f"@{user.username}" if user.username else user.first_name

    group_text = (
        f"<b>Новая заявка от:</b> 👤 {author_mention}\n\n"
        f"{message_text}")

    if data.get('comment'):
        group_text += f"\n<i>Комментарий: {data.get('comment')}</i>"

    try:
        sent_message = await bot.send_message(chat_id=GROUP_ID, text=group_text, parse_mode="HTML")
        async with async_session_factory() as session:
            await session.execute(
                update(Request).where(Request.id == request_id).values(group_message_id=sent_message.message_id))
            await session.commit()
        await update_dashboard(bot)
    except Exception as e:
        print(f"Error sending to group: {e}")

    await callback.message.edit_text(f"{message_text}\n\n✅ Ваша заявка успешно создана и опубликована!")
    await state.clear()
    await callback.answer()
