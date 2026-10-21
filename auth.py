
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

    connection = sqlite3.connect(DB_PATH)

    try:
        connection.execute(
            """
            INSERT INTO users (username, password_hash)
            VALUES (?, ?)
            """,
            (username, hashed_password),
        )

        connection.commit()
        return True

    except sqlite3.IntegrityError:
        return False

    finally:
        connection.close()


def verify_user(username: str, password: str) -> bool:
    username = username.strip()

    if not username or len(username) > 30:
        return False

    connection = sqlite3.connect(DB_PATH)

    try:
        row = connection.execute(
            """
            SELECT password_hash
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()

    finally:
        connection.close()

    if row is None:
        return False

    return password_hash.verify(password, row[0])
