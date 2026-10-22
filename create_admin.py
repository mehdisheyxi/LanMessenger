
from getpass import getpass
from auth import create_admin

username = input("Admin username: ").strip()
password = getpass("Admin password: ")
confirm_password = getpass("Confirm password: ")

if password != confirm_password:
    print("Passwords do not match!")
elif create_admin(username, password):
    print("Admin created successfully.")
else:
    print("Failed: username may exist or input is invalid.")
