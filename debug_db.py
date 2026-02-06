#!/usr/bin/env python3
import sqlite3
import os

# Определяем путь к базе данных
if "RAILWAY" in os.environ:
    db_path = "/tmp/scam_database.db"
else:
    db_path = "scam_database.db"

print(f"🔍 Проверяем базу данных: {db_path}")
print(f"📁 Файл существует: {os.path.exists(db_path)}")

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Проверяем таблицу scammers
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scammers'")
    if cursor.fetchone():
        print("✅ Таблица scammers существует")

        # Получаем все записи
        cursor.execute("SELECT user_id, username, threat_level, added_date FROM scammers")
        records = cursor.fetchall()

        print(f"📊 Всего записей: {len(records)}")
        print("\n📋 Содержимое базы:")
        print("-" * 80)
        for i, (user_id, username, level, date) in enumerate(records, 1):
            print(f"{i:3}. ID: {user_id:15} | Username: {username or 'нет':20} | Level: {level} | Date: {date}")
        print("-" * 80)

        # Проверяем структуру таблицы
        cursor.execute("PRAGMA table_info(scammers)")
        columns = cursor.fetchall()
        print("\n📐 Структура таблицы scammers:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
    else:
        print("❌ Таблица scammers не найдена!")

    conn.close()
else:
    print("❌ Файл базы данных не найден!")