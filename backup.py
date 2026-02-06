#!/usr/bin/env python3
"""
Скрипт для резервного копирования базы данных
"""

import os
import shutil
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def backup_database():
    """Создает резервную копию базы данных"""
    db_file = "scam_database.db"
    backup_dir = "backups"

    if not os.path.exists(db_file):
        logger.error(f"❌ Файл базы данных не найден: {db_file}")
        return False

    # Создаем папку для бэкапов если её нет
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        logger.info(f"✅ Создана папка для бэкапов: {backup_dir}")

    # Генерируем имя файла с датой
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"scam_db_backup_{timestamp}.db")

    try:
        # Копируем файл
        shutil.copy2(db_file, backup_file)
        logger.info(f"✅ Резервная копия создана: {backup_file}")

        # Удаляем старые бэкапы (оставляем последние 10)
        backup_files = sorted([
            os.path.join(backup_dir, f)
            for f in os.listdir(backup_dir)
            if f.startswith("scam_db_backup_") and f.endswith(".db")
        ])

        if len(backup_files) > 10:
            for old_backup in backup_files[:-10]:
                os.remove(old_backup)
                logger.info(f"🗑️ Удален старый бэкап: {old_backup}")

        return True

    except Exception as e:
        logger.error(f"❌ Ошибка при создании бэкапа: {e}")
        return False


def list_backups():
    """Показывает список доступных бэкапов"""
    backup_dir = "backups"

    if not os.path.exists(backup_dir):
        print("📭 Папка с бэкапами не найдена")
        return

    backup_files = sorted([
        os.path.join(backup_dir, f)
        for f in os.listdir(backup_dir)
        if f.startswith("scam_db_backup_") and f.endswith(".db")
    ])

    print(f"📋 Доступно бэкапов: {len(backup_files)}")
    for i, backup in enumerate(backup_files, 1):
        size = os.path.getsize(backup)
        date_str = backup.split('_')[-1].replace('.db', '')
        date_obj = datetime.strptime(date_str[:8], "%Y%m%d")
        print(f"{i}. {backup} ({size:,} байт) - {date_obj.strftime('%d.%m.%Y')}")


def restore_backup(backup_number=None):
    """Восстанавливает базу из бэкапа"""
    backup_dir = "backups"

    if not os.path.exists(backup_dir):
        print("❌ Папка с бэкапами не найдена")
        return False

    backup_files = sorted([
        os.path.join(backup_dir, f)
        for f in os.listdir(backup_dir)
        if f.startswith("scam_db_backup_") and f.endswith(".db")
    ])

    if not backup_files:
        print("❌ Нет доступных бэкапов")
        return False

    if backup_number is None:
        print("📋 Выберите бэкап для восстановления:")
        list_backups()
        try:
            backup_number = int(input("\nВведите номер бэкапа: "))
        except:
            print("❌ Неверный номер")
            return False

    if backup_number < 1 or backup_number > len(backup_files):
        print("❌ Неверный номер бэкапа")
        return False

    backup_file = backup_files[backup_number - 1]

    try:
        # Создаем бэкап текущей базы
        if os.path.exists("scam_database.db"):
            temp_backup = f"scam_database_pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2("scam_database.db", temp_backup)
            print(f"✅ Создан бэкап текущей базы: {temp_backup}")

        # Восстанавливаем из бэкапа
        shutil.copy2(backup_file, "scam_database.db")
        print(f"✅ База восстановлена из: {backup_file}")
        print(f"📊 Размер: {os.path.getsize('scam_database.db'):,} байт")

        return True

    except Exception as e:
        print(f"❌ Ошибка при восстановлении: {e}")
        return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "backup":
            backup_database()
        elif command == "list":
            list_backups()
        elif command == "restore":
            if len(sys.argv) > 2:
                restore_backup(int(sys.argv[2]))
            else:
                restore_backup()
        else:
            print("Использование:")
            print("  python backup.py backup   - создать бэкап")
            print("  python backup.py list     - показать бэкапы")
            print("  python backup.py restore  - восстановить бэкап")
            print("  python backup.py restore N - восстановить бэкап номер N")
    else:
        # По умолчанию создаем бэкап
        backup_database()