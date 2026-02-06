from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard():
    keyboard = [
        [KeyboardButton(text="🔍 Проверить")],
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="❓ Справка")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_admin_keyboard():
    keyboard = [
        [KeyboardButton(text="🔍 Проверить")],
        [KeyboardButton(text="➕ Добавить"), KeyboardButton(text="📋 Все записи")],
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="❓ Справка")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_cancel_keyboard():
    keyboard = [[KeyboardButton(text="❌ Отмена")]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)