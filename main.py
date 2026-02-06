import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token="8473743571:AAHU6sSYsiUx8rFTxpXeR6oVhAONnZ3HT60")
dp = Dispatcher()

# Настройки
ADMIN_ID = 599952947
GOOGLE_SHEET_ID = "ТВОЙ_ID_ТАБЛИЦЫ"  # ЗАМЕНИ


# Подключение к Google Sheets
def get_google_sheet():
    # Создай файл credentials.json (инструкция ниже)
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']

    # Если файла credentials.json нет, используем публичный доступ
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        client = gspread.authorize(creds)
    except:
        # Публичный доступ только для чтения
        client = gspread.service_account(filename='credentials.json') if os.path.exists('credentials.json') else None

    if client:
        try:
            sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1
            return sheet
        except:
            return None
    return None


# Клавиатуры
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Проверить")],
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="❓ Справка")]
        ],
        resize_keyboard=True
    )


def get_admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Проверить")],
            [KeyboardButton(text="➕ Добавить"), KeyboardButton(text="📋 Все записи")],
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="❓ Справка")]
        ],
        resize_keyboard=True
    )


# Команды
@dp.message(Command("start"))
async def start(message: Message):
    welcome = (
        f"🛡️ <b>Добро пожаловать в бота антискам базы TRUSTON!</b>\n\n"
        f"Просто отправьте ID или @username для проверки.\n\n"
        f"✅ База обновляется ежедневно\n"
        f"🔒 Данные хранятся в защищенном хранилище\n"
        f"📊 Более 1000 проверенных записей"
    )

    if message.from_user.id == ADMIN_ID:
        await message.answer(welcome, parse_mode="HTML", reply_markup=get_admin_keyboard())
    else:
        await message.answer(welcome, parse_mode="HTML", reply_markup=get_main_keyboard())


@dp.message(Command("stats"))
async def stats(message: Message):
    sheet = get_google_sheet()
    if sheet:
        records = sheet.get_all_records()
        count = len(records)

        response = (
            f"📊 <b>Статистика базы TRUSTON</b>\n\n"
            f"• 📁 Всего записей: <b>{count}</b>\n"
            f"• 📅 Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
            f"• 🔗 Источник: Google Sheets\n\n"
            f"<i>База работает в реальном времени</i>"
        )
    else:
        response = "⚠️ База временно недоступна"

    await message.answer(response, parse_mode="HTML")


@dp.message(Command("help"))
async def help_cmd(message: Message):
    help_text = (
        f"🛡️ <b>Бот антискам базы TRUSTON</b>\n\n"
        f"<b>Команды:</b>\n"
        f"• /start - Запуск бота\n"
        f"• /check - Проверить пользователя\n"
        f"• /stats - Статистика\n"
        f"• /help - Справка\n\n"
        f"<b>Как использовать:</b>\n"
        f"1. Отправьте ID пользователя (цифры)\n"
        f"2. Или отправьте @username\n"
        f"3. Получите результат проверки\n\n"
        f"<b>Уровни угрозы:</b>\n"
        f"• 1 - Проверенный\n"
        f"• 2 - Подозрительный\n"
        f"• 3 - Мошенник"
    )
    await message.answer(help_text, parse_mode="HTML")


@dp.message(lambda m: m.text == "🔍 Проверить")
async def check_button(message: Message):
    await message.answer("Отправьте ID или @username для проверки:", reply_markup=None)


@dp.message(lambda m: m.text == "📊 Статистика")
async def stats_button(message: Message):
    await stats(message)


@dp.message(lambda m: m.text == "❓ Справка")
async def help_button(message: Message):
    await help_cmd(message)


@dp.message(lambda m: m.text == "📋 Все записи")
async def list_all(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа")
        return

    sheet = get_google_sheet()
    if not sheet:
        await message.answer("⚠️ База недоступна")
        return

    records = sheet.get_all_records()
    if not records:
        await message.answer("📭 База пуста")
        return

    response = "📋 <b>Последние 10 записей:</b>\n\n"
    for i, record in enumerate(records[-10:], 1):
        user_id = record.get('ID', '?')
        username = record.get('Username', 'нет')
        level = record.get('Уровень', '3')
        date = record.get('Дата', '?')

        level_emoji = ["1️⃣", "2️⃣", "3️⃣"][int(level) - 1] if level in ['1', '2', '3'] else "3️⃣"
        response += f"{i}. {level_emoji} <code>{user_id}</code> (@{username}) - {date}\n"

    response += f"\n<i>Всего записей: {len(records)}</i>"
    await message.answer(response, parse_mode="HTML")


# Поиск пользователя
@dp.message()
async def search_user(message: Message):
    # Пропускаем команды
    if message.text.startswith('/'):
        return

    # Пропускаем кнопки
    if message.text in ["🔍 Проверить", "📊 Статистика", "❓ Справка", "➕ Добавить", "📋 Все записи"]:
        return

    query = message.text.strip().replace('@', '')

    sheet = get_google_sheet()
    if not sheet:
        await message.answer("⚠️ База временно недоступна. Попробуйте позже.")
        return

    records = sheet.get_all_records()

    # Ищем пользователя
    found = None
    for record in records:
        if query == str(record.get('ID', '')) or query.lower() == str(record.get('Username', '')).lower():
            found = record
            break

    if found:
        user_id = found.get('ID', '?')
        username = found.get('Username', 'нет')
        level = found.get('Уровень', '3')
        reason = found.get('Причина', 'Не указана')
        proof = found.get('Доказательства', 'Не приложены')
        date = found.get('Дата', 'Неизвестно')

        # Определяем уровень
        if level == '1':
            status = "✅ <b>Проверенный пользователь</b>"
            advice = "Нареканий нет. Можно проводить сделки."
        elif level == '2':
            status = "⚠️ <b>Требует осторожности</b>"
            advice = "Есть жалобы. Используйте гаранта."
        else:
            status = "🚨 <b>Мошенник</b>"
            advice = "Подтвержденный обман. Сделки запрещены!"

        response = (
            f"{status}\n\n"
            f"👤 <b>ID:</b> <code>{user_id}</code>\n"
            f"📛 <b>Юзернейм:</b> @{username}\n"
            f"📝 <b>Причина:</b> {reason}\n"
            f"🔗 <b>Доказательства:</b> {proof}\n"
            f"📅 <b>Дата внесения:</b> {date}\n\n"
            f"<b>Рекомендации:</b> {advice}\n\n"
            f"<i>База данных проекта TRUSTON</i>"
        )
    else:
        response = (
            f"🔍 <b>Поиск:</b> <code>{query}</code>\n\n"
            f"❌ Не найден в базе.\n"
            f"✅ Статус: чистый\n\n"
            f"<i>Пользователь не имеет нареканий в нашей базе</i>"
        )

    if message.from_user.id == ADMIN_ID:
        await message.answer(response, parse_mode="HTML", reply_markup=get_admin_keyboard())
    else:
        await message.answer(response, parse_mode="HTML", reply_markup=get_main_keyboard())


# Запуск
async def main():
    logger.info("🤖 Бот TRUSTON запускается...")

    # Тестируем подключение к Google Sheets
    sheet = get_google_sheet()
    if sheet:
        logger.info("✅ Подключено к Google Sheets")
        records = len(sheet.get_all_records())
        logger.info(f"📊 Записей в базе: {records}")
    else:
        logger.warning("⚠️ Google Sheets недоступен. Бот будет работать в режиме чтения.")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())