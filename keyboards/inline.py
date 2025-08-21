from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton


def get_request_type_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Мне нужны...", callback_data="request_type_take"),
        InlineKeyboardButton(text="Я отдам...", callback_data="request_type_give"))
    return builder.as_markup()


def get_amount_kb(amounts, back_to_state: str = None):
    builder = InlineKeyboardBuilder()

    if amounts:
        for amount in amounts:
            builder.add(InlineKeyboardButton(text=str(amount), callback_data=f"amount_{amount}"))
        builder.adjust(4)

    add_back_button(builder, back_to_state)
    return builder.as_markup()


def get_currency_from_kb(back_to_state: str = None, exclude_currency=None):
    currencies = {
        "долларов...": "currency_from_USD",
        "сомони...": "currency_from_TJS",
        "сумов...": "currency_from_UZS",
        "рублей...": "currency_from_RUB"
    }

    builder = InlineKeyboardBuilder()
    for text, callback_data in currencies.items():
        if exclude_currency != callback_data.split('_')[1]:
            builder.add(InlineKeyboardButton(text=text, callback_data=callback_data))
    builder.adjust(4)

    add_back_button(builder, back_to_state)
    return builder.as_markup()


def get_money_type_from_kb(back_to_state: str = None):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="наличных...", callback_data="money_type_from_cash"),
                InlineKeyboardButton(text="безналичных...", callback_data="money_type_from_online"))

    add_back_button(builder, back_to_state)
    return builder.as_markup()


def get_location_from_kb(back_to_state: str = None):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="в Душанбе...", callback_data="location_dushanbe"),
        InlineKeyboardButton(text="в Ташкенте...", callback_data="location_tashkent"),
        InlineKeyboardButton(text="в Москве...", callback_data="location_moscow"))
    builder.adjust(1)

    add_back_button(builder, back_to_state)
    return builder.as_markup()


def get_money_type_take_to_kb(back_to_state: str = None):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="отдам наличные...", callback_data="money_type_to_cash"),
                InlineKeyboardButton(text="отдам безналичные...", callback_data="money_type_to_online"))

    add_back_button(builder, back_to_state)
    return builder.as_markup()


def get_currency_to_kb(back_to_state: str = None, exclude_currency=None):
    currencies = {
        "доллары...": "currency_to_USD",
        "сомони...": "currency_to_TJS",
        "сумы...": "currency_to_UZS",
        "рубли...": "currency_to_RUB"
    }

    builder = InlineKeyboardBuilder()
    for text, callback_data in currencies.items():
        if exclude_currency != callback_data.split('_')[1]:
            builder.add(InlineKeyboardButton(text=text, callback_data=callback_data))
    builder.adjust(4)

    add_back_button(builder, back_to_state)
    return builder.as_markup()


def get_location_to_kb(back_to_state: str = None):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="в Душанбе", callback_data="location_dushanbe"),
        InlineKeyboardButton(text="в Ташкенте", callback_data="location_tashkent"),
        InlineKeyboardButton(text="в Москве", callback_data="location_moscow"))
    builder.adjust(1)

    add_back_button(builder, back_to_state)
    return builder.as_markup()


def get_money_type_give_to_kb(back_to_state: str = None):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="нужны наличные...", callback_data="money_type_to_cash"),
                InlineKeyboardButton(text="нужны безналичные...", callback_data="money_type_to_online"))

    add_back_button(builder, back_to_state)
    return builder.as_markup()


def get_show_matches_kb(back_to_state: str = None):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Да", callback_data="proceed_to_confirm"))

    builder.add(InlineKeyboardButton(text="❌ Нет", callback_data="req_cancel"))
    if back_to_state:
        builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back_to_{back_to_state}"))
    return builder.as_markup()


def get_confirm_kb(back_to_state: str = None):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Подтвердить", callback_data="req_confirm"))
    builder.row(InlineKeyboardButton(text="💬 Добавить комментарий", callback_data="req_add_comment"))
    builder.add(InlineKeyboardButton(text="❌ Отменить", callback_data="req_cancel"))

    add_back_button(builder, back_to_state)
    return builder.as_markup()


def get_comment_kb(back_to_state: str = None):
    builder = InlineKeyboardBuilder()
    add_back_button(builder, back_to_state)
    return builder.as_markup()


def get_my_requests_kb(requests):
    builder = InlineKeyboardBuilder()
    if not requests:
        return builder.as_markup()

    for req in requests:
        builder.row(
            InlineKeyboardButton(
                text=f"❌ Закрыть заявку #{req.id}",
                callback_data=f"close_req_{req.id}"))

    return builder.as_markup()


def get_converter_currency_kb(exclude_callback=None):
    api_currencies = {
        "🇹🇯 TJS": "cur_TJS",
        "🇺🇸 USD": "cur_USD",
        "🇺🇿 UZS": "cur_UZS",
        "🇷🇺 RUB": "cur_RUB",
    }
    builder = InlineKeyboardBuilder()
    for text, callback_data in api_currencies.items():
        if callback_data != exclude_callback:
            builder.add(InlineKeyboardButton(text=text, callback_data=callback_data))
    builder.adjust(2)
    return builder.as_markup()


def get_converter_menu_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Посмотреть все курсы", callback_data="conv_menu_show_all"))
    builder.add(InlineKeyboardButton(text="🔢 Открыть конвертер", callback_data="conv_menu_open_converter"))
    return builder.as_markup()


def get_skip_comment_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➡️ Пропустить", callback_data="skip_comment"))
    return builder.as_markup()


def add_back_button(builder: InlineKeyboardBuilder, back_to_state: str):
    if back_to_state:
        builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back_to_{back_to_state}"))
