from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, desc, func, update
from config import GROUP_ID
from aiogram.filters import StateFilter

from db.database import async_session_factory
from db.models import Request
from handlers.fsm import CreateRequest
from keyboards import inline
from utils.dashboard_updater import update_dashboard, format_number

router = Router()

CURRENCY_SYMBOLS = {
    'USD': '$',
    'RUB': '₽',
    'TJS': 'смн',
    'UZS': 'сум'
}

STEPS_KEYS = {
    CreateRequest.request_type: ['request_type_key', 'request_type_value'],
    CreateRequest.amount: ['amount'],
    CreateRequest.currency_from: ['currency_from_key', 'currency_from_value'],
    CreateRequest.money_type_from: ['money_type_from_key', 'money_type_from_value'],
    CreateRequest.location_from: ['location_from_key', 'location_from_value'],
    CreateRequest.money_type_to: ['money_type_to_key', 'money_type_to_value'],
    CreateRequest.currency_to: ['currency_to_key', 'currency_to_value'],
    CreateRequest.location_to: ['location_to_key', 'location_to_value'],
    CreateRequest.confirm: ['final_message_text', 'comment']
}

ORDERED_STATES = list(STEPS_KEYS.keys())


def build_text_from_state(data: dict) -> str:
    """Централизованная функция для построения текста заявки из данных состояния."""
    parts = []
    prefix = data.get("request_type_value", "")
    amount_str = format_number(data.get("amount", 0))

    # 1. Тип и сумма (база)
    if prefix and amount_str != "0":
        parts.append(f"{prefix}{amount_str}")
    else:  # Если данных еще нет, возвращаем пустую строку
        return ""

    # 2. Валюта "от"
    if data.get("currency_from_key"):
        currency_code = data.get("currency_from_key")
        symbol = CURRENCY_SYMBOLS.get(currency_code, "")
        if currency_code == 'USD':
            parts[0] = f"{prefix}{symbol}{amount_str}"
        elif currency_code == 'RUB':
            parts[0] = f"{prefix}{amount_str}{symbol}"
        else:
            parts[0] = f"{prefix}{amount_str} {symbol}"

    # 3. Тип денег "от"
    if data.get("money_type_from_value"): parts.append(data.get("money_type_from_value"))
    # 4. Локация "от"
    if data.get("location_from_value"): parts.append(data.get("location_from_value"))
    # 5. Тип денег "к"
    if data.get("money_type_to_value"): parts.append(data.get("money_type_to_value"))
    # 6. Валюта "к"
    if data.get("currency_to_value"): parts.append(data.get("currency_to_value"))
    # 7. Локация "к"
    if data.get("location_to_value"): parts.append(data.get("location_to_value"))

    return " ".join(parts)


async def show_request_type_step(message: types.Message, state: FSMContext, edit=False):
    text = "Выберите необходимое действие:"
    kb = inline.get_request_type_kb()
    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await state.clear()
        sent_message = await message.answer(text, reply_markup=kb)
        await state.update_data(editor_message_id=sent_message.message_id)
    await state.set_state(CreateRequest.request_type)


async def show_amount_step(message: types.Message, state: FSMContext, user_id: int):
    async with async_session_factory() as session:
        subquery = select(Request.amount, func.max(Request.id).label('max_id')).where(
            Request.user_id == user_id).group_by(
            Request.amount).alias('subquery')
        query = select(subquery.c.amount).order_by(desc(subquery.c.max_id)).limit(4)
        result = await session.execute(query)
        amounts = [int(a) for a in result.scalars().all()]
    if not amounts:
        amounts = [100, 500, 1000, 5000]

    text = "Введите сумму или выберите из популярных вариантов:"
    kb = inline.get_amount_kb(amounts, back_to_state=CreateRequest.request_type.state)
    await message.edit_text(text, reply_markup=kb)
    await state.set_state(CreateRequest.amount)


async def show_currency_from_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = build_text_from_state(data)
    kb = inline.get_currency_from_kb(back_to_state=CreateRequest.amount.state)
    await message.edit_text(text, reply_markup=kb)
    await state.set_state(CreateRequest.currency_from)


async def show_money_type_from_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = build_text_from_state(data)
    kb = inline.get_money_type_from_kb(back_to_state=CreateRequest.currency_from.state)
    await message.edit_text(text, reply_markup=kb)
    await state.set_state(CreateRequest.money_type_from)


async def show_location_from_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = build_text_from_state(data)
    kb = inline.get_location_from_kb(back_to_state=CreateRequest.money_type_from.state)
    await message.edit_text(text, reply_markup=kb)
    await state.set_state(CreateRequest.location_from)


async def show_money_type_to_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = build_text_from_state(data)
    request_type = data.get("request_type_key")
    if request_type == "take":
        kb = inline.get_money_type_take_to_kb(back_to_state=CreateRequest.location_from.state)
    else:
        kb = inline.get_money_type_give_to_kb(back_to_state=CreateRequest.location_from.state)
    await message.edit_text(text, reply_markup=kb)
    await state.set_state(CreateRequest.money_type_to)


