import json
import csv
import io
import re
import tempfile
import os
from datetime import datetime
from aiogram import Router, types
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, ContentType
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state

from config import THREAT_LEVELS, ADMIN_CONTACTS, PROJECT_NAME
from database import db
from keyboards import get_admin_keyboard, get_main_keyboard, get_threat_level_keyboard, get_delete_keyboard, \
    get_cancel_keyboard, get_confirm_keyboard
from utils import format_user_info, is_admin

router = Router()


# ============ СОСТОЯНИЯ ============
class AddScammer(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_username = State()
    waiting_for_reason = State()
    waiting_for_proof = State()
    waiting_for_files = State()
    waiting_for_threat_level = State()


class DeleteScammer(StatesGroup):
    waiting_for_user_id = State()


class BatchAddScammers(StatesGroup):
    waiting_for_file = State()
    waiting_for_confirmation = State()


# ============ СТАРТ И КОМАНДЫ ============
@router.message(Command("start"))
async def cmd_start(message: Message):
    welcome_text = (
        f"🛡️ <b>Добро пожаловать в антискам базу проекта {PROJECT_NAME}</b>\n\n"
        f"Я помогаю проверять пользователей на наличие жалоб.\n"
        f"Отправьте мне <b>ID</b> или <b>@username</b> пользователя для проверки.\n\n"
        f"Вы также можете использовать кнопки ниже:"
    )

    if is_admin(message.from_user.id):
        await message.answer(welcome_text, reply_markup=get_admin_keyboard(), parse_mode="HTML")
    else:
        await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        f"🛡️ <b>Справка по базе {PROJECT_NAME}</b>\n\n"
        f"<b>Основные команды:</b>\n"
        f"• /start - Запустить бота\n"
        f"• /check - Проверить пользователя\n"
        f"• /add - Добавить запись (админы)\n"
        f"• /batch_add - Массовая загрузка из файла (админы)\n"
        f"• /delete - Удалить запись (админы)\n"
        f"• /stats - Статистика\n"
        f"• /backup - Создать резервную копию (админы)\n"
        f"• /help - Справка\n\n"
        f"<b>Форматы файлов для массовой загрузки:</b>\n"
        f"• CSV: user_id,username,threat_level,reason,proof\n"
        f"• TXT: ID ЮЗЕРНЕЙМ УРОВЕНЬ \"ПРИЧИНА\" \"ДОКАЗАТЕЛЬСТВА\"\n"
        f"• Уровни: 1✅, 2⚠️, 3🚨\n"
        f"• Пример TXT: 123456789 scammer1 3 \"Обманул\" \"скрины\"\n\n"
        f"<b>По вопросам:</b>\n{ADMIN_CONTACTS}"
    )
    await message.answer(help_text, parse_mode="HTML")


