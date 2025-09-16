import os
from motor.motor_asyncio import AsyncIOMotorClient
from mongomock_motor import AsyncMongoMockClient

def get_test_db_url():
    return os.getenv("TEST_MONGODB_URL", "mongodb://localhost:27017/tmhire_test")

def get_test_db_name():
    return os.getenv("TEST_DB_NAME", "tmhire_test")

async def get_test_db():
    """
    Get test database instance - uses mongomock for testing
    """
    client = AsyncMongoMockClient()
    db = client[get_test_db_name()]
    return db

async def clear_test_db(db):
    """
    Clear all collections in test database
    """
    collections = await db.list_collection_names()
    for collection in collections:
        await db[collection].delete_many({})

def get_collection_names():
    """
    Return list of collection names used in the application
    """
    return [
        "users",
        "clients",
        "projects",
        "teams",
        "plants",
        "pumps",
        "transit_mixers",
        "schedules",
        "schedule_calendar"
    ]