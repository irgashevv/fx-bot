from aiogram.fsm.state import State, StatesGroup


class CreateRequest(StatesGroup):
    request_type = State()  # Тип заявки (купить/продать)
    main_currency = State()  # Основная валюта (USD, TJS...)
    main_currency_type = State()  # Тип основной валюты (наличные/электронные)
    amount = State()  # Сумма основной валюты
    second_currency = State()  # Вторая валюта
    second_currency_type = State()  # Тип второй валюты
    comment = State()  # Комментарий
    confirm = State()  # Подтверждение
