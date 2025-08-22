from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, desc, func, update
from config import GROUP_ID
from aiogram.filters import StateFilter
from sqlalchemy.orm import selectinload
from aiogram.exceptions import TelegramBadRequest

from db.database import async_session_factory
from db.models import Request
from handlers.fsm import CreateRequest
from keyboards import inline
from utils.dashboard_updater import update_dashboard, format_number

router = Router()

CURRENCY_SYMBOLS = {
    'USD': '$', 'RUB': '₽', 'TJS': 'смн', 'UZS': 'сум'
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
    CreateRequest.show_matches: [],
    CreateRequest.confirm: ['final_message_text', 'comment']
}
ORDERED_STATES = list(STEPS_KEYS.keys())


def build_text_from_state(data: dict) -> str:
    parts = []
    prefix = data.get("request_type_value", "")
    amount_str = format_number(data.get("amount", 0))
    if prefix and amount_str != "0":
        parts.append(f"{prefix}{amount_str}")
    else:
        return ""
    if data.get("currency_from_key"):
        currency_code = data.get("currency_from_key")
        symbol = CURRENCY_SYMBOLS.get(currency_code, "")
        if currency_code == 'USD':
            parts[0] = f"{prefix}{symbol}{amount_str}"
        elif currency_code == 'RUB':
            parts[0] = f"{prefix}{amount_str}{symbol}"
        else:
            parts[0] = f"{prefix}{amount_str} {symbol}"
    if data.get("money_type_from_value"): parts.append(data.get("money_type_from_value"))
    if data.get("location_from_value"): parts.append(data.get("location_from_value"))
    if data.get("money_type_to_value"): parts.append(data.get("money_type_to_value"))
    if data.get("currency_to_value"): parts.append(data.get("currency_to_value"))
    if data.get("location_to_value"): parts.append(data.get("location_to_value"))
    return " ".join(parts)


async def find_matching_requests(state: FSMContext, user_id: int):
    data = await state.get_data()
    current_type = data.get("request_type_key")
    opposite_type = "give" if current_type == "take" else "take"
    async with async_session_factory() as session:
        query = (
            select(Request).where(
                Request.status == 'ACTIVE',
                Request.user_id != user_id,
                Request.request_type == opposite_type,
                Request.currency_from == data.get("currency_from_key"),
                Request.currency_to == data.get("currency_to_key"),
                Request.location_from == data.get("location_from_key"),
                Request.location_to == data.get("location_to_key"),
                Request.money_type_from == data.get("money_type_from_key"),
                Request.money_type_to == data.get("money_type_to_key"),
            ).options(selectinload(Request.user)).order_by(Request.created_at.desc())
        )
        result = await session.execute(query)
        return result.scalars().all()


async def show_request_type_step(message: types.Message, state: FSMContext, edit=False):
    text = "Выберите необходимое действие:"
    kb = inline.get_request_type_kb()
    try:
        if edit:
            await message.edit_text(text, reply_markup=kb)
        else:
            await state.clear()
            sent_message = await message.answer(text, reply_markup=kb)
            await state.update_data(editor_message_id=sent_message.message_id)
    except TelegramBadRequest:
        pass
    await state.set_state(CreateRequest.request_type)


async def show_amount_step(message: types.Message, state: FSMContext, user_id: int):
    async with async_session_factory() as session:
        subquery = select(Request.amount, func.max(Request.id).label('max_id')).where(
            Request.user_id == user_id).group_by(Request.amount).alias('subquery')
        query = select(subquery.c.amount).order_by(desc(subquery.c.max_id)).limit(4)
        result = await session.execute(query)
        amounts = [int(a) for a in result.scalars().all()]
    if not amounts: amounts = [100, 500, 1000, 5000]
    text = "Введите сумму или выберите из популярных вариантов:"
    kb = inline.get_amount_kb(amounts, back_to_state=CreateRequest.request_type.state)
    try:
        await message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass
    await state.set_state(CreateRequest.amount)


async def show_currency_from_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = build_text_from_state(data)
    kb = inline.get_currency_from_kb(back_to_state=CreateRequest.amount.state)
    try:
        await message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass
    await state.set_state(CreateRequest.currency_from)


async def show_money_type_from_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = build_text_from_state(data)
    kb = inline.get_money_type_from_kb(back_to_state=CreateRequest.currency_from.state)
    try:
        await message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass
    await state.set_state(CreateRequest.money_type_from)


