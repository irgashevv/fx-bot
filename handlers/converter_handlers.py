import requests
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

from .fsm import CurrencyConverter
from keyboards.inline import get_converter_currency_kb, get_converter_menu_kb

converter_router = Router()


def get_alif_rates_new():
    url = "https://alif.tj/api/rates"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        rates = {}
        if "localRates" in data:
            for currency_data in data["localRates"]:
                name = currency_data.get("name")
                if name in ["USD", "RUB", "EUR", "UZS", "KZT"]:
                    rates[name] = {
                        "buy": float(currency_data.get("buyValue", 0)),
                        "sell": float(currency_data.get("sellValue", 0)),
                    }
        rates['TJS'] = {'buy': 1.0, 'sell': 1.0}
        return rates
    except Exception as e:
        print(f"Could not get new Alif rates: {e}")
        return None


def calculate_cross_conversion(amount, from_curr, to_curr, rates):
    if not rates or from_curr not in rates or to_curr not in rates:
        return None, None

    if from_curr == to_curr:
        return amount, 1.0

    amount_in_tjs = amount * rates[from_curr]['buy']

    result_amount = amount_in_tjs / rates[to_curr]['sell']

    direct_rate = rates[from_curr]['buy'] / rates[to_curr]['sell']

    return round(result_amount, 2), round(direct_rate, 4)


@converter_router.callback_query(F.data == "conv_menu_open_converter")
async def convert_start(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer(
        "Выберите исходную валюту (что отдаете):",
        reply_markup=get_converter_currency_kb())
    await callback.message.delete()  # Удаляем старое меню
    await state.set_state(CurrencyConverter.from_currency)
    await callback.answer()


@converter_router.callback_query(F.data.startswith('cur_'), CurrencyConverter.from_currency)
async def process_from_currency(callback: types.CallbackQuery, state: FSMContext):
    from_curr_code = callback.data.split('_')[1]
    currency_text = [btn.text for row in callback.message.reply_markup.inline_keyboard for btn in row if
                     btn.callback_data == callback.data][0]
    await state.update_data(from_currency=from_curr_code)

    await callback.message.edit_text(f"Исходная валюта: {currency_text}")
    await callback.message.answer(
        "Теперь выберите целевую валюту (что получаете):",
        reply_markup=get_converter_currency_kb(exclude_callback=callback.data))
    await state.set_state(CurrencyConverter.to_currency)
    await callback.answer()


@converter_router.message(F.text == "💱 Курсы валют")
@converter_router.message(Command("rates"))
async def show_converter_menu(message: types.Message):
    await message.answer(
        "Выберите действие:",
        reply_markup=get_converter_menu_kb())


@converter_router.callback_query(F.data == "conv_menu_show_all")
async def show_all_rates(callback: types.CallbackQuery):
    await callback.message.edit_text("⏳ Получаю актуальные курсы от Алиф Банка...")

    all_rates = get_alif_rates_new()

    if all_rates:
        text = "<b>Курсы валют Алиф Банка (относительно TJS)</b>\n\n"
        for curr in ["USD", "EUR", "RUB", "UZS", "KZT"]:
            if curr in all_rates:
                rate = all_rates[curr]
                text += f"<b>{curr}:</b>\n"
                text += f"  Покупка: <code>{rate['buy']}</code>\n"
                text += f"  Продажа: <code>{rate['sell']}</code>\n\n"

        await callback.message.edit_text(text, parse_mode="HTML")
    else:
        await callback.message.edit_text("❌ Не удалось получить курсы. Попробуйте позже.")

    await callback.answer()


@converter_router.callback_query(F.data.startswith('cur_'), CurrencyConverter.to_currency)
async def process_to_currency(callback: types.CallbackQuery, state: FSMContext):
    to_curr_code = callback.data.split('_')[1]
    currency_text = [btn.text for row in callback.message.reply_markup.inline_keyboard for btn in row if
                     btn.callback_data == callback.data][0]
    await state.update_data(to_currency=to_curr_code)

    data = await state.get_data()
    from_curr = data['from_currency']

    await callback.message.edit_text(f"Целевая валюта: {currency_text}")
    await callback.message.answer(f"Введите сумму в {from_curr}, которую хотите сконвертировать:")
    await state.set_state(CurrencyConverter.amount)
    await callback.answer()


@converter_router.message(CurrencyConverter.amount)
async def process_amount_and_calculate(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(',', '.'))
    except (ValueError, TypeError):
        await message.answer("❗️Неверный формат. Пожалуйста, введите только число.")
        return

    data = await state.get_data()
    from_curr = data['from_currency']
    to_curr = data['to_currency']

    await message.answer("⏳ Считаю курс по данным Алиф Банка...")

    all_rates = get_alif_rates_new()

    result_amount, direct_rate = calculate_cross_conversion(amount, from_curr, to_curr, all_rates)

    if result_amount is not None:
        await message.answer(
            f"✅ Результат:\n"
            f"<code>{amount} {from_curr} = {result_amount} {to_curr}</code>\n\n"
            f"<i>Кросс-курс: 1 {from_curr} ≈ {direct_rate} {to_curr}</i>",
            parse_mode="HTML")
    else:
        await message.answer("❌ Не удалось получить или рассчитать курс. Попробуйте позже.")

    await state.clear()
