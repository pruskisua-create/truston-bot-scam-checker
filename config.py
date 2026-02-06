import os

# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN", "8473743571:AAHU6sSYsiUx8rFTxpXeR6oVhAONnZ3HT60")

# ID администраторов
ADMIN_IDS = [int(os.getenv("ADMIN_ID", "599952947"))]

# Уровни угрозы
THREAT_LEVELS = {
    1: {"name": "✅ Проверенный", "description": "Нареканий нет", "emoji": "✅"},
    2: {"name": "⚠️ Подозрение", "description": "Есть жалобы", "emoji": "⚠️"},
    3: {"name": "🚨 Мошенник", "description": "Подтвержденный обман", "emoji": "🚨"}
}

PROJECT_NAME = "TRUSTON"
ADMIN_CONTACTS = "@nemurovv / @F4ll3NAngel"