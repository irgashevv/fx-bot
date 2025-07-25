from aiogram.fsm.state import State, StatesGroup


class CreateRequest(StatesGroup):
    # Общие
    flow_type = State()
    comment = State()
    confirm = State()

    # Секция "ОТДАЮ"
    from_currency = State()
    from_type = State()
    from_location = State()
    from_amount = State()

    # Секция "ПОЛУЧАЮ"
    to_currency = State()
    to_type = State()
    to_location = State()
