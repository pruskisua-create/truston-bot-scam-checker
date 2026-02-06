from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard():
    keyboard = [
        [KeyboardButton(text="🔍 Проверить пользователя")],
        [KeyboardButton(text="📊 Статистика базы")],
        [KeyboardButton(text="❓ Справка")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_admin_keyboard():
    keyboard = [
        [KeyboardButton(text="🔍 Проверить пользователя")],
        [KeyboardButton(text="➕ Добавить запись"), KeyboardButton(text="🗑️ Удалить запись")],
        [KeyboardButton(text="📁 Массовая загрузка"), KeyboardButton(text="📋 Все записи")],
        [KeyboardButton(text="📊 Статистика базы"), KeyboardButton(text="❓ Справка")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_threat_level_keyboard():
    buttons = [
        [InlineKeyboardButton(text="✅ Проверенный", callback_data="threat_1")],
        [InlineKeyboardButton(text="⚠️ Требует осторожности", callback_data="threat_2")],
        [InlineKeyboardButton(text="🚨 Мошенник", callback_data="threat_3")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_delete_keyboard(user_id):
    buttons = [
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"delete_confirm_{user_id}")],
        [InlineKeyboardButton(text="❌ Нет, отменить", callback_data=f"delete_cancel_{user_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cancel_keyboard():
    keyboard = [[KeyboardButton(text="Отмена")]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_confirm_keyboard():
    buttons = [
        [InlineKeyboardButton(text="✅ Да, импортировать", callback_data="confirm_yes")],
        [InlineKeyboardButton(text="❌ Нет, отменить", callback_data="confirm_no")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)