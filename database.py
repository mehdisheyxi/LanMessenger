
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

        # جدول پیام‌های خصوصی
        connection.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                recipient_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_read INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (sender_id)
                    REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (recipient_id)
                    REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # بهینه‌سازی جست‌وجوی پیام‌های دریافتی و گفتگوها
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_recipient
            ON messages (recipient_id, is_read, id)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation
            ON messages (sender_id, recipient_id, id)
        """)

        connection.commit()

    finally:
        connection.close()


def search_users(query: str, current_user_id: int):
    query = query.strip()

    if not query:
        return []

    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row

        rows = connection.execute(
            """
            SELECT id, username
            FROM users
            WHERE username LIKE ? COLLATE NOCASE
              AND id != ?
              AND is_active = 1
            ORDER BY username
            LIMIT 20
            """,
            (f"%{query}%", current_user_id),
        ).fetchall()

    return [dict(row) for row in rows]


def save_private_message(
    sender_id: int,
    recipient_id: int,
    message: str,
):
    message = message.strip()

    if not message or len(message) > 1000:
        return None

    if sender_id == recipient_id:
        return None

    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(
            """
            INSERT INTO messages (
                sender_id,
                recipient_id,
                message
            )
            SELECT ?, ?, ?
            WHERE EXISTS (
                SELECT 1 FROM users
                WHERE id = ? AND is_active = 1
            )
            AND EXISTS (
                SELECT 1 FROM users
                WHERE id = ? AND is_active = 1
            )
            """,
            (
                sender_id,
                recipient_id,
                message,
                sender_id,
                recipient_id,
            ),
        )

        if cursor.rowcount == 0:
            return None

        return cursor.lastrowid


def get_private_messages(
    user_id: int,
    other_user_id: int,
    limit: int = 100,
):
    limit = max(1, min(limit, 100))

    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row

        rows = connection.execute(
            """
            SELECT
                id,
                sender_id,
                recipient_id,
                message,
                created_at,
                is_read
            FROM messages
            WHERE (
                sender_id = ? AND recipient_id = ?
            )
            OR (
                sender_id = ? AND recipient_id = ?
            )
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                user_id,
                other_user_id,
                other_user_id,
                user_id,
                limit,
            ),
        ).fetchall()

    return [dict(row) for row in reversed(rows)]



def mark_messages_read(
    recipient_id: int,
    sender_id: int,
):
    with sqlite3.connect(DB_PATH) as connection:
        # شناسه پیام‌هایی که هنوز خوانده نشده‌اند
        rows = connection.execute(
            """
            SELECT id
            FROM messages
            WHERE recipient_id = ?
              AND sender_id = ?
              AND is_read = 0
            """,
            (recipient_id, sender_id),
        ).fetchall()

        message_ids = [row[0] for row in rows]

        if not message_ids:
            return []

        connection.execute(
            """
            UPDATE messages
            SET is_read = 1
            WHERE recipient_id = ?
              AND sender_id = ?
              AND is_read = 0
            """,
            (recipient_id, sender_id),
        )

        return message_ids