async def show_currency_to_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = build_text_from_state(data)
    kb = inline.get_currency_to_kb(back_to_state=CreateRequest.money_type_to.state)
    await message.edit_text(text, reply_markup=kb)
    await state.set_state(CreateRequest.currency_to)


async def show_location_to_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = build_text_from_state(data)
    kb = inline.get_location_to_kb(back_to_state=CreateRequest.currency_to.state)
    await message.edit_text(text, reply_markup=kb)
    await state.set_state(CreateRequest.location_to)
    await state.set_state(CreateRequest.location_to)


async def show_confirm_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    message_text = build_text_from_state(data)
    await state.update_data(final_message_text=message_text)

    comment = data.get("comment")
    final_text_for_user = f"<b>Проверьте вашу заявку:</b>\n\n<b>{message_text}</b>"
    if comment:
        final_text_for_user += f"\n<b>Комментарий:</b> {comment}"

    kb = inline.get_confirm_kb(back_to_state=CreateRequest.location_to.state)
    await message.edit_text(final_text_for_user, reply_markup=kb, parse_mode="HTML")
    await state.set_state(CreateRequest.confirm)


@router.callback_query(F.data.startswith("back_to_"))
async def process_back_button(callback: types.CallbackQuery, state: FSMContext):
    target_state_name = callback.data.split('_', 2)[-1]

    # --- ЛОГИКА ОЧИСТКИ БУДУЩИХ ДАННЫХ ---
    data = await state.get_data()

    # --- ИСПРАВЛЕННЫЙ БЛОК ---
    try:
        # Находим объект состояния в нашем списке по его строковому имени
        target_state_object = next(s for s in ORDERED_STATES if s.state == target_state_name)
        # Находим индекс этого объекта в списке
        target_index = ORDERED_STATES.index(target_state_object)
    except (StopIteration, ValueError):
        # Если такого состояния нет в нашем списке, ничего не делаем
        await callback.answer("Ошибка навигации.", show_alert=True)
        return
    # --- КОНЕЦ ИСПРАВЛЕННОГО БЛОКА ---

    # Собираем все ключи, которые нужно удалить (все, что идут ПОСЛЕ нашего целевого шага)
    keys_to_delete = set()
    for i in range(target_index, len(ORDERED_STATES)):
        state_to_clear = ORDERED_STATES[i]
        keys_to_delete.update(STEPS_KEYS.get(state_to_clear, []))

    # Удаляем эти ключи из данных состояния
    for key in keys_to_delete:
        if key in data:
            del data[key]

    # Сохраняем очищенные данные обратно в FSM
    await state.set_data(data)

    # --- КОНЕЦ ЛОГИКИ ОЧИСТКИ ---

    # Карта для вызова нужной show-функции
    state_map = {
        CreateRequest.request_type.state: (show_request_type_step, {}),
        CreateRequest.amount.state: (show_amount_step, {'user_id': callback.from_user.id}),
        CreateRequest.currency_from.state: (show_currency_from_step, {}),
        CreateRequest.money_type_from.state: (show_money_type_from_step, {}),
        CreateRequest.location_from.state: (show_location_from_step, {}),
        CreateRequest.money_type_to.state: (show_money_type_to_step, {}),
        CreateRequest.currency_to.state: (show_currency_to_step, {}),
        CreateRequest.location_to.state: (show_location_to_step, {}),
        CreateRequest.confirm.state: (show_confirm_step, {}),
    }

    show_function, kwargs = state_map.get(target_state_name, (None, None))

    if show_function:
        if target_state_name == CreateRequest.request_type.state:
            kwargs['edit'] = True
        await show_function(callback.message, state, **kwargs)

    await callback.answer()


@router.message(F.text == "➕ Создать заявку")
async def start_request(message: types.Message, state: FSMContext):
    await show_request_type_step(message, state)


@router.callback_query(F.data.startswith("request_type_"), CreateRequest.request_type)
async def process_request_type(callback: types.CallbackQuery, state: FSMContext):
    request_type_key = callback.data.split('_')[-1]
    request_type_value = "Мне нужны " if request_type_key == 'take' else "Я отдам "
    await state.update_data(request_type_key=request_type_key, request_type_value=request_type_value)

    await show_amount_step(callback.message, state, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data.startswith("amount_"), CreateRequest.amount)
async def process_amount_callback(callback: types.CallbackQuery, state: FSMContext):
    amount = float(callback.data.split('_')[1])
    await state.update_data(amount=amount)
    await show_currency_from_step(callback.message, state)
    await callback.answer()


@router.message(CreateRequest.amount)
async def process_amount_manual(message: types.Message, state: FSMContext, bot: Bot):
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0: raise ValueError
    except ValueError:
        return await message.answer("Пожалуйста, введите корректное положительное число.")

    await state.update_data(amount=amount)

    # Редактируем исходное сообщение бота
    data = await state.get_data()
    editor_message_id = data.get('editor_message_id')
    if editor_message_id:
        # Создаем "ненастоящий" объект message для передачи в show_... функцию
        editor_message = types.Message(message_id=editor_message_id, chat=message.chat)
        await show_currency_from_step(editor_message, state)

    await message.delete()


