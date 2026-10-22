
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "lanmessenger.db"


def init_db():
    connection = sqlite3.connect(DB_PATH)

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # بررسی ستون‌های موجود برای حفظ دیتابیس قبلی
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(users)"
            ).fetchall()
        }

        if "role" not in columns:
            connection.execute("""
                ALTER TABLE users
                ADD COLUMN role TEXT NOT NULL DEFAULT 'user'
            """)

        if "is_active" not in columns:
            connection.execute("""
                ALTER TABLE users
                ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1
            """)

        # تنظیمات برنامه
        connection.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # ثبت‌نام عمومی در شروع فعال است
        connection.execute("""
            INSERT OR IGNORE INTO settings (key, value)
            VALUES ('registration_enabled', '1')
        """)

        connection.commit()

    finally:
        connection.close()
