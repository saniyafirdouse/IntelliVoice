from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME", "intellivoice")

client = None
db = None

# 2026-10-28: give up on an unreachable database after 5 s (the default is 30 s,
# which looked like the assistant "thinking" forever on a network that blocks
# MongoDB). The knowledge engine then answers from its offline copy.
TIMEOUT_MS = 5000

async def connect_to_mongo():
    global client, db
    client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=TIMEOUT_MS, connectTimeoutMS=TIMEOUT_MS)
    db = client[DATABASE_NAME]
    try:
        await db.command("ping")
        print("✅ Connected to MongoDB Atlas")
    except Exception as e:
        # Not fatal: answers come from the offline copy (database/offline_copy/).
        print(f"⚠️  MongoDB Atlas is NOT reachable on this network ({type(e).__name__}). "
              "Answering from the offline copy. Check Atlas > Network Access, or use a phone hotspot.")

async def close_mongo_connection():
    global client
    if client:
        client.close()
        print("❌ MongoDB connection closed")

def get_database():
    return db