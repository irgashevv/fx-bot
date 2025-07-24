from aiogram.fsm.state import State, StatesGroup


class CreateRequest(StatesGroup):
    request_type = State()
    currency_from = State()
    amount_from = State()
    currency_to = State()
    comment = State()
    confirm = State()
