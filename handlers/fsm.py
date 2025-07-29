from aiogram.fsm.state import State, StatesGroup


class CreateRequest(StatesGroup):
    flow_type = State()
    comment = State()
    confirm = State()

    from_currency = State()
    from_type = State()
    from_location = State()
    from_amount = State()

    to_currency = State()
    to_type = State()
    to_location = State()


class CurrencyConverter(StatesGroup):
    from_currency = State()
    to_currency = State()
    amount = State()


class AdminBroadcast(StatesGroup):
    message_text = State()
    confirm = State()