async def show_location_from_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = build_text_from_state(data)
    kb = inline.get_location_from_kb(back_to_state=CreateRequest.money_type_from.state)
    try:
        await message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass
    await state.set_state(CreateRequest.location_from)


async def show_money_type_to_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = build_text_from_state(data)
    request_type = data.get("request_type_key")
    kb = inline.get_money_type_take_to_kb(
        back_to_state=CreateRequest.location_from.state) if request_type == "take" else inline.get_money_type_give_to_kb(
        back_to_state=CreateRequest.location_from.state)
    try:
        await message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass
    await state.set_state(CreateRequest.money_type_to)


async def show_currency_to_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = build_text_from_state(data)
    kb = inline.get_currency_to_kb(back_to_state=CreateRequest.money_type_to.state)
    try:
        await message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass
    await state.set_state(CreateRequest.currency_to)


async def show_location_to_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = build_text_from_state(data)
    kb = inline.get_location_to_kb(back_to_state=CreateRequest.currency_to.state)
    try:
        await message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass
    await state.set_state(CreateRequest.location_to)


async def show_matches_step(message: types.Message, state: FSMContext, user_id: int, username: str, first_name: str):
    matches = await find_matching_requests(state, user_id=user_id)
    if not matches:
        await show_confirm_step(message, state)
        return
    text_parts = ["*Мы нашли для вас подходящие заявки:*"]
    for req in matches:
        author = f"@{req.user.username}" if req.user.username else req.user.first_name
        safe_author = author.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("`", "\\`")
        safe_message = req.message_text.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("`", "\\`")
        text_parts.append(f"— *{safe_author}*: {safe_message}")
    text_parts.append("\n*Ваша заявка:*")
    data = await state.get_data()
    my_request_text = build_text_from_state(data)
    my_author = f"@{username}" if username else first_name
    safe_my_author = my_author.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("`", "\\`")
    safe_my_request_text = my_request_text.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("`",
                                                                                                               "\\`")
    text_parts.append(f"— *{safe_my_author}*: {safe_my_request_text}")
    text_parts.append("\nВсе равно создать заявку?")
    final_text = "\n\n".join(text_parts)
    kb = inline.get_show_matches_kb(back_to_state=CreateRequest.location_to.state)
    try:
        await message.edit_text(final_text, reply_markup=kb, parse_mode="MarkdownV2")
    except TelegramBadRequest:
        pass
    await state.set_state(CreateRequest.show_matches)


