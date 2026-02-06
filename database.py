import sqlite3
import os
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_name=None):
        # Для Render.com используем папку /tmp которая сохраняется
        if db_name is None:
            # Проверяем есть ли переменная RENDER
            if os.environ.get('RENDER') or os.environ.get('RENDER_EXTERNAL_HOSTNAME'):
                # На Render используем /tmp
                db_name = "/tmp/scam_database.db"
                logger.info("📁 Режим: Render.com")
            else:
                db_name = "scam_database.db"
                logger.info("📁 Режим: Локальный")

        self.db_path = os.path.abspath(db_name)
        logger.info(f"📁 База данных: {self.db_path}")

        # Создаем папку если её нет
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.cursor = self.conn.cursor()
            self.create_tables()
            logger.info("✅ База данных готова")
        except Exception as e:
            logger.error(f"❌ Ошибка базы данных: {e}")
            raise

    def create_tables(self):
        self.cursor.execute('''
                            CREATE TABLE IF NOT EXISTS scammers
                            (
                                id
                                INTEGER
                                PRIMARY
                                KEY
                                AUTOINCREMENT,
                                user_id
                                TEXT
                                UNIQUE
                                NOT
                                NULL,
                                username
                                TEXT,
                                threat_level
                                INTEGER
                                DEFAULT
                                3,
                                reason
                                TEXT,
                                proof
                                TEXT,
                                files
                                TEXT
                                DEFAULT
                                '[]',
                                added_by
                                INTEGER,
                                added_date
                                TIMESTAMP
                                DEFAULT
                                CURRENT_TIMESTAMP,
                                updated_date
                                TIMESTAMP
                            )
                            ''')

        self.cursor.execute('''
                            CREATE TABLE IF NOT EXISTS files
                            (
                                id
                                INTEGER
                                PRIMARY
                                KEY
                                AUTOINCREMENT,
                                file_id
                                TEXT
                                UNIQUE
                                NOT
                                NULL,
                                file_type
                                TEXT,
                                caption
                                TEXT,
                                related_user_id
                                TEXT,
                                uploaded_date
                                TIMESTAMP
                                DEFAULT
                                CURRENT_TIMESTAMP
                            )
                            ''')

        self.cursor.execute('''
                            CREATE TABLE IF NOT EXISTS admin_log
                            (
                                id
                                INTEGER
                                PRIMARY
                                KEY
                                AUTOINCREMENT,
                                admin_id
                                INTEGER,
                                action
                                TEXT,
                                target_user_id
                                TEXT,
                                timestamp
                                TIMESTAMP
                                DEFAULT
                                CURRENT_TIMESTAMP
                            )
                            ''')

        self.conn.commit()

    def add_scammer(self, user_id, username, threat_level, reason, proof, files_json, added_by):
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO scammers 
                (user_id, username, threat_level, reason, proof, files, added_by, updated_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, threat_level, reason, proof, files_json, added_by, datetime.now()))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка при добавлении скамера: {e}")
            return False

    def find_user(self, query):
        try:
            query = query.strip().replace('@', '')

            # Ищем по ID
            if query.isdigit():
                self.cursor.execute('''
                                    SELECT user_id, username, threat_level, reason, proof, files, added_date
                                    FROM scammers
                                    WHERE user_id = ?
                                    ''', (query,))
                result = self.cursor.fetchone()
                if result:
                    return result, 'id'

            # Ищем по username
            self.cursor.execute('''
                                SELECT user_id, username, threat_level, reason, proof, files, added_date
                                FROM scammers
                                WHERE LOWER(username) = ?
                                ''', (query.lower(),))
            result = self.cursor.fetchone()
            if result:
                return result, 'username'

            return None, None
        except Exception as e:
            logger.error(f"❌ Ошибка при поиске пользователя: {e}")
            return None, None

    def get_all_scammers(self):
        try:
            self.cursor.execute('''
                                SELECT user_id, username, threat_level, reason, added_date
                                FROM scammers
                                ORDER BY threat_level DESC, added_date DESC
                                ''')
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ Ошибка при получении всех записей: {e}")
            return []

    def delete_scammer(self, user_id):
        try:
            self.cursor.execute('DELETE FROM scammers WHERE user_id = ?', (user_id,))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except Exception as e:
            logger.error(f"❌ Ошибка при удалении скамера: {e}")
            return False

    def log_admin_action(self, admin_id, action, target_user_id):
        try:
            self.cursor.execute('''
                                INSERT INTO admin_log (admin_id, action, target_user_id)
                                VALUES (?, ?, ?)
                                ''', (admin_id, action, target_user_id))
            self.conn.commit()
        except Exception as e:
            logger.error(f"❌ Ошибка при логировании: {e}")


db = Database()