@router.message(Command("backup"))
async def cmd_backup(message: Message):
    """Создание резервной копии базы данных"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа.", reply_markup=get_main_keyboard())
        return

    # Получаем все записи из базы
    all_scammers = db.get_all_scammers()

    if not all_scammers:
        await message.answer("📭 База данных пуста. Нечего сохранять.")
        return

    await message.answer("🔄 Создаю резервную копию...")

    try:
        # Создаем структуру для бэкапа
        backup_data = []
        total_records = len(all_scammers)
        processed = 0

        for user_id, username, threat_level, reason, added_date in all_scammers:
            # Получаем полные данные пользователя
            user_data, _ = db.find_user(user_id)
            if user_data:
                backup_data.append({
                    'user_id': user_data[0],
                    'username': user_data[1] or '',
                    'threat_level': user_data[2],
                    'reason': user_data[3] or 'Не указана',
                    'proof': user_data[4] or 'Не предоставлены',
                    'added_date': added_date or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })

            processed += 1
            if processed % 10 == 0:  # Обновляем прогресс каждые 10 записей
                await message.edit_text(f"🔄 Обработано {processed}/{total_records} записей...")

        # Создаем временный файл
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
            temp_file = f.name

        # Отправляем файл пользователю
        with open(temp_file, 'rb') as f:
            backup_bytes = f.read()

        # Создаем имя файла с датой
        backup_filename = f"truston_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        await message.answer_document(
            document=types.BufferedInputFile(backup_bytes, filename=backup_filename),
            caption=f"📦 <b>Резервная копия базы {PROJECT_NAME}</b>\n\n"
                    f"📊 Записей: {len(backup_data)}\n"
                    f"📅 Дата создания: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                    f"<i>Для восстановления используйте команду /batch_add и отправьте этот файл</i>",
            parse_mode="HTML"
        )

        # Удаляем временный файл
        os.unlink(temp_file)

        await message.answer(f"✅ Резервная копия создана успешно! Сохранено {len(backup_data)} записей.")

    except Exception as e:
        await message.answer(f"❌ Ошибка при создании резервной копии: {str(e)}")


@router.message(Command("batch_add"))
async def cmd_batch_add(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа.", reply_markup=get_main_keyboard())
        return

    await message.answer(
        "📁 <b>Массовая загрузка записей из файла</b>\n\n"
        "Отправьте мне файл в формате CSV, TXT или JSON (бэкап)\n\n"
        "<b>Формат CSV:</b>\n"
        "<code>user_id,username,threat_level,reason,proof</code>\n\n"
        "<b>Формат TXT:</b>\n"
        "<code>123456789 scammer1 3 \"Обманул на 1000$\" \"скрины\"</code>\n\n"
        "<b>Формат JSON:</b> файл созданный командой /backup\n\n"
        "<b>Примечания:</b>\n"
        "• threat_level: 1✅, 2⚠️, 3🚨\n"
        "• username можно оставить пустым (используйте -)\n"
        "• Для отмены напишите 'отмена'",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(BatchAddScammers.waiting_for_file)


def parse_txt_content(content):
    """Парсит TXT файл с данными"""
    data = []
    errors = []

    lines = content.strip().split('\n')
    for i, line in enumerate(lines, start=1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        try:
            # Парсим строку вида: ID ЮЗЕРНЕЙМ УРОВЕНЬ "ПРИЧИНА" "ДОКАЗАТЕЛЬСТВА"
            # Находим части в кавычках
            parts = []
            current = ""
            in_quotes = False

            for char in line:
                if char == '"':
                    in_quotes = not in_quotes
                elif char == ' ' and not in_quotes:
                    if current:
                        parts.append(current)
                        current = ""
                else:
                    current += char

            if current:
                parts.append(current)

            # Должно быть минимум 3 части (ID, username, level)
            if len(parts) < 3:
                errors.append(f"Строка {i}: Недостаточно данных")
                continue

            user_id = parts[0].strip()
            username = parts[1].strip() if len(parts) > 1 else ""
            threat_level = parts[2].strip() if len(parts) > 2 else "3"
            reason = parts[3].strip() if len(parts) > 3 else "Не указана"
            proof = parts[4].strip() if len(parts) > 4 else "Не предоставлены"

            # Заменяем - на пустую строку для username
            if username == "-" or username.lower() == "нет":
                username = ""

            # Валидация
            if not user_id.isdigit():
                errors.append(f"Строка {i}: user_id должен содержать только цифры")
                continue

            try:
                threat_level_int = int(threat_level)
                if threat_level_int not in [1, 2, 3]:
                    errors.append(f"Строка {i}: threat_level должен быть 1, 2 или 3")
                    continue
            except ValueError:
                errors.append(f"Строка {i}: threat_level должен быть числом")
                continue

            # Очищаем username от @
            username = username.replace('@', '')

            data.append({
                'user_id': user_id,
                'username': username,
                'threat_level': threat_level_int,
                'reason': reason,
                'proof': proof
            })

        except Exception as e:
            errors.append(f"Строка {i}: Ошибка обработки - {str(e)}")
            continue

    return data, errors


def parse_csv_content(content):
    """Парсит CSV файл с данными"""
    data = []
    errors = []

    # Пробуем разные разделители
    for delimiter in (',', ';', '\t'):
        try:
            reader = csv.reader(io.StringIO(content), delimiter=delimiter)
            rows = list(reader)

            if rows and len(rows[0]) >= 3:  # Проверяем первую строку
                # Пропускаем заголовок если он есть
                start_index = 0
                first_row = rows[0]
                # Если первая строка содержит не цифры в первом столбце, это заголовок
                if not first_row[0].replace('-', '').isdigit():
                    start_index = 1

                for i, row in enumerate(rows[start_index:], start=start_index + 1):
                    try:
                        if len(row) < 3:
                            errors.append(f"Строка {i}: Мало данных")
                            continue

                        user_id = str(row[0]).strip()
                        username = str(row[1]).strip() if len(row) > 1 else ""
                        threat_level = str(row[2]).strip() if len(row) > 2 else "3"
                        reason = str(row[3]).strip() if len(row) > 3 else "Не указана"
                        proof = str(row[4]).strip() if len(row) > 4 else "Не предоставлены"

                        # Заменяем - на пустую строку
                        if username == "-" or username.lower() in ["нет", "no", "skip"]:
                            username = ""

                        # Валидация
                        if not user_id.isdigit():
                            errors.append(f"Строка {i}: user_id должен содержать только цифры")
                            continue

                        try:
                            threat_level_int = int(threat_level)
                            if threat_level_int not in [1, 2, 3]:
                                errors.append(f"Строка {i}: threat_level должен быть 1, 2 или 3")
                                continue
                        except ValueError:
                            errors.append(f"Строка {i}: threat_level должен быть числом")
                            continue

                        username = username.replace('@', '')

                        data.append({
                            'user_id': user_id,
                            'username': username,
                            'threat_level': threat_level_int,
                            'reason': reason,
                            'proof': proof
                        })

                    except Exception as e:
                        errors.append(f"Строка {i}: Ошибка обработки - {str(e)}")
                        continue

                break  # Если удалось распарсить, выходим

        except:
            continue

    return data, errors


def parse_json_content(content):
    """Парсит JSON файл (бэкап)"""
    data = []
    errors = []

    try:
        backup_data = json.loads(content)

        if not isinstance(backup_data, list):
            errors.append("JSON должен содержать массив записей")
            return data, errors

        for i, item in enumerate(backup_data, 1):
            try:
                if not isinstance(item, dict):
                    errors.append(f"Запись {i}: должна быть объектом")
                    continue

                # Получаем поля
                user_id = str(item.get('user_id', '')).strip()
                username = str(item.get('username', '')).strip()
                threat_level = str(item.get('threat_level', '3')).strip()
                reason = str(item.get('reason', 'Не указана')).strip()
                proof = str(item.get('proof', 'Не предоставлены')).strip()

                # Валидация
                if not user_id or not user_id.isdigit():
                    errors.append(f"Запись {i}: неверный user_id")
                    continue

                try:
                    threat_level_int = int(threat_level)
                    if threat_level_int not in [1, 2, 3]:
                        errors.append(f"Запись {i}: threat_level должен быть 1, 2 или 3")
                        continue
                except ValueError:
                    errors.append(f"Запись {i}: threat_level должен быть числом")
                    continue

                # Очищаем username от @
                username = username.replace('@', '')

                data.append({
                    'user_id': user_id,
                    'username': username,
                    'threat_level': threat_level_int,
                    'reason': reason,
                    'proof': proof
                })

            except Exception as e:
                errors.append(f"Запись {i}: ошибка обработки - {str(e)}")
                continue

    except json.JSONDecodeError as e:
        errors.append(f"Ошибка разбора JSON: {str(e)}")
    except Exception as e:
        errors.append(f"Ошибка обработки файла: {str(e)}")

    return data, errors


@router.message(BatchAddScammers.waiting_for_file)
async def process_batch_file(message: Message, state: FSMContext):
    if message.text and message.text.lower() == 'отмена':
        await state.clear()
        await message.answer("❌ Массовая загрузка отменена.", reply_markup=get_admin_keyboard())
        return

    if not message.document:
        await message.answer("❌ Пожалуйста, отправьте файл (CSV, TXT или JSON) или напишите 'отмена'.")
        return

    # Проверяем формат файла
    file_name = message.document.file_name.lower()
    if not (file_name.endswith('.csv') or file_name.endswith('.txt') or file_name.endswith('.json')):
        await message.answer("❌ Файл должен быть в формате CSV (.csv), TXT (.txt) или JSON (.json)")
        return

    try:
        # Скачиваем файл
        file = await message.bot.download(message.document.file_id)
        content = file.read().decode('utf-8-sig').strip()

        if not content:
            await message.answer("❌ Файл пустой.")
            return

        # Определяем формат и парсим
        valid_data = []
        errors = []

        if file_name.endswith('.txt'):
            valid_data, errors = parse_txt_content(content)
        elif file_name.endswith('.csv'):
            valid_data, errors = parse_csv_content(content)
        else:  # JSON
            valid_data, errors = parse_json_content(content)

        if not valid_data:
            await message.answer(
                "❌ Не найдено валидных данных для импорта.\n"
                f"Ошибки:\n" + "\n".join(errors[:10]),
                parse_mode="HTML"
            )
            return

        # Сохраняем данные в состоянии
        await state.update_data(
            batch_data=valid_data,
            batch_errors=errors,
            batch_file_name=message.document.file_name
        )

        # Показываем предпросмотр
        preview_text = (
            f"📊 <b>Предпросмотр импорта</b>\n\n"
            f"📁 Файл: <code>{message.document.file_name}</code>\n"
            f"📈 Найдено записей: {len(valid_data)}\n"
            f"❌ Ошибок: {len(errors)}\n\n"
            f"<b>Первые 5 записей:</b>\n"
        )

        for i, data in enumerate(valid_data[:5], 1):
            level_info = THREAT_LEVELS.get(data['threat_level'], THREAT_LEVELS[3])
            username_display = f"@{data['username']}" if data['username'] else "не указан"
            preview_text += (
                f"{i}. {level_info['emoji']} <code>{data['user_id']}</code> "
                f"({username_display})\n"
            )

        if len(valid_data) > 5:
            preview_text += f"\n<i>... и еще {len(valid_data) - 5} записей</i>"

        if errors:
            preview_text += f"\n\n<b>Ошибки ({min(len(errors), 3)} из {len(errors)}):</b>\n"
            for error in errors[:3]:
                preview_text += f"• {error}\n"
            if len(errors) > 3:
                preview_text += f"<i>... и еще {len(errors) - 3} ошибок</i>"

        preview_text += (
            f"\n\n<b>Продолжить импорт?</b>\n"
            f"Будут добавлены {len(valid_data)} записей."
        )

        await message.answer(preview_text, parse_mode="HTML", reply_markup=get_confirm_keyboard())
        await state.set_state(BatchAddScammers.waiting_for_confirmation)

    except Exception as e:
        await message.answer(f"❌ Ошибка при обработке файла: {str(e)}")
        await state.clear()


@router.callback_query(BatchAddScammers.waiting_for_confirmation, lambda c: c.data == "confirm_yes")
async def process_batch_confirm_yes(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    user_data = await state.get_data()
    batch_data = user_data.get('batch_data', [])
    errors = user_data.get('batch_errors', [])
    file_name = user_data.get('batch_file_name', 'файл.csv')

    if not batch_data:
        await callback.message.edit_text("❌ Нет данных для импорта.")
        await state.clear()
        return

    # Импортируем данные
    added_count = 0
    skipped_count = 0
    error_count = 0

    progress_msg = await callback.message.answer(
        f"🔄 <b>Начинаю импорт...</b>\n"
        f"⏳ Обработано: 0/{len(batch_data)}",
        parse_mode="HTML"
    )

    for i, data in enumerate(batch_data, 1):
        try:
            # Проверяем, существует ли уже пользователь
            existing_user, _ = db.find_user(data['user_id'])

            if existing_user:
                skipped_count += 1
            else:
                # Добавляем пользователя
                success = db.add_scammer(
                    user_id=data['user_id'],
                    username=data['username'],
                    threat_level=data['threat_level'],
                    reason=data['reason'],
                    proof=data['proof'],
                    files_json='[]',
                    added_by=callback.from_user.id
                )

                if success:
                    added_count += 1
                    db.log_admin_action(callback.from_user.id, "batch_add", data['user_id'])
                else:
                    error_count += 1

            # Обновляем прогресс каждые 10 записей
            if i % 10 == 0 or i == len(batch_data):
                await progress_msg.edit_text(
                    f"🔄 <b>Идет импорт...</b>\n"
                    f"⏳ Обработано: {i}/{len(batch_data)}\n"
                    f"✅ Добавлено: {added_count}\n"
                    f"⏭️ Пропущено: {skipped_count}\n"
                    f"❌ Ошибок: {error_count}",
                    parse_mode="HTML"
                )

        except Exception as e:
            error_count += 1
            errors.append(f"Ошибка при импорте {data['user_id']}: {str(e)}")
            continue

    # Итоговое сообщение
    result_text = (
        f"📊 <b>Результаты импорта из {file_name}</b>\n\n"
        f"📈 Всего записей в файле: {len(batch_data) + len(errors)}\n"
        f"✅ Успешно добавлено: <b>{added_count}</b>\n"
        f"⏭️ Пропущено (уже в базе): <b>{skipped_count}</b>\n"
        f"❌ Ошибок при импорте: <b>{error_count}</b>\n"
        f"⚠️ Ошибок валидации: <b>{len(errors)}</b>\n\n"
    )

    if errors:
        result_text += f"<b>Примеры ошибок:</b>\n"
        for error in errors[:5]:
            result_text += f"• {error}\n"
        if len(errors) > 5:
            result_text += f"<i>... и еще {len(errors) - 5} ошибок</i>\n"

    # Обновляем статистику в сообщении
    await progress_msg.edit_text(result_text, parse_mode="HTML")

    # Отправляем кнопки
    await callback.message.answer("Что дальше?", reply_markup=get_admin_keyboard())

    await state.clear()


@router.callback_query(BatchAddScammers.waiting_for_confirmation, lambda c: c.data == "confirm_no")
async def process_batch_confirm_no(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text("❌ Импорт отменен.")
    await state.clear()
    await callback.message.answer("Что дальше?", reply_markup=get_admin_keyboard())


@router.message(Command("delete"))
async def cmd_delete(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа.", reply_markup=get_main_keyboard())
        return

    await message.answer(
        "🗑️ <b>Удаление записи</b>\n\n"
        "Введите ID пользователя для удаления:",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(DeleteScammer.waiting_for_user_id)


# ============ ОБРАБОТКА УДАЛЕНИЯ ============
@router.message(DeleteScammer.waiting_for_user_id)
async def process_delete_id(message: Message, state: FSMContext):
    if message.text.lower() == 'отмена':
        await state.clear()
        await message.answer("❌ Удаление отменено.", reply_markup=get_admin_keyboard())
        return

    user_id = message.text.strip().replace('@', '')

    if not user_id.isdigit():
        await message.answer("❌ ID должен содержать только цифры. Попробуйте еще раз или напишите 'отмена':")
        return

    # Проверяем, существует ли запись
    user_data, _ = db.find_user(user_id)
    if not user_data:
        await message.answer(f"❌ Запись с ID <code>{user_id}</code> не найдена.", parse_mode="HTML")
        await state.clear()
        await message.answer("Что дальше?", reply_markup=get_admin_keyboard())
        return

    # Показываем информацию о пользователе и запрашиваем подтверждение
    response, _ = format_user_info(user_data)
    await message.answer(
        f"⚠️ <b>Вы действительно хотите удалить эту запись?</b>\n\n{response}",
        parse_mode="HTML",
        reply_markup=get_delete_keyboard(user_id)
    )
    await state.clear()


@router.callback_query(lambda c: c.data.startswith("delete_confirm_"))
async def process_delete_confirm(callback: CallbackQuery):
    user_id = callback.data.replace("delete_confirm_", "")

    # Удаляем запись
    success = db.delete_scammer(user_id)

    if success:
        await callback.message.edit_text(
            f"✅ Запись с ID <code>{user_id}</code> успешно удалена!",
            parse_mode="HTML"
        )
        db.log_admin_action(callback.from_user.id, "delete", user_id)
    else:
        await callback.message.edit_text(
            f"❌ Ошибка при удаления записи с ID <code>{user_id}</code>",
            parse_mode="HTML"
        )

    await callback.answer()
    await callback.message.answer("Что дальше?", reply_markup=get_admin_keyboard())


@router.callback_query(lambda c: c.data.startswith("delete_cancel_"))
async def process_delete_cancel(callback: CallbackQuery):
    user_id = callback.data.replace("delete_cancel_", "")
    await callback.message.edit_text(
        f"❌ Удаление записи с ID <code>{user_id}</code> отменено.",
        parse_mode="HTML"
    )
    await callback.answer()
    await callback.message.answer("Что дальше?", reply_markup=get_admin_keyboard())


# ============ КНОПКИ ============
@router.message(lambda m: m.text == "🔍 Проверить пользователя")
async def button_check(message: Message):
    await message.answer(
        "Отправьте <b>ID</b> или <b>@username</b> пользователя для проверки:",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(lambda m: m.text == "❓ Справка")
async def button_help(message: Message):
    await cmd_help(message)


@router.message(lambda m: m.text == "📊 Статистика базы")
async def button_stats(message: Message):
    all_scammers = db.get_all_scammers()
    total = len(all_scammers)

    verified = len([s for s in all_scammers if s[2] == 1])
    suspicious = len([s for s in all_scammers if s[2] == 2])
    scammers = len([s for s in all_scammers if s[2] == 3])

    stats_text = (
        f"📊 <b>Статистика базы {PROJECT_NAME}</b>\n\n"
        f"• 📁 Всего записей: <b>{total}</b>\n"
        f"• ✅ Проверенных: <b>{verified}</b>\n"
        f"• ⚠️ Под подозрением: <b>{suspicious}</b>\n"
        f"• 🚨 Мошенников: <b>{scammers}</b>\n\n"
        f"<i>Данные обновляются в реальном времени</i>"
    )

    await message.answer(stats_text, parse_mode="HTML")


@router.message(lambda m: m.text == "📋 Все записи")
async def button_list(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен.", reply_markup=get_main_keyboard())
        return

    all_scammers = db.get_all_scammers()

    if not all_scammers:
        await message.answer("📭 База данных пуста.")
        return

    response = f"📋 <b>Записи в базе {PROJECT_NAME}:</b>\n\n"
    for i, scammer in enumerate(all_scammers[:15], 1):
        user_id, username, threat_level, reason, added_date = scammer
        level_info = THREAT_LEVELS.get(threat_level, THREAT_LEVELS[3])
        date_short = added_date.split()[0] if added_date else "???"
        username_display = f"@{username}" if username else "нет"
        response += f"{i}. {level_info['emoji']} <code>{user_id}</code> ({username_display}) - {date_short}\n"

    response += f"\n<i>Всего записей: {len(all_scammers)}</i>"
    await message.answer(response, parse_mode="HTML")


@router.message(lambda m: m.text == "➕ Добавить запись")
async def button_add(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа.", reply_markup=get_main_keyboard())
        return

    await state.clear()
    await state.update_data(files=[])
    await message.answer(
        "📝 <b>Добавление новой записи</b>\n\n"
        "<b>ШАГ 1:</b> Введите <b>ID пользователя</b> (только цифры):\n"
        "<i>Пример: 123456789</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(AddScammer.waiting_for_user_id)


@router.message(lambda m: m.text == "🗑️ Удалить запись")
async def button_delete(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа.", reply_markup=get_main_keyboard())
        return

    await state.clear()
    await cmd_delete(message, state)


@router.message(lambda m: m.text == "📁 Массовая загрузка")
async def button_batch_add(message: Message, state: FSMContext):
    await cmd_batch_add(message, state)


# ============ ДОБАВЛЕНИЕ ЗАПИСИ ============
@router.message(AddScammer.waiting_for_user_id)
async def process_user_id(message: Message, state: FSMContext):
    user_input = message.text.strip().replace('@', '')

    if not user_input.isdigit():
        await message.answer("❌ ID должен содержать только цифры. Попробуйте еще раз:")
        return

    # Проверяем, есть ли уже такой пользователь в базе
    existing_user, _ = db.find_user(user_input)
    if existing_user:
        response, files = format_user_info(existing_user)
        await message.answer(
            f"⚠️ <b>Пользователь уже есть в базе!</b>\n\n{response}",
            parse_mode="HTML"
        )

        await message.answer(
            "Что вы хотите сделать?\n"
            "• Напишите 'отмена' чтобы выйти\n"
            "• Напишите 'новый' чтобы ввести другой ID",
            reply_markup=get_cancel_keyboard()
        )
        return

    await state.update_data(user_id=user_input)

    await message.answer(
        f"✅ ID <code>{user_input}</code> принят!\n\n"
        "<b>ШАГ 2:</b> Введите <b>юзернейм</b> (без @) или 'пропустить':",
        parse_mode="HTML"
    )
    await state.set_state(AddScammer.waiting_for_username)


@router.message(AddScammer.waiting_for_username)
async def process_username(message: Message, state: FSMContext):
    # Обработка отмены или выбора
    text_lower = message.text.lower()
    if text_lower == 'отмена':
        await state.clear()
        await message.answer("❌ Добавление отменено.", reply_markup=get_admin_keyboard())
        return
    elif text_lower == 'новый':
        await message.answer(
            "Введите <b>ID пользователя</b> (только цифры):",
            parse_mode="HTML"
        )
        await state.set_state(AddScammer.waiting_for_user_id)
        return

    username = message.text.strip().replace('@', '')

    if username.lower() in ['пропустить', 'skip', 'нет', 'no', '-']:
        username = ""

    await state.update_data(username=username)

    username_display = f"@{username}" if username else "не указан"
    await message.answer(
        f"✅ Юзернейм {username_display}!\n\n"
        "<b>ШАГ 3:</b> Введите <b>причину</b> внесения:",
        parse_mode="HTML"
    )
    await state.set_state(AddScammer.waiting_for_reason)


@router.message(AddScammer.waiting_for_reason)
async def process_reason(message: Message, state: FSMContext):
    reason = message.text.strip()

    if len(reason) < 5:
        await message.answer("❌ Слишком коротко. Напишите подробнее:")
        return

    await state.update_data(reason=reason)

    await message.answer(
        "✅ Причина сохранена!\n\n"
        "<b>ШАГ 4:</b> Введите <b>текстовые доказательства</b> или 'нет':",
        parse_mode="HTML"
    )
    await state.set_state(AddScammer.waiting_for_proof)


@router.message(AddScammer.waiting_for_proof)
async def process_proof(message: Message, state: FSMContext):
    proof = message.text.strip()

    if proof.lower() in ['нет', 'no', 'н', '-']:
        proof = "Текстовые доказательства не предоставлены"

    await state.update_data(proof=proof)

    await message.answer(
        "✅ Доказательства сохранены!\n\n"
        "<b>ШАГ 5:</b> Прикрепите файлы (фото/видео) или напишите 'готово':",
        parse_mode="HTML"
    )
    await state.set_state(AddScammer.waiting_for_files)


@router.message(AddScammer.waiting_for_files)
async def process_files(message: Message, state: FSMContext):
    # Проверяем, если это текст "готово" или "пропустить" (в любом регистре)
    if message.text:
        text_lower = message.text.lower()
        if text_lower in ['готово', 'пропустить', 'skip', 'done', 'готова', 'готов']:
            # Получаем текущие данные из состояния
            user_data = await state.get_data()
            files = user_data.get('files', [])

            # Сохраняем файлы в формате JSON
            files_json = json.dumps(files)
            await state.update_data(files_json=files_json)

            await message.answer(
                "🎯 <b>ШАГ 6:</b> Выберите <b>уровень угрозы</b>:",
                reply_markup=get_threat_level_keyboard(),
                parse_mode="HTML"
            )
            await state.set_state(AddScammer.waiting_for_threat_level)
            return

    # Проверяем, если это файл (фото, видео или документ)
    if message.photo or message.video or message.document:
        # Получаем текущие файлы из состояния
        user_data = await state.get_data()
        files = user_data.get('files', [])

        # Определяем тип файла и получаем file_id
        file_data = {}

        if message.photo:
            file_data = {
                'file_id': message.photo[-1].file_id,
                'file_type': 'photo',
                'caption': message.caption or ''
            }
        elif message.video:
            file_data = {
                'file_id': message.video.file_id,
                'file_type': 'video',
                'caption': message.caption or ''
            }
        elif message.document:
            file_data = {
                'file_id': message.document.file_id,
                'file_type': 'document',
                'caption': message.caption or ''
            }

        # Добавляем файл в список
        files.append(file_data)
        await state.update_data(files=files)

        await message.answer(
            f"✅ Файл добавлен! Всего файлов: {len(files)}\n"
            f"Отправьте еще файлы или напишите 'готово' чтобы продолжить."
        )
        return

    # Если это не файл и не "готово" - просим отправить файл или написать "готово"
    await message.answer(
        "Пожалуйста, отправьте файл (фото/видео/документ) или напишите 'готово' чтобы продолжить."
    )


@router.callback_query(lambda c: c.data.startswith("threat_"))
async def process_threat_level(callback: CallbackQuery, state: FSMContext):
    threat_level = int(callback.data.split("_")[1])
    user_data = await state.get_data()
    level_info = THREAT_LEVELS[threat_level]

    # Получаем файлы в формате JSON
    files_json = user_data.get('files_json', '[]')

    success = db.add_scammer(
        user_id=user_data['user_id'],
        username=user_data.get('username', ''),
        threat_level=threat_level,
        reason=user_data['reason'],
        proof=user_data['proof'],
        files_json=files_json,
        added_by=callback.from_user.id
    )

    if success:
        username_display = f"@{user_data.get('username')}" if user_data.get('username') else "не указан"
        files_list = json.loads(files_json)

        await callback.message.edit_text(
            f"✅ <b>ЗАПИСЬ ДОБАВЛЕНА!</b>\n\n"
            f"👤 <b>ID:</b> <code>{user_data['user_id']}</code>\n"
            f"📛 <b>Юзернейм:</b> {username_display}\n"
            f"🚨 <b>Уровень:</b> {level_info['name']}\n"
            f"📎 <b>Файлов прикреплено:</b> {len(files_list)}\n"
            f"📅 <b>Дата:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            parse_mode="HTML"
        )
        db.log_admin_action(callback.from_user.id, "add", user_data['user_id'])
        await callback.message.answer("Что дальше?", reply_markup=get_admin_keyboard())
    else:
        await callback.message.edit_text("❌ Ошибка при сохранении", parse_mode="HTML")

    await state.clear()
    await callback.answer()


# ============ ПОИСК ПОЛЬЗОВАТЕЛЯ ============
async def send_files(bot, chat_id, files):
    """Отправляет файлы пользователю"""
    try:
        for file_data in files:
            file_id = file_data.get('file_id')
            file_type = file_data.get('file_type')
            caption = file_data.get('caption', '')[:1024]

            if file_type == 'photo':
                await bot.send_photo(chat_id=chat_id, photo=file_id, caption=caption)
            elif file_type == 'video':
                await bot.send_video(chat_id=chat_id, video=file_id, caption=caption)
            elif file_type == 'document':
                await bot.send_document(chat_id=chat_id, document=file_id, caption=caption)
            else:
                await bot.send_document(chat_id=chat_id, document=file_id, caption=caption)
    except Exception as e:
        print(f"Ошибка при отправке файлов: {e}")
        await bot.send_message(chat_id, f"⚠️ Не удалось отправить некоторые файлы: {str(e)}")


# Обработчик для поиска (только когда не в состоянии)
@router.message(StateFilter(default_state))
async def process_search(message: Message):
    """Обрабатывает поиск только когда не в состоянии FSM"""

    # Пропускаем команды и кнопки (они уже обработаны другими хэндлерами)
    if message.text in ["🔍 Проверить пользователя", "❓ Справка", "📊 Статистика базы",
                        "📋 Все записи", "➕ Добавить запись", "🗑️ Удалить запись", "📁 Массовая загрузка"]:
        return

    user_input = message.text.strip()

    # Ищем пользователя
    user_data, found_by = db.find_user(user_input.replace('@', ''))

    if not user_data:
        response = f"🔍 <b>Поиск:</b> <code>{user_input}</code>\n\n❌ Не найден в базе.\n✅ Статус: чистый"
        keyboard = get_admin_keyboard() if is_admin(message.from_user.id) else get_main_keyboard()
        await message.answer(response, parse_mode="HTML", reply_markup=keyboard)
        return

    response, files = format_user_info(user_data)
    keyboard = get_admin_keyboard() if is_admin(message.from_user.id) else get_main_keyboard()

    found_text = "ID" if found_by == 'id' else "юзернейму"
    search_info = f"🔍 <b>Найдено по {found_text}:</b> <code>{user_input}</code>\n\n"
    response = search_info + response

    # Отправляем текстовую информацию
    await message.answer(response, parse_mode="HTML", reply_markup=keyboard)

    # Если есть файлы - отправляем их
    if files:
        await send_files(message.bot, message.chat.id, files)