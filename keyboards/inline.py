from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton


def get_request_type_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💰 Купить", callback_data="req_type_BUY"),
        InlineKeyboardButton(text="💸 Продать", callback_data="req_type_SELL"))
    return builder.as_markup()


def get_confirm_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="req_confirm"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="req_cancel"))
    return builder.as_markup()


def get_currency_kb(exclude_callback=None):
    currencies = {
        "USD Наличные (Душанбе)": "cur_USD_CASH_DYU",
        "USD Наличные (Ташкент)": "cur_USD_CASH_TAS",
        "USD Электронные (Душанбе)": "cur_USD_CARD_DYU",
        "USD Электронные (Ташкент)": "cur_USD_CARD_TAS",
        "TJS": "cur_TJS_CARD",
        "UZS": "cur_UZS_CARD",
    }

    builder = InlineKeyboardBuilder()
    for text, callback_data in currencies.items():
        if callback_data != exclude_callback:
            builder.add(InlineKeyboardButton(text=text, callback_data=callback_data))

    builder.adjust(1)

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
