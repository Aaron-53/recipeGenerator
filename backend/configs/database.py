from motor.motor_asyncio import AsyncIOMotorClient
from configs import settings


class Database:
    client: AsyncIOMotorClient = None


db = Database()


async def get_database():
    """Get database instance"""
    return db.client[settings.DATABASE_NAME]


async def connect_to_mongo():
    """Connect to MongoDB"""
    print("Connecting to MongoDB...")
    db.client = AsyncIOMotorClient(settings.MONGODB_URL)
    print("Connected to MongoDB successfully!")


async def close_mongo_connection():
    """Close MongoDB connection"""
    print("Closing MongoDB connection...")
    db.client.close()
    print("MongoDB connection closed!")


async def get_collection(collection_name: str):
    """Get a specific collection from the database"""
    database = await get_database()
    return database[collection_name]