async def show_confirm_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    message_text = build_text_from_state(data)
    await state.update_data(final_message_text=message_text)
    comment = data.get("comment")
    final_text_for_user = f"<b>Проверьте вашу заявку:</b>\n\n<b>{message_text}</b>"
    if comment: final_text_for_user += f"\n<b>Комментарий:</b> {comment}"
    kb = inline.get_confirm_kb(back_to_state=CreateRequest.location_to.state)
    try:
        await message.edit_text(final_text_for_user, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest:
        pass
    await state.set_state(CreateRequest.confirm)


@router.callback_query(F.data.startswith("back_to_"))
async def process_back_button(callback: types.CallbackQuery, state: FSMContext):
    target_state_name = callback.data.split('_', 2)[-1]
    data = await state.get_data()

    if target_state_name == CreateRequest.location_from.state:
        money_type = data.get("money_type_from_key")
        currency = data.get("currency_from_key")
        if money_type == 'online' and currency in ['TJS', 'UZS', 'RUB']:
            target_state_name = CreateRequest.money_type_from.state

    if target_state_name == CreateRequest.location_to.state:
        money_type = data.get("money_type_to_key")
        currency = data.get("currency_to_key")
        if money_type == 'online' and currency in ['TJS', 'UZS', 'RUB']:
            target_state_name = CreateRequest.currency_to.state

    try:
        target_state_object = next(s for s in ORDERED_STATES if s.state == target_state_name)
        target_index = ORDERED_STATES.index(target_state_object)
    except (StopIteration, ValueError):
        await callback.answer("Ошибка навигации.", show_alert=True)
        return

    keys_to_delete = {key for i in range(target_index, len(ORDERED_STATES)) for key in
                      STEPS_KEYS.get(ORDERED_STATES[i], [])}
    for key in keys_to_delete:
        if key in data: del data[key]
    await state.set_data(data)

    state_map = {
        CreateRequest.request_type.state: (show_request_type_step, {}),
        CreateRequest.amount.state: (show_amount_step, {'user_id': callback.from_user.id}),
        CreateRequest.currency_from.state: (show_currency_from_step, {}),
        CreateRequest.money_type_from.state: (show_money_type_from_step, {}),
        CreateRequest.location_from.state: (show_location_from_step, {}),
        CreateRequest.money_type_to.state: (show_money_type_to_step, {}),
        CreateRequest.currency_to.state: (show_currency_to_step, {}),
        CreateRequest.location_to.state: (show_location_to_step, {}),
        CreateRequest.show_matches.state: (show_matches_step,
                                           {'user_id': callback.from_user.id, 'username': callback.from_user.username,
                                            'first_name': callback.from_user.first_name}),
        CreateRequest.confirm.state: (show_confirm_step, {}),
    }

    show_function, kwargs = state_map.get(target_state_name, (None, None))
    if show_function:
        if target_state_name == CreateRequest.request_type.state: kwargs['edit'] = True
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
    await state.update_data(amount=float(callback.data.split('_')[1]))
    await show_currency_from_step(callback.message, state)
    await callback.answer()


@router.message(CreateRequest.amount)
async def process_amount_manual(message: types.Message, state: FSMContext, bot: Bot):
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0: raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректное положительное число.")
        return

    await message.delete()

    await state.update_data(amount=amount)

    data = await state.get_data()
    editor_message_id = data.get('editor_message_id')

    if editor_message_id:
        text = build_text_from_state(data)
        kb = inline.get_currency_from_kb(back_to_state=CreateRequest.amount.state)

        try:
            await bot.edit_message_text(
                text=text,
                chat_id=message.chat.id,
                message_id=editor_message_id,
                reply_markup=kb
            )
        except TelegramBadRequest:
            pass

    await state.set_state(CreateRequest.currency_from)

@router.callback_query(F.data.startswith("currency_from_"), CreateRequest.currency_from)
async def process_currency_from(callback: types.CallbackQuery, state: FSMContext):
    currency_code = callback.data.split('_')[-1]
    currency_from_value = \
        [b.text for r in callback.message.reply_markup.inline_keyboard for b in r if b.callback_data == callback.data][
            0].replace("...", "")
    await state.update_data(currency_from_key=currency_code, currency_from_value=currency_from_value)
    await show_money_type_from_step(callback.message, state)
    await callback.answer()


@router.callback_query(F.data.startswith("money_type_from_"), CreateRequest.money_type_from)
async def process_money_type_from(callback: types.CallbackQuery, state: FSMContext):
    money_type_from_key = callback.data.split('_')[-1]
    money_type_from_value = \
        [b.text for r in callback.message.reply_markup.inline_keyboard for b in r if b.callback_data == callback.data][
            0].replace("...", "")
    await state.update_data(money_type_from_key=money_type_from_key, money_type_from_value=money_type_from_value)
    data = await state.get_data()
    currency_from = data.get("currency_from_key")
    auto_location_map = {'TJS': ('dushanbe', 'в Душанбе'), 'UZS': ('tashkent', 'в Ташкенте'),
                         'RUB': ('moscow', 'в Москве')}
    if money_type_from_key == 'online' and currency_from in auto_location_map:
        loc_key, loc_value = auto_location_map[currency_from]
        await state.update_data(location_from_key=loc_key, location_from_value=loc_value)
        await show_money_type_to_step(callback.message, state)
    else:
        await show_location_from_step(callback.message, state)
    await callback.answer()


@router.callback_query(F.data.startswith("location_"), CreateRequest.location_from)
async def process_location_from(callback: types.CallbackQuery, state: FSMContext):
    location_value = \
        [b.text for r in callback.message.reply_markup.inline_keyboard for b in r if b.callback_data == callback.data][
            0].replace("...", "")
    await state.update_data(location_from_key=callback.data.split('_')[-1].replace("location_", ""),
                            location_from_value=location_value)
    await show_money_type_to_step(callback.message, state)
    await callback.answer()


@router.callback_query(F.data.startswith("money_type_to_"), CreateRequest.money_type_to)
async def process_money_type_to(callback: types.CallbackQuery, state: FSMContext):
    money_type_to_value = \
        [b.text for r in callback.message.reply_markup.inline_keyboard for b in r if b.callback_data == callback.data][
            0].replace("...", "")
    await state.update_data(money_type_to_key=callback.data.split('_')[-1], money_type_to_value=money_type_to_value)
    await show_currency_to_step(callback.message, state)
    await callback.answer()


@router.callback_query(F.data.startswith("currency_to_"), CreateRequest.currency_to)
async def process_currency_to(callback: types.CallbackQuery, state: FSMContext):
    currency_to_key = callback.data.split('_')[-1]
    currency_to_value = \
        [b.text for r in callback.message.reply_markup.inline_keyboard for b in r if b.callback_data == callback.data][
            0].replace("...", "")
    await state.update_data(currency_to_key=currency_to_key, currency_to_value=currency_to_value)
    data = await state.get_data()
    money_type_to = data.get("money_type_to_key")
    auto_location_map = {'TJS': ('dushanbe', 'в Душанбе'), 'UZS': ('tashkent', 'в Ташкенте'),
                         'RUB': ('moscow', 'в Москве')}
    if money_type_to == 'online' and currency_to_key in auto_location_map:
        loc_key, loc_value = auto_location_map[currency_to_key]
        await state.update_data(location_to_key=loc_key, location_to_value=loc_value)
        await show_matches_step(callback.message, state, user_id=callback.from_user.id,
                                username=callback.from_user.username, first_name=callback.from_user.first_name)
    else:
        await show_location_to_step(callback.message, state)
    await callback.answer()


@router.callback_query(F.data.startswith("location_"), CreateRequest.location_to)
async def process_location_to(callback: types.CallbackQuery, state: FSMContext):
    location_to_value = \
        [b.text for r in callback.message.reply_markup.inline_keyboard for b in r if b.callback_data == callback.data][
            0].replace("...", "")
    await state.update_data(location_to_key=callback.data.split('_')[-1].replace("location_", ""),
                            location_to_value=location_to_value)
    await show_matches_step(callback.message, state, user_id=callback.from_user.id,
                            username=callback.from_user.username, first_name=callback.from_user.first_name)
    await callback.answer()


@router.callback_query(F.data == "proceed_to_confirm", CreateRequest.show_matches)
async def proceed_to_confirm(callback: types.CallbackQuery, state: FSMContext):
    await show_confirm_step(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "req_add_comment", CreateRequest.confirm)
async def process_add_comment(callback: types.CallbackQuery, state: FSMContext):
    try:
        await callback.message.edit_text(f"Отправьте текст комментария...",
                                         reply_markup=inline.get_comment_kb(back_to_state=CreateRequest.confirm.state))
    except TelegramBadRequest:
        pass
    await state.set_state(CreateRequest.comment)
    await callback.answer()


@router.message(CreateRequest.comment)
async def process_comment(message: types.Message, state: FSMContext, bot: Bot):
    await state.update_data(comment=message.text)
    await message.delete()

    data = await state.get_data()
    editor_message_id = data.get('editor_message_id')

    if editor_message_id:
        message_text = build_text_from_state(data)
        await state.update_data(final_message_text=message_text)
        comment = data.get("comment")
        final_text_for_user = f"<b>Проверьте вашу заявку:</b>\n\n<b>{message_text}</b>"
        if comment:
            final_text_for_user += f"\n<b>Комментарий:</b> {comment}"

        kb = inline.get_confirm_kb(back_to_state=CreateRequest.location_to.state)

        try:
            await bot.edit_message_text(
                text=final_text_for_user,
                chat_id=message.chat.id,
                message_id=editor_message_id,
                reply_markup=kb,
                parse_mode="HTML")
        except TelegramBadRequest:
            pass

    await state.set_state(CreateRequest.confirm)


@router.callback_query(F.data == "req_cancel",
                       StateFilter(CreateRequest.confirm, CreateRequest.comment, CreateRequest.show_matches))
async def process_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.edit_text("Действие отменено.")
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data == "req_confirm", CreateRequest.confirm)
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
    try:
        await callback.message.edit_text(f"{message_text}\n\n✅ Ваша заявка успешно создана и опубликована!")
    except TelegramBadRequest:
        pass
    await state.clear()
    await callback.answer()
