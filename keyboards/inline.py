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


# 2. Выбор валюты
def get_currency_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="USD 🇺🇸", callback_data="cur_USD"))
    builder.add(InlineKeyboardButton(text="TJS 🇹🇯", callback_data="cur_TJS"))
    builder.add(InlineKeyboardButton(text="UZS 🇺🇿", callback_data="cur_UZS"))
    builder.add(InlineKeyboardButton(text="RUB 🇷🇺", callback_data="cur_RUB"))
    return builder.as_markup()


# 3. Выбор типа: Наличные или Электронные
def get_money_type_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💵 Наличные", callback_data="type_cash"))
    builder.add(InlineKeyboardButton(text="💻 Электронные", callback_data="type_online"))
    return builder.as_markup()


# 4. Выбор локации
def get_location_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Душанбе 🇹🇯", callback_data="loc_dushanbe"))
    builder.add(InlineKeyboardButton(text="Ташкент 🇺🇿", callback_data="loc_tashkent"))
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
