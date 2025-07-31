from aiogram.fsm.state import State, StatesGroup


class CreateRequest(StatesGroup):
    flow_type = State()
    operation_type = State()

    main_currency = State()
    main_amount = State()
    main_money_type = State()
    main_location = State()

    secondary_currency = State()
    secondary_money_type = State()
    secondary_location = State()

    comment = State()
    confirm = State()


class CurrencyConverter(StatesGroup):
    from_currency = State()
    to_currency = State()
    amount = State()


class AdminBroadcast(StatesGroup):
    message_text = State()
    confirm = State()