@router.callback_query(F.data.startswith("currency_from_"), CreateRequest.currency_from)
async def process_currency_from(callback: types.CallbackQuery, state: FSMContext):
    currency_code = callback.data.split('_')[-1]
    currency_from_value = [
        btn.text for row in callback.message.reply_markup.inline_keyboard for btn in row
        if btn.callback_data == callback.data
    ][0].replace("...", "")

    await state.update_data(currency_from_key=currency_code, currency_from_value=currency_from_value)
    await show_money_type_from_step(callback.message, state)
    await callback.answer()


@router.callback_query(F.data.startswith("money_type_from_"), CreateRequest.money_type_from)
async def process_money_type_from(callback: types.CallbackQuery, state: FSMContext):
    money_type_from_value = [
        btn.text for row in callback.message.reply_markup.inline_keyboard for btn in row
        if btn.callback_data == callback.data
    ][0].replace("...", "")

    await state.update_data(
        money_type_from_key=callback.data.split('_')[-1],
        money_type_from_value=money_type_from_value,
    )
    await show_location_from_step(callback.message, state)
    await callback.answer()


@router.callback_query(F.data.startswith("location_"), CreateRequest.location_from)
async def process_location_from(callback: types.CallbackQuery, state: FSMContext):
    location_value = [
        btn.text for row in callback.message.reply_markup.inline_keyboard for btn in row
        if btn.callback_data == callback.data
    ][0].replace("...", "")

    await state.update_data(
        location_from_key=callback.data.split('_')[-1],
        location_from_value=location_value,
    )
    await show_money_type_to_step(callback.message, state)
    await callback.answer()


@router.callback_query(F.data.startswith("money_type_to_"), CreateRequest.money_type_to)
async def process_money_type_to(callback: types.CallbackQuery, state: FSMContext):
    money_type_to_value = [
        btn.text for row in callback.message.reply_markup.inline_keyboard for btn in row
        if btn.callback_data == callback.data
    ][0].replace("...", "")

    await state.update_data(
        money_type_to_key=callback.data.split('_')[-1],
        money_type_to_value=money_type_to_value,
    )
    await show_currency_to_step(callback.message, state)
    await callback.answer()


@router.callback_query(F.data.startswith("currency_to_"), CreateRequest.currency_to)
async def process_currency_to(callback: types.CallbackQuery, state: FSMContext):
    currency_to_value = [
        btn.text for row in callback.message.reply_markup.inline_keyboard for btn in row
        if btn.callback_data == callback.data
    ][0].replace("...", "")

    await state.update_data(
        currency_to_key=callback.data.split('_')[-1],
        currency_to_value=currency_to_value,
    )
    await show_location_to_step(callback.message, state)
    await callback.answer()


@router.callback_query(F.data.startswith("location_"), CreateRequest.location_to)
async def process_location_to(callback: types.CallbackQuery, state: FSMContext):
    location_to_value = [
        btn.text for row in callback.message.reply_markup.inline_keyboard for btn in row
        if btn.callback_data == callback.data
    ][0].replace("...", "")

    await state.update_data(
        location_to_key=callback.data.split('_')[-1],
        location_to_value=location_to_value,
    )
    await show_confirm_step(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "req_add_comment", CreateRequest.confirm)
async def process_add_comment(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        f"Отправьте текст комментария...",
    )
    await state.set_state(CreateRequest.comment)
    await callback.answer()


@router.message(CreateRequest.comment)
async def process_comment(message: types.Message, state: FSMContext):
    await state.update_data(comment=message.text)

    await message.delete()

    data = await state.get_data()
    message_text = data.get("message_text")
    comment = data.get("comment")
    final_text = f"<b>Проверьте вашу заявку:</b>\n\n<b>{message_text}</b>\n<b>Комментарий:</b> {comment}"
    kb = inline.get_confirm_kb(back_to_state=CreateRequest.location_to.state)
    await message.answer(final_text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(CreateRequest.confirm)


@router.callback_query(F.data == "req_cancel", StateFilter(CreateRequest.confirm, CreateRequest.comment))
async def process_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Действие отменено.")
    await callback.answer()


@router.callback_query(F.data == "req_final_confirm", CreateRequest.confirm)
async def process_final_confirm(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user = callback.from_user
    message_text = data.get("final_message_text")
    comment = data.get('comment')

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
            comment=comment,
            message_text=message_text
        )
        session.add(new_request)
        await session.commit()
        request_id = new_request.id

    author_mention = f"@{user.username}" if user.username else user.first_name
    group_text = f"<b>Новая заявка от:</b> 👤 {author_mention}\n\n{message_text}"
    if comment:
        group_text += f"\n<i>Комментарий: {comment}</i>"

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
