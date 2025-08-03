from app.db.mongodb import plants, transit_mixers
from app.models.plant import PlantModel, PlantCreate, PlantUpdate
from bson import ObjectId
from typing import List, Optional, Dict

async def get_all_plants(user_id: str) -> List[PlantModel]:
    """Get all plants for a user"""
    plant_list = []
    async for plant in plants.find({"user_id": ObjectId(user_id)}):
        plant_list.append(PlantModel(**plant))
    return plant_list

async def get_plant(id: str, user_id: str) -> Optional[PlantModel]:
    """Get a specific plant by ID"""
    plant = await plants.find_one({"_id": ObjectId(id), "user_id": ObjectId(user_id)})
    if plant:
        return PlantModel(**plant)
    return None

async def create_plant(plant: PlantCreate, user_id: str) -> PlantModel:
    """Create a new plant"""
    plant_data = plant.model_dump()
    plant_data["user_id"] = ObjectId(user_id)
    
    result = await plants.insert_one(plant_data)
    
    new_plant = await plants.find_one({"_id": result.inserted_id})
    return PlantModel(**new_plant)

async def update_plant(id: str, plant: PlantUpdate, user_id: str) -> Optional[PlantModel]:
    """Update a plant"""
    plant_data = {k: v for k, v in plant.model_dump().items() if v is not None}
    
    if not plant_data:
        return await get_plant(id, user_id)
    
    await plants.update_one(
        {"_id": ObjectId(id), "user_id": ObjectId(user_id)},
        {"$set": plant_data}
    )
    
    return await get_plant(id, user_id)

async def delete_plant(id: str, user_id: str) -> Dict[str, bool]:
    """Delete a plant and update associated transit mixers"""
    # First, update any transit mixers that belong to this plant
    await transit_mixers.update_many(
        {"plant_id": ObjectId(id)},
        {"$set": {"plant_id": None}}
    )
    
    # Then delete the plant
    result = await plants.delete_one({"_id": ObjectId(id), "user_id": ObjectId(user_id)})
    
    return {"success": result.deleted_count > 0}

async def get_plant_tms(id: str, user_id: str) -> Dict:
    """Get all transit mixers for a specific plant"""
    plant = await get_plant(id, user_id)
    if not plant:
        return {"plant": None, "transit_mixers": []}
    
    tm_list = []
    async for tm in transit_mixers.find({"plant_id": ObjectId(id), "user_id": ObjectId(user_id)}):
        tm_list.append(tm)
    
    return {
        "plant": plant.model_dump(by_alias=True),
        "transit_mixers": tm_list
    } 