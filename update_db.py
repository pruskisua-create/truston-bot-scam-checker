import sqlite3
import os


def update_database():
    db_path = 'scam_database.db'

    if not os.path.exists(db_path):
        print("❌ База данных не найдена!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("🔄 Обновляю структуру базы данных...")

    # Проверяем существующие колонки
    cursor.execute("PRAGMA table_info(scammers)")
    columns = [col[1] for col in cursor.fetchall()]

    print(f"Текущие колонки: {columns}")

    # Добавляем колонку files если её нет
    if 'files' not in columns:
        print("➕ Добавляю колонку 'files'...")
        cursor.execute("ALTER TABLE scammers ADD COLUMN files TEXT DEFAULT '[]'")

    # Добавляем таблицу files если её нет
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='files'")
    if not cursor.fetchone():
        print("➕ Создаю таблицу 'files'...")
        cursor.execute('''
                       CREATE TABLE files
                       (
                           id              INTEGER PRIMARY KEY AUTOINCREMENT,
                           file_id         TEXT UNIQUE NOT NULL,
                           file_type       TEXT,
                           caption         TEXT,
                           related_user_id TEXT,
                           uploaded_date   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                       )
                       ''')

    conn.commit()
    conn.close()
    print("✅ База данных успешно обновлена!")


if __name__ == "__main__":
    update_database()
    input("Нажмите Enter для выхода...")