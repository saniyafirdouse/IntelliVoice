"""
Create (or reset the password of) an admin account.

Run from the backend/ folder:
    python create_admin.py

It asks for name, email and password, and saves the admin in the MongoDB
"users" collection with a hashed password. There is no public admin
sign-up on purpose: only someone with database access can make admins.
"""

import asyncio
import getpass

from database.connection import close_mongo_connection, connect_to_mongo, get_database
from utils.auth import hash_password


async def main():
    name = input("Admin name: ").strip()
    email = input("Admin email: ").strip().lower()
    password = getpass.getpass("Password (min 8 characters, hidden while typing): ")
    if len(password) < 8 or "@" not in email or not name:
        print("❌ Need a name, a valid email and a password of at least 8 characters.")
        return

    await connect_to_mongo()
    db = get_database()
    await db["users"].update_one(
        {"email": email},
        {"$set": {"name": name, "email": email, "role": "admin",
                  "password_hash": hash_password(password)}},
        upsert=True,
    )
    print(f"✅ Admin account ready: {email}")
    await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(main())
