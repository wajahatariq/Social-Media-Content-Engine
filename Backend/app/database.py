import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGODB_URL")
client = AsyncIOMotorClient(MONGO_URL)
db = client.techware_hub_db

# Collections
clients_collection = db.get_collection("clients")
calendars_collection = db.get_collection("content_calendars")

async def get_db_status():
    try:
        await client.admin.command('ping')
        return "Connected to MongoDB"
    except Exception as e:
        return f"Database Error: {e}"