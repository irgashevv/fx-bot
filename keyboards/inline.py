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


def get_currency_kb(exclude_currency=None):
    currencies = ["USD", "TJS", "UZS", "RUB"]
    builder = InlineKeyboardBuilder()
    for cur in currencies:
        if cur != exclude_currency:
            builder.add(InlineKeyboardButton(text=cur, callback_data=f"cur_{cur}"))
    builder.adjust(2)
    return builder.as_markup()


def get_currency_type_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💵 Наличные", callback_data="cur_type_CASH"),
        InlineKeyboardButton(text="💳 Электронные", callback_data="cur_type_ELEC"))
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
