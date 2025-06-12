from app.db.mongodb import pumps, PyObjectId
from app.models.pump import PumpModel, PumpCreate, PumpUpdate
from bson import ObjectId
from typing import List, Optional
from datetime import datetime

async def get_all_pumps(user_id: str) -> List[PumpModel]:
    """Get all pumps for a user"""
    result = []
    async for pump in pumps.find({"user_id": ObjectId(user_id)}):
        result.append(PumpModel(**pump))
    return result

async def get_pump(id: str, user_id: str) -> Optional[PumpModel]:
    """Get a specific pump by ID"""
    pump = await pumps.find_one({"_id": ObjectId(id), "user_id": ObjectId(user_id)})
    if pump:
        return PumpModel(**pump)
    return None

async def create_pump(pump: PumpCreate, user_id: str) -> PumpModel:
    """Create a new pump"""
    pump_data = pump.model_dump()
    pump_data["user_id"] = ObjectId(user_id)
    if "plant_id" in pump_data and pump_data["plant_id"]:
        pump_data["plant_id"] = ObjectId(pump_data["plant_id"])
    pump_data["created_at"] = datetime.utcnow()
    result = await pumps.insert_one(pump_data)
    new_pump = await pumps.find_one({"_id": result.inserted_id})
    return PumpModel(**new_pump)

async def update_pump(id: str, pump: PumpUpdate, user_id: str) -> Optional[PumpModel]:
    """Update a pump"""
    pump_data = {k: v for k, v in pump.model_dump().items() if v is not None}
    if "plant_id" in pump_data and pump_data["plant_id"]:
        pump_data["plant_id"] = ObjectId(pump_data["plant_id"])
    if not pump_data:
        return await get_pump(id, user_id)
    await pumps.update_one(
        {"_id": ObjectId(id), "user_id": ObjectId(user_id)},
        {"$set": pump_data}
    )
    return await get_pump(id, user_id)

async def delete_pump(id: str, user_id: str) -> bool:
    """Delete a pump"""
    result = await pumps.delete_one({"_id": ObjectId(id), "user_id": ObjectId(user_id)})
    return result.deleted_count > 0

async def get_pumps_by_plant(plant_id: str, user_id: str) -> List[PumpModel]:
    """Get all pumps for a specific plant"""
    result = []
    async for pump in pumps.find({"plant_id": ObjectId(plant_id), "user_id": ObjectId(user_id)}):
        result.append(PumpModel(**pump))
    return result

