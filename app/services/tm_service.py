from app.db.mongodb import transit_mixers, PyObjectId
from app.models.transit_mixer import TransitMixerModel, TransitMixerCreate, TransitMixerUpdate
from bson import ObjectId
from typing import List, Optional

async def get_all_tms(user_id: str) -> List[TransitMixerModel]:
    """Get all transit mixers for a user"""
    tms = []
    async for tm in transit_mixers.find({"user_id": ObjectId(user_id)}):
        tms.append(TransitMixerModel(**tm))
    return tms

async def get_tm(id: str, user_id: str) -> Optional[TransitMixerModel]:
    """Get a specific transit mixer by ID"""
    tm = await transit_mixers.find_one({"_id": ObjectId(id), "user_id": ObjectId(user_id)})
    if tm:
        return TransitMixerModel(**tm)
    return None

async def create_tm(tm: TransitMixerCreate, user_id: str) -> TransitMixerModel:
    """Create a new transit mixer"""
    tm_data = tm.model_dump()
    tm_data["user_id"] = ObjectId(user_id)
    
    # Convert plant_id to ObjectId if it exists
    if "plant_id" in tm_data and tm_data["plant_id"]:
        tm_data["plant_id"] = ObjectId(tm_data["plant_id"])
    
    result = await transit_mixers.insert_one(tm_data)
    
    new_tm = await transit_mixers.find_one({"_id": result.inserted_id})
    return TransitMixerModel(**new_tm)

async def update_tm(id: str, tm: TransitMixerUpdate, user_id: str) -> Optional[TransitMixerModel]:
    """Update a transit mixer"""
    tm_data = {k: v for k, v in tm.model_dump().items() if v is not None}
    
    # Convert plant_id to ObjectId if it exists
    if "plant_id" in tm_data and tm_data["plant_id"]:
        tm_data["plant_id"] = ObjectId(tm_data["plant_id"])
    
    if not tm_data:
        return await get_tm(id, user_id)
    
    await transit_mixers.update_one(
        {"_id": ObjectId(id), "user_id": ObjectId(user_id)},
        {"$set": tm_data}
    )
    
    return await get_tm(id, user_id)

async def delete_tm(id: str, user_id: str) -> bool:
    """Delete a transit mixer"""
    result = await transit_mixers.delete_one({"_id": ObjectId(id), "user_id": ObjectId(user_id)})
    return result.deleted_count > 0

async def get_average_capacity(user_id: str) -> float:
    """Get the average capacity of all transit mixers for a user"""
    result = await transit_mixers.aggregate([
        {"$match": {"user_id": ObjectId(user_id)}},
        {"$group": {"_id": None, "avg_capacity": {"$avg": "$capacity"}}}
    ]).to_list(1)
    
    if result:
        return result[0]["avg_capacity"]
    return 0.0

async def get_tms_by_plant(plant_id: str, user_id: str) -> List[TransitMixerModel]:
    """Get all transit mixers for a specific plant"""
    tms = []
    async for tm in transit_mixers.find({"plant_id": ObjectId(plant_id), "user_id": ObjectId(user_id)}):
        tms.append(TransitMixerModel(**tm))
    return tms 