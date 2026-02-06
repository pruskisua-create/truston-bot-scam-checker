import json
from datetime import datetime
from aiogram import Router, types
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import BOT_TOKEN, ADMIN_IDS, THREAT_LEVELS, PROJECT_NAME
from database import db
from keyboards import get_main_keyboard, get_admin_keyboard, get_cancel_keyboard

router = Router()


# Проверка админа
def is_admin(user_id):
    return user_id in ADMIN_IDS


# ============ СОСТОЯНИЯ ============
class AddScammer(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_username = State()
    waiting_for_reason = State()
    waiting_for_proof = State()
    waiting_for_threat_level = State()


# ============ КОМАНДЫ ============
@router.message(Command("start"))
async def cmd_start(message: Message):
    welcome_text = (
        f"🛡️ <b>Добро пожаловать в бота с нашей антискам базой проекта TRUSTON!</b>\n\n"
        f"Я помогаю проверять пользователей на наличие жалоб и предупреждений о мошенничестве.\n\n"
        f"<b>Как использовать:</b>\n"
        f"• Отправьте <b>ID</b> пользователя (только цифры)\n"
        f"• Или отправьте <b>@username</b> (без @ или с ним)\n\n"
        f"<i>База обновляется командой TRUSTON для безопасности сообщества</i>"
    )

    if is_admin(message.from_user.id):
        await message.answer(welcome_text, reply_markup=get_admin_keyboard(), parse_mode="HTML")
    else:
        await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        f"🛡️ <b>Справка по боту TRUSTON</b>\n\n"
        f"<b>Основные команды:</b>\n"
        f"• /start - Запустить бота\n"
        f"• /check - Проверить пользователя\n"
        f"• /add - Добавить запись (админы)\n"
        f"• /stats - Статистика базы\n"
        f"• /help - Эта справка\n\n"
        f"<b>Уровни угрозы:</b>\n"
        f"• 1️⃣ - Проверенный\n"
        f"• 2️⃣ - Подозрительный\n"
        f"• 3️⃣ - Мошенник\n\n"
        f"<b>Просто отправьте ID или @username для проверки!</b>"
    )
    await message.answer(help_text, parse_mode="HTML")


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    all_records = db.get_all_scammers()
    total = len(all_records)

    stats_text = (
        f"📊 <b>Статистика базы TRUSTON</b>\n\n"
        f"• 📁 Всего записей: <b>{total}</b>\n"
        f"• 📅 Последнее обновление: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        f"<i>База работает и обновляется</i>"
    )

    await message.answer(stats_text, parse_mode="HTML")


@router.message(Command("check"))
async def cmd_check(message: Message):
    await message.answer("🔍 Отправьте ID или @username для проверки:", reply_markup=ReplyKeyboardRemove())


# ============ ПОИСК ПОЛЬЗОВАТЕЛЯ ============
@router.message()
async def process_message(message: Message, state: FSMContext):
    # Если пользователь в процессе добавления - пропускаем
    current_state = await state.get_state()
    if current_state:
        return

    # Пропускаем команды
    if message.text and message.text.startswith('/'):
        return

    # Пропускаем кнопки меню
    if message.text in ["🔍 Проверить", "📊 Статистика", "❓ Справка", "➕ Добавить", "🗑️ Удалить", "📋 Все записи",
                        "❌ Отмена"]:
        return

    user_input = message.text.strip()
    if not user_input:
        return

    # Ищем пользователя
    user_data, found_by = db.find_user(user_input)

    if not user_data:
        response = f"🔍 <b>Поиск:</b> <code>{user_input}</code>\n\n❌ Не найден в базе.\n✅ Статус: чистый"
        keyboard = get_admin_keyboard() if is_admin(message.from_user.id) else get_main_keyboard()
        await message.answer(response, parse_mode="HTML", reply_markup=keyboard)
        return

    # Форматируем результат
    user_id, username, level, reason, proof, date = user_data
    level_info = THREAT_LEVELS.get(level, THREAT_LEVELS[3])

    response = (
        f"{level_info['emoji']} <b>{level_info['name']}</b>\n\n"
        f"👤 <b>ID:</b> <code>{user_id}</code>\n"
        f"📛 <b>Юзернейм:</b> @{username or 'не указан'}\n"
        f"📝 <b>Причина:</b> {reason or 'Не указана'}\n"
        f"🔗 <b>Доказательства:</b> {proof or 'Не приложены'}\n"
        f"📅 <b>Дата внесения:</b> {date or 'Неизвестно'}\n\n"
        f"<i>База данных проекта TRUSTON</i>"
    )

    keyboard = get_admin_keyboard() if is_admin(message.from_user.id) else get_main_keyboard()
    await message.answer(response, parse_mode="HTML", reply_markup=keyboard)


# ============ АДМИН КОМАНДЫ ============
@router.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа", reply_markup=get_main_keyboard())
        return

    await state.set_state(AddScammer.waiting_for_user_id)
    await message.answer(
        "➕ <b>Добавление новой записи</b>\n\n"
        "Введите ID пользователя (только цифры):\n\n"
        "Для отмены: ❌ Отмена",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )


