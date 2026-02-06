import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import BOT_TOKEN, ADMIN_IDS, THREAT_LEVELS, PROJECT_NAME
from database import db
from keyboards import get_main_keyboard, get_admin_keyboard, get_cancel_keyboard

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# Проверка админа
def is_admin(user_id):
    return user_id in ADMIN_IDS


# ============ КОМАНДЫ ============
@dp.message(Command("start"))
async def start(message: types.Message):
    text = f"🛡️ Добро пожаловать в {PROJECT_NAME}!\nОтправьте ID или @username для проверки."

    if is_admin(message.from_user.id):
        await message.answer(text, reply_markup=get_admin_keyboard())
    else:
        await message.answer(text, reply_markup=get_main_keyboard())


@dp.message(Command("batch_add"))
async def batch_add(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа")
        return

    await message.answer(
        "📁 Отправьте файл TXT или CSV\n\n"
        "Формат TXT:\n"
        "123456789 username 3 \"Причина\" \"Доказательства\"\n\n"
        "Для отмены: ❌ Отмена",
        reply_markup=get_cancel_keyboard()
    )


@dp.message(Command("debug"))
async def debug(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    all_records = db.get_all_scammers()
    text = f"📊 Записей: {len(all_records)}\n\n"

    for i, (user_id, username, level, reason, date) in enumerate(all_records[:5], 1):
        text += f"{i}. ID: {user_id} | @{username or 'нет'}\n"

    await message.answer(text)


# ============ ПОИСК ============
@dp.message(
    lambda m: m.text and not m.text.startswith('/') and m.text not in ["🔍 Проверить", "📊 Статистика", "❓ Справка",
                                                                       "➕ Добавить", "🗑️ Удалить", "📁 Импорт",
                                                                       "📋 Все записи", "❌ Отмена"])
async def search_user(message: types.Message):
    query = message.text.strip()
    logger.info(f"🔍 Поиск: {query}")

    user_data, found_by = db.find_user(query)

    if not user_data:
        await message.answer(f"🔍 {query}\n❌ Не найден\n✅ Чистый")
        return

    user_id, username, level, reason, proof, files, date = user_data
    level_info = THREAT_LEVELS.get(level, THREAT_LEVELS[3])

    text = (
        f"{level_info['emoji']} <b>{level_info['name']}</b>\n\n"
        f"👤 ID: <code>{user_id}</code>\n"
        f"📛 @{username or 'не указан'}\n"
        f"📝 {reason or 'Без причины'}\n"
        f"📅 {date or 'Неизвестно'}\n\n"
        f"{level_info['description']}"
    )

    await message.answer(text, parse_mode="HTML")


# ============ КНОПКИ ============
@dp.message(lambda m: m.text == "🔍 Проверить" or m.text == "🔍 Проверить пользователя")
async def check_button(message: types.Message):
    await message.answer("Отправьте ID или @username:", reply_markup=types.ReplyKeyboardRemove())


@dp.message(lambda m: m.text == "📊 Статистика" or m.text == "📊 Статистика базы")
async def stats_button(message: types.Message):
    all_records = db.get_all_scammers()
    total = len(all_records)

    text = f"📊 <b>{PROJECT_NAME}</b>\nВсего записей: <b>{total}</b>"
    await message.answer(text, parse_mode="HTML")


@dp.message(lambda m: m.text == "📋 Все записи")
async def list_button(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа")
        return

    all_records = db.get_all_scammers()

    if not all_records:
        await message.answer("📭 База пуста")
        return

    text = "📋 <b>Все записи:</b>\n\n"
    for i, (user_id, username, level, reason, date) in enumerate(all_records[:10], 1):
        text += f"{i}. <code>{user_id}</code> | @{username or 'нет'}\n"

    await message.answer(text, parse_mode="HTML")


@dp.message(lambda m: m.text == "❌ Отмена")
async def cancel_button(message: types.Message):
    await message.answer("❌ Отменено",
                         reply_markup=get_admin_keyboard() if is_admin(message.from_user.id) else get_main_keyboard())


# ============ ЗАПУСК ============
async def main():
    logger.info("🚀 Запуск бота...")

    try:
        me = await bot.get_me()
        logger.info(f"✅ Бот: @{me.username}")

        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"💥 Ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(main())