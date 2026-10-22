
import sqlite3
from getpass import getpass
from database import DB_PATH


username = input("Admin username to delete: ").strip()

if not username:
    print("Username cannot be empty.")
    raise SystemExit

confirm = input(
    f"Are you sure you want to delete admin '{username}'? (yes/no): "
).strip().lower()

if confirm != "yes":
    print("Operation cancelled.")
    raise SystemExit

with sqlite3.connect(DB_PATH) as connection:
    connection.row_factory = sqlite3.Row

    admin = connection.execute(
        """
        SELECT id, username, role
        FROM users
        WHERE username = ? COLLATE NOCASE
          AND role = 'admin'
        """,
        (username,),
    ).fetchone()

    if admin is None:
        print("Admin account not found.")
        raise SystemExit

    admin_count = connection.execute(
        "SELECT COUNT(*) FROM users WHERE role = 'admin'"
    ).fetchone()[0]

    if admin_count <= 1:
        print("Cannot delete the last admin account.")
        raise SystemExit

    password = getpass("Your admin password: ")

    stored_hash = connection.execute(
        "SELECT password_hash FROM users WHERE username = ? COLLATE NOCASE",
        (username,),
    ).fetchone()

    from auth import password_hash

    if not password_hash.verify(password, stored_hash["password_hash"]):
        print("Incorrect password.")
        raise SystemExit

    connection.execute(
        "DELETE FROM users WHERE id = ? AND role = 'admin'",
        (admin["id"],),
    )

    print(f"Admin '{username}' deleted successfully.")
