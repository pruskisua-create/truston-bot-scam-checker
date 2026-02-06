import sqlite3
import os
import json
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_name=None):
        # ВСЕГДА используем одну и ту же папку - НЕ /tmp/
        if db_name is None:
            db_name = "scam_database.db"

        self.db_path = os.path.abspath(db_name)
        logger.info(f"📁 База данных: {self.db_path}")

        # Создаем папку если её нет
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

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
            # Логируем добавление
            logger.info(f"➕ Добавляем пользователя: ID={user_id}, username={username}")

            self.cursor.execute('''
                INSERT OR REPLACE INTO scammers 
                (user_id, username, threat_level, reason, proof, files, added_by, updated_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, threat_level, reason, proof, files_json, added_by, datetime.now()))
            self.conn.commit()
            logger.info(f"✅ Успешно добавлен: ID={user_id}")
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
            result = self.cursor.fetchone()
            if result:
                logger.info(f"✅ Найден в check_user: ID={user_id}, username={result[1]}")
            return result
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке пользователя: {e}")
            self.log_error(str(e), "check_user")
            return None

    def check_user_by_username(self, username):
        try:
            username_clean = username.lower().replace('@', '')
            logger.info(f"🔍 check_user_by_username: ищем '{username_clean}'")

            self.cursor.execute('''
                                SELECT user_id, username, threat_level, reason, proof, files, added_date
                                FROM scammers
                                WHERE LOWER(TRIM(REPLACE(username, '@', ''))) = ?
                                ''', (username_clean,))
            result = self.cursor.fetchone()
            if result:
                logger.info(f"✅ Найден в check_user_by_username: '{username}' -> {result[1]}")
            return result
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке по юзернейму: {e}")
            self.log_error(str(e), "check_user_by_username")
            return None

    def find_user(self, query):
        try:
            original_query = query
            query = query.strip()
            logger.info(f"🔍 ПОИСК: ввели '{original_query}' -> очистили '{query}'")

            # Удаляем @ если есть
            query = query.replace('@', '')
            logger.info(f"🔍 ПОИСК после удаления @: '{query}'")

            # Сначала ищем по точному совпадению ID
            if query.isdigit():
                logger.info(f"🔍 Ищем по ID: '{query}'")
                result = self.check_user(query)
                if result:
                    logger.info(f"✅ НАЙДЕН ПО ID: {query} -> username: {result[1]}")
                    return result, 'id'
                else:
                    logger.info(f"❌ НЕ НАЙДЕН ПО ID: {query}")

            # Ищем по username (без учета регистра)
            username_clean = query.lower()
            logger.info(f"🔍 Ищем по юзернейму: '{username_clean}'")

            # Пробуем разные варианты поиска
            try:
                self.cursor.execute('''
                                    SELECT user_id, username, threat_level, reason, proof, files, added_date
                                    FROM scammers
                                    WHERE LOWER(TRIM(REPLACE(username, '@', ''))) = ?
                                    ''', (username_clean,))
                result = self.cursor.fetchone()

                if result:
                    logger.info(f"✅ НАЙДЕН ПО USERNAME: запрос '{username_clean}' -> найден '{result[1]}'")
                    return result, 'username'
            except Exception as e:
                logger.error(f"⚠️ Ошибка при поиске по username: {e}")

            # Показываем что есть в базе для отладки
            logger.info(f"📋 Для отладки - все записи в базе:")
            all_records = self.get_all_scammers()
            for i, (user_id, username, level, reason, date) in enumerate(all_records[:20], 1):
                logger.info(f"  {i:2}. ID: {user_id} | Username: '{username}' | Level: {level}")

            logger.info(f"❌ НЕ НАЙДЕН ВООБЩЕ: '{original_query}'")
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
            results = self.cursor.fetchall()
            logger.info(f"📋 Получено всех записей: {len(results)}")
            return results
        except Exception as e:
            logger.error(f"❌ Ошибка при получении всех записей: {e}")
            self.log_error(str(e), "get_all_scammers")
            return []

    def delete_scammer(self, user_id):
        try:
            logger.info(f"🗑️ Удаление пользователя: ID={user_id}")
            self.cursor.execute('DELETE FROM scammers WHERE user_id = ?', (user_id,))
            self.conn.commit()
            deleted = self.cursor.rowcount > 0
            logger.info(f"{'✅ Успешно удален' if deleted else '❌ Не найден для удаления'}: ID={user_id}")
            return deleted
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
            logger.info(f"📝 Лог админа: {action} для {target_user_id}")
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

    def debug_search(self, query):
        """Отладочная функция для поиска"""
        logger.info(f"🔧 ОТЛАДКА ПОИСКА для: '{query}'")

        # Очищаем запрос
        clean_query = query.strip().replace('@', '')
        logger.info(f"🔧 Очищенный запрос: '{clean_query}'")

        # Проверяем по ID
        if clean_query.isdigit():
            logger.info(f"🔧 Проверяем по ID: {clean_query}")
            self.cursor.execute("SELECT user_id, username FROM scammers WHERE user_id = ?", (clean_query,))
            result = self.cursor.fetchone()
            if result:
                logger.info(f"🔧 Найден по ID: {result}")
            else:
                logger.info(f"🔧 Не найден по ID")

        # Проверяем по username
        username_search = clean_query.lower()
        logger.info(f"🔧 Проверяем по username (нижний регистр): '{username_search}'")

        # Пробуем разные варианты
        self.cursor.execute("SELECT user_id, username FROM scammers")
        all_users = self.cursor.fetchall()

        logger.info(f"🔧 Всего записей в базе: {len(all_users)}")
        matches = []

        for user_id, username in all_users:
            if username:
                clean_username = username.lower().replace('@', '')
                if username_search in clean_username or clean_username in username_search:
                    matches.append((user_id, username))
                    logger.info(f"🔧 СОВПАДЕНИЕ: ID={user_id}, username='{username}'")

        logger.info(f"🔧 Найдено совпадений: {len(matches)}")
        return matches


db = Database()