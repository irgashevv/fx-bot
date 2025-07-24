from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="➕ Создать заявку"),
        ],
        [
            KeyboardButton(text="📋 Актуальные заявки"),
            KeyboardButton(text="⚙️ Мои заявки"),
        ]
    ],
    resize_keyboard=True,
    one_time_keyboard=False,
    input_field_placeholder="Выберите действие из меню")
