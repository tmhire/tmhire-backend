import motor.motor_asyncio
from bson import ObjectId
import os
from dotenv import load_dotenv
from pydantic_core import core_schema
from pydantic import GetCoreSchemaHandler
from typing import Annotated, Any

# Load environment variables
load_dotenv()

# MongoDB connection string
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "concrete_supply")

# Create client
client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
database = client[DB_NAME]

# Collections
users = database.users
transit_mixers = database.transit_mixers
schedules = database.schedules
plants = database.plants
schedule_calendar = database.schedule_calendar
clients = database.clients
projects = database.projects
pumps = database.pumps

# Helper class for converting between MongoID and string
class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: Any, _handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.union_schema([
            core_schema.is_instance_schema(ObjectId),
            core_schema.chain_schema([
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(cls.validate),
            ]),
        ])
    
    @classmethod
    def validate(cls, value):
        if not ObjectId.is_valid(value):
            raise ValueError("Invalid ObjectId")
        return ObjectId(value) 