import sqlite3
import os
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_name=None):
        if db_name is None:
            # Для Railway используем /tmp, для ПК - локальную папку
            if "RAILWAY" in os.environ:
                db_name = "/tmp/scam_database.db"
            else:
                db_name = "scam_database.db"

        self.db_path = os.path.abspath(db_name)
        logger.info(f"📁 База данных: {self.db_path}")

        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.cursor = self.conn.cursor()
            self.create_tables()
            self.backup_check()
            logger.info("✅ База данных готова")
        except Exception as e:
            logger.error(f"❌ Ошибка базы данных: {e}")
            raise

    def backup_check(self):
        """Проверяет и создает резервную копию базы данных"""
        try:
            if os.path.exists(self.db_path):
                # Проверяем размер базы данных
                size = os.path.getsize(self.db_path)
                logger.info(f"📊 Размер базы данных: {size} байт")

                # Создаем резервную копию раз в день
                backup_dir = "backups"
                if not os.path.exists(backup_dir):
                    os.makedirs(backup_dir)

                backup_file = os.path.join(backup_dir, f"scam_db_backup_{datetime.now().strftime('%Y%m%d')}.db")

                if not os.path.exists(backup_file):
                    import shutil
                    shutil.copy2(self.db_path, backup_file)
                    logger.info(f"✅ Создана резервная копия: {backup_file}")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось создать резервную копию: {e}")

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

        # Таблица для логов ошибок
        self.cursor.execute('''
                            CREATE TABLE IF NOT EXISTS error_logs
                            (
                                id
                                INTEGER
                                PRIMARY
                                KEY
                                AUTOINCREMENT,
                                error_message
                                TEXT,
                                error_type
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
            self.log_error(str(e), "add_scammer")
            return False

    def check_user(self, user_id):
        try:
            self.cursor.execute('''
                                SELECT user_id, username, threat_level, reason, proof, files, added_date
                                FROM scammers
                                WHERE user_id = ?
                                ''', (user_id,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке пользователя: {e}")
            self.log_error(str(e), "check_user")
            return None

    def check_user_by_username(self, username):
        try:
            username = username.lower().replace('@', '')
            self.cursor.execute('''
                                SELECT user_id, username, threat_level, reason, proof, files, added_date
                                FROM scammers
                                WHERE LOWER(username) = ?
                                ''', (username,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке по юзернейму: {e}")
            self.log_error(str(e), "check_user_by_username")
            return None

    def find_user(self, query):
        try:
            query = query.strip().replace('@', '')

            if query.isdigit():
                result = self.check_user(query)
                if result:
                    return result, 'id'

            result = self.check_user_by_username(query)
            if result:
                return result, 'username'

            return None, None
        except Exception as e:
            logger.error(f"❌ Ошибка при поиске пользователя: {e}")
            self.log_error(str(e), "find_user")
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
            self.log_error(str(e), "get_all_scammers")
            return []

    def delete_scammer(self, user_id):
        try:
            self.cursor.execute('DELETE FROM scammers WHERE user_id = ?', (user_id,))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except Exception as e:
            logger.error(f"❌ Ошибка при удалении скамера: {e}")
            self.log_error(str(e), "delete_scammer")
            return False

    def log_admin_action(self, admin_id, action, target_user_id):
        try:
            self.cursor.execute('''
                                INSERT INTO admin_log (admin_id, action, target_user_id)
                                VALUES (?, ?, ?)
                                ''', (admin_id, action, target_user_id))
            self.conn.commit()
        except Exception as e:
            logger.error(f"❌ Ошибка при логировании действия админа: {e}")

    def log_error(self, error_message, error_type):
        """Логирует ошибки в базу данных"""
        try:
            self.cursor.execute('''
                                INSERT INTO error_logs (error_message, error_type)
                                VALUES (?, ?)
                                ''', (error_message, error_type))
            self.conn.commit()
        except Exception as e:
            logger.error(f"❌ Ошибка при логировании ошибки: {e}")


db = Database()