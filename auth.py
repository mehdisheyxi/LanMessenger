
import sqlite3

from pwdlib import PasswordHash

from database import DB_PATH

password_hash = PasswordHash.recommended()


def register_user(username: str, password: str) -> bool:
    username = username.strip()

    if not username or len(username) > 30:
        return False

    if len(password) < 8 or len(password) > 128:
        return False

    hashed_password = password_hash.hash(password)

    with sqlite3.connect(DB_PATH) as connection:
        try:
            connection.execute(
                """
                INSERT INTO users (username, password_hash)
                VALUES (?, ?)
                """,
                (username, hashed_password),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def verify_user(username: str, password: str) -> bool:
    username = username.strip()

    if not username or len(username) > 30:
        return False

    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute(
            """
            SELECT password_hash, is_active
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()

    if row is None or not row[1]:
        return False

    return password_hash.verify(password, row[0])


def create_admin(username: str, password: str) -> bool:
    username = username.strip()

    if not username or len(username) > 30:
        return False

    if len(password) < 8 or len(password) > 128:
        return False

    hashed_password = password_hash.hash(password)

    with sqlite3.connect(DB_PATH) as connection:
        try:
            connection.execute(
                """
                INSERT INTO users (username, password_hash, role)
                VALUES (?, ?, 'admin')
                """,
                (username, hashed_password),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def get_user(username: str):
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT id, username, role, is_active, created_at
            FROM users
            WHERE username = ?
            """,
            (username.strip(),),
        ).fetchone()

    return dict(row) if row else None


def list_users():
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT id, username, role, is_active, created_at
            FROM users
            ORDER BY id
            """
        ).fetchall()

    return [dict(row) for row in rows]


def set_user_active(user_id: int, active: bool) -> bool:
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(
            """
            UPDATE users
            SET is_active = ?
            WHERE id = ? AND role = 'user'
            """,
            (int(active), user_id),
        )
        return cursor.rowcount > 0


def change_user_password(user_id: int, new_password: str) -> bool:
    if len(new_password) < 8 or len(new_password) > 128:
        return False

    hashed_password = password_hash.hash(new_password)

    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(
            """
            UPDATE users
            SET password_hash = ?
            WHERE id = ? AND role = 'user'
            """,
            (hashed_password, user_id),
        )
        return cursor.rowcount > 0


def delete_user(user_id: int) -> bool:
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(
            """
            DELETE FROM users
            WHERE id = ? AND role = 'user'
            """,
            (user_id,),
        )
        return cursor.rowcount > 0


def get_setting(key: str, default: str = "") -> str:
    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute(
            "SELECT value FROM settings WHERE key = ?",
            (key,),
        ).fetchone()

    return row[0] if row else default


def set_setting(key: str, value: str):
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
