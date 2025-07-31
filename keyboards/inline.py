from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton


def get_confirm_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Подтвердить", callback_data="req_confirm"))
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="req_cancel"))
    return builder.as_markup()


# 1. Выбор сценария: Обмен или Перевод
def get_flow_type_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💱 Обмен валют", callback_data="flow_exchange"))
    builder.add(InlineKeyboardButton(text="💸 Перевод денег", callback_data="flow_transfer"))
    return builder.as_markup()

def get_operation_type_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💰 Хочу КУПИТЬ", callback_data="op_buy"),
        InlineKeyboardButton(text="💸 Хочу ПРОДАТЬ", callback_data="op_sell"))
    return builder.as_markup()

# 2. Выбор валюты
def get_currency_kb(exclude_currency=None):
    currencies = {"USD": "cur_USD", "TJS": "cur_TJS", "UZS": "cur_UZS", "RUB": "cur_RUB"}
    builder = InlineKeyboardBuilder()
    for text, callback_data in currencies.items():
        if exclude_currency != callback_data.split('_')[1]:
            builder.add(InlineKeyboardButton(text=text, callback_data=callback_data))
    builder.adjust(4)
    return builder.as_markup()


# 3. Выбор типа: Наличные или Электронные
def get_money_type_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💵 Наличные", callback_data="type_cash"),
                InlineKeyboardButton(text="💻 Электронные", callback_data="type_online"))
    return builder.as_markup()


# 4. Выбор локации
def get_location_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Душанбе 🇹🇯", callback_data="loc_dushanbe"),
        InlineKeyboardButton(text="Ташкент 🇺🇿", callback_data="loc_tashkent"),
        InlineKeyboardButton(text="Москва 🇷🇺", callback_data="loc_moscow"))
    builder.adjust(3)
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


def get_amount_kb(amounts):
    builder = InlineKeyboardBuilder()

    if amounts:
        for amount in amounts:
            builder.add(InlineKeyboardButton(text=str(amount), callback_data=f"amount_{amount}"))
        builder.adjust(4)

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


def get_converter_operation_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Купить", callback_data="conv_op_BUY"),
        InlineKeyboardButton(text="Продать", callback_data="conv_op_SELL"))
    return builder.as_markup()


def get_converter_menu_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Посмотреть все курсы", callback_data="conv_menu_show_all"))
    builder.add(InlineKeyboardButton(text="🔢 Открыть конвертер", callback_data="conv_menu_open_converter"))
    return builder.as_markup()
