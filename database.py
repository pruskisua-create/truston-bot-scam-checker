import sqlite3
import os
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.db_path = "scam_database.db"
        logger.info(f"📁 База: {os.path.abspath(self.db_path)}")

        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        logger.info("✅ База готова")

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
                                CURRENT_TIMESTAMP
                            )
                            ''')
        self.conn.commit()

    def add_scammer(self, user_id, username, threat_level, reason, proof, files_json, added_by):
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO scammers 
                (user_id, username, threat_level, reason, proof, files, added_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, threat_level, reason, proof, files_json, added_by))
            self.conn.commit()
            logger.info(f"✅ Добавлен: ID={user_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return False

    def find_user(self, query):
        query = query.strip().replace('@', '')

        # Ищем по ID
        if query.isdigit():
            self.cursor.execute(
                'SELECT user_id, username, threat_level, reason, proof, files, added_date FROM scammers WHERE user_id = ?',
                (query,))
            result = self.cursor.fetchone()
            if result:
                return result, 'id'

        # Ищем по username
        self.cursor.execute(
            'SELECT user_id, username, threat_level, reason, proof, files, added_date FROM scammers WHERE LOWER(username) = ?',
            (query.lower(),))
        result = self.cursor.fetchone()
        if result:
            return result, 'username'

        return None, None

    def get_all_scammers(self):
        self.cursor.execute(
            'SELECT user_id, username, threat_level, reason, added_date FROM scammers ORDER BY added_date DESC')
        return self.cursor.fetchall()

    def delete_scammer(self, user_id):
        self.cursor.execute('DELETE FROM scammers WHERE user_id = ?', (user_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0


db = Database()