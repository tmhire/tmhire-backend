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
    
    result = await transit_mixers.insert_one(tm_data)
    
    new_tm = await transit_mixers.find_one({"_id": result.inserted_id})
    return TransitMixerModel(**new_tm)

async def update_tm(id: str, tm: TransitMixerUpdate, user_id: str) -> Optional[TransitMixerModel]:
    """Update an existing transit mixer"""
    # Filter out None values
    tm_data = {k: v for k, v in tm.model_dump().items() if v is not None}
    
    if not tm_data:
        # No update data provided
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
    """Calculate average capacity of all transit mixers for a user"""
    tms = await get_all_tms(user_id)
    
    if not tms:
        return 0.0
    
    total_capacity = sum(tm.capacity for tm in tms)
    return total_capacity / len(tms) 