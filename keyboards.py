from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    Keyboard = ReplyKeyboardMarkup(
        keyboard= [
            [KeyboardButton(text="Добавить привычку")],
            [KeyboardButton(text="Мои привычки")],
            [KeyboardButton(text="Редактировать привычки")],
            [KeyboardButton(text="Статистика"), KeyboardButton(text="История")],
            [KeyboardButton(text="Очистить историю")]
        ],
        resize_keyboard=True
    )
    return Keyboard