@router.message(AddScammer.waiting_for_user_id)
async def process_user_id(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление отменено", reply_markup=get_admin_keyboard())
        return

    user_id = message.text.strip()
    if not user_id.isdigit():
        await message.answer("❌ ID должен содержать только цифры. Попробуйте еще раз:")
        return

    await state.update_data(user_id=user_id)
    await state.set_state(AddScammer.waiting_for_username)
    await message.answer("Введите юзернейм (без @) или 'пропустить':")


@router.message(AddScammer.waiting_for_username)
async def process_username(message: Message, state: FSMContext):
    username = message.text.strip().replace('@', '')
    if username.lower() in ['пропустить', 'нет', 'no', '-']:
        username = ""

    await state.update_data(username=username)
    await state.set_state(AddScammer.waiting_for_reason)
    await message.answer("Введите причину внесения:")


@router.message(AddScammer.waiting_for_reason)
async def process_reason(message: Message, state: FSMContext):
    reason = message.text.strip()
    await state.update_data(reason=reason)
    await state.set_state(AddScammer.waiting_for_proof)
    await message.answer("Введите доказательства или 'нет':")


@router.message(AddScammer.waiting_for_proof)
async def process_proof(message: Message, state: FSMContext):
    proof = message.text.strip()
    if proof.lower() in ['нет', 'no', 'н']:
        proof = "Не предоставлены"

    await state.update_data(proof=proof)
    await state.set_state(AddScammer.waiting_for_threat_level)

    await message.answer(
        "Выберите уровень угрозы:\n\n"
        "1️⃣ - Проверенный (зелёный)\n"
        "2️⃣ - Подозрительный (жёлтый)\n"
        "3️⃣ - Мошенник (красный)\n\n"
        "Введите цифру (1, 2 или 3):"
    )


@router.message(AddScammer.waiting_for_threat_level)
async def process_threat_level(message: Message, state: FSMContext):
    try:
        threat_level = int(message.text.strip())
        if threat_level not in [1, 2, 3]:
            await message.answer("❌ Введите 1, 2 или 3:")
            return
    except:
        await message.answer("❌ Введите цифру (1, 2 или 3):")
        return

    # Получаем все данные
    user_data = await state.get_data()

    # Добавляем в базу
    success = db.add_scammer(
        user_id=user_data['user_id'],
        username=user_data.get('username', ''),
        threat_level=threat_level,
        reason=user_data['reason'],
        proof=user_data['proof'],
        added_by=message.from_user.id
    )

    if success:
        level_info = THREAT_LEVELS[threat_level]
        await message.answer(
            f"✅ <b>Запись добавлена!</b>\n\n"
            f"👤 ID: <code>{user_data['user_id']}</code>\n"
            f"📛 Юзернейм: @{user_data.get('username', 'не указан')}\n"
            f"🚨 Уровень: {level_info['name']}\n"
            f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            parse_mode="HTML",
            reply_markup=get_admin_keyboard()
        )
    else:
        await message.answer("❌ Ошибка при добавлении", reply_markup=get_admin_keyboard())

    await state.clear()


# ============ КНОПКИ МЕНЮ ============
@router.message(lambda m: m.text == "🔍 Проверить")
async def button_check(message: Message):
    await cmd_check(message)


@router.message(lambda m: m.text == "📊 Статистика")
async def button_stats(message: Message):
    await cmd_stats(message)


@router.message(lambda m: m.text == "❓ Справка")
async def button_help(message: Message):
    await cmd_help(message)


@router.message(lambda m: m.text == "➕ Добавить")
async def button_add(message: Message, state: FSMContext):
    await cmd_add(message, state)


@router.message(lambda m: m.text == "📋 Все записи")
async def button_list(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа", reply_markup=get_main_keyboard())
        return

    all_records = db.get_all_scammers()

    if not all_records:
        await message.answer("📭 База пуста")
        return

    text = "📋 <b>Все записи в базе:</b>\n\n"
    for i, (user_id, username, level, reason, date) in enumerate(all_records[:15], 1):
        level_emoji = ["1️⃣", "2️⃣", "3️⃣"][level - 1] if level in [1, 2, 3] else "3️⃣"
        username_display = f"@{username}" if username else "нет"
        date_short = date.split()[0] if date else "???"
        text += f"{i}. {level_emoji} <code>{user_id}</code> ({username_display}) - {date_short}\n"

    text += f"\n<i>Всего: {len(all_records)} записей</i>"
    await message.answer(text, parse_mode="HTML")


@router.message(lambda m: m.text == "❌ Отмена")
async def button_cancel(message: Message, state: FSMContext):
    await state.clear()
    keyboard = get_admin_keyboard() if is_admin(message.from_user.id) else get_main_keyboard()
    await message.answer("❌ Действие отменено", reply_markup=keyboard)