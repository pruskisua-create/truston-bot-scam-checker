import sqlite3
import os
import json
import logging

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        # Всегда используем одну и ту же базу
        self.db_path = "truston_scam.db"
        logger.info(f"📁 База данных: {self.db_path}")

        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        """Создает таблицы если их нет"""
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
                                added_date
                                TIMESTAMP
                                DEFAULT
                                CURRENT_TIMESTAMP
                            )
                            ''')
        self.conn.commit()
        logger.info("✅ Таблицы созданы")

    def add_scammer(self, user_id, username, threat_level, reason, proof, added_by):
        """Добавляет пользователя в базу"""
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO scammers 
                (user_id, username, threat_level, reason, proof)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, username, threat_level, reason, proof))
            self.conn.commit()
            logger.info(f"✅ Добавлен: ID={user_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return False

    def find_user(self, query):
        """Ищет пользователя по ID или username"""
        query = query.strip().replace('@', '')

        # Ищем по ID
        if query.isdigit():
            self.cursor.execute('''
                                SELECT user_id, username, threat_level, reason, proof, added_date
                                FROM scammers
                                WHERE user_id = ?
                                ''', (query,))
            result = self.cursor.fetchone()
            if result:
                return result, 'id'

        # Ищем по username
        self.cursor.execute('''
                            SELECT user_id, username, threat_level, reason, proof, added_date
                            FROM scammers
                            WHERE username LIKE ?
                            ''', (f"%{query}%",))
        result = self.cursor.fetchone()
        if result:
            return result, 'username'

        return None, None

    def get_all_scammers(self):
        """Получает все записи"""
        self.cursor.execute('''
                            SELECT user_id, username, threat_level, reason, added_date
                            FROM scammers
                            ORDER BY added_date DESC
                            ''')
        return self.cursor.fetchall()

    def delete_scammer(self, user_id):
        """Удаляет запись"""
        self.cursor.execute('DELETE FROM scammers WHERE user_id = ?', (user_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0


db = Database()