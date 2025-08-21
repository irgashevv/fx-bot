from aiogram.fsm.state import State, StatesGroup


class CreateRequest(StatesGroup):
    request_type = State()

    amount = State()
    currency_from = State()
    money_type_from = State()
    location_from = State()

    money_type_to = State()
    currency_to = State()
    location_to = State()

    show_matches = State()
    comment = State()
    confirm = State()

class CurrencyConverter(StatesGroup):
    from_currency = State()
    to_currency = State()
    amount = State()


class AdminBroadcast(StatesGroup):
    message_text = State()
    confirm = State()
