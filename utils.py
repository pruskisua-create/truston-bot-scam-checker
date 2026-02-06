from config import THREAT_LEVELS, PROJECT_NAME
import json


def format_user_info(user_data):
    """Форматирует информацию о пользователе для вывода"""
    if not user_data:
        return "Пользователь не найден в базе. ✅ Статус: чистый.", None

    user_id, username, threat_level, reason, proof, files_json, added_date = user_data
    level_info = THREAT_LEVELS.get(threat_level, THREAT_LEVELS[3])

    formatted_date = added_date.split('.')[0] if added_date else "Неизвестно"

    # Обрабатываем файлы
    files = []
    if files_json and files_json != '[]':
        try:
            files = json.loads(files_json)
        except:
            files = []

    message = (
        f"{level_info['emoji']} <b>Статус:</b> {level_info['name']}\n\n"
        f"👤 <b>ID:</b> <code>{user_id}</code>\n"
        f"📛 <b>Юзернейм:</b> @{username if username else 'не указан'}\n"
        f"📝 <b>Причина внесения:</b> {reason or 'Не указана'}\n"
        f"🔗 <b>Доказательства:</b> {proof or 'Не приложены'}\n"
        f"📎 <b>Файлов прикреплено:</b> {len(files)}\n"
        f"📅 <b>Дата внесения:</b> {formatted_date}\n\n"
        f"<b>Рекомендации:</b> {level_info['description']}\n\n"
        f"<i>База данных проекта {PROJECT_NAME}</i>"
    )

    return message, files


def is_admin(user_id):
    """Проверяет, является ли пользователь администратором"""
    from config import ADMIN_IDS
    return user_id in ADMIN_IDS