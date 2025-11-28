from datetime import datetime
from app.db.mongodb import plants, transit_mixers
from app.models.plant import PlantModel, PlantCreate, PlantUpdate
from app.models.user import UserModel
from bson import ObjectId
from typing import List, Optional, Dict
from pymongo import DESCENDING
from fastapi import HTTPException

async def get_all_plants(current_user: UserModel) -> List[PlantModel]:
    """Get all plants for the current user's company"""
    query = {}
    
    # Super admin can see all plants
    if current_user.role != "super_admin":
        if not current_user.company_id:
            return []  # User not part of a company
        query["company_id"] = ObjectId(current_user.company_id)
    
    plant_list = []
    async for plant in plants.find(query).sort("created_at", DESCENDING):
        plant_list.append(PlantModel(**plant))
    return plant_list

async def get_plant(id: str, current_user: UserModel) -> Optional[PlantModel]:
    """Get a specific plant by ID"""
    query = {"_id": ObjectId(id)}
    
    # Super admin can see all plants
    if current_user.role != "super_admin":
        if not current_user.company_id:
            return None
        query["company_id"] = ObjectId(current_user.company_id)
    
    plant = await plants.find_one(query)
    if plant:
        return PlantModel(**plant)
    return None

async def create_plant(plant: PlantCreate, current_user: UserModel) -> PlantModel:
    """Create a new plant"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    plant_data = plant.model_dump()
    plant_data["company_id"] = ObjectId(current_user.company_id)
    plant_data["created_by"] = ObjectId(current_user.id)
    plant_data["user_id"] = ObjectId(current_user.id)  # Keep for compatibility
    plant_data["created_at"] = datetime.utcnow()
    plant_data["last_updated"] = datetime.utcnow()
    
    result = await plants.insert_one(plant_data)
    
    new_plant = await plants.find_one({"_id": result.inserted_id})
    return PlantModel(**new_plant)

async def update_plant(id: str, plant: PlantUpdate, current_user: UserModel) -> Optional[PlantModel]:
    """Update a plant"""
    plant_data = {k: v for k, v in plant.model_dump().items() if v is not None}
    
    if not plant_data:
        return await get_plant(id, current_user)
    
    query = {"_id": ObjectId(id)}
    # Super admin can update any plant
    if current_user.role != "super_admin":
        if not current_user.company_id:
            raise HTTPException(status_code=403, detail="User must belong to a company")
        query["company_id"] = ObjectId(current_user.company_id)
    
    await plants.update_one(query, {"$set": plant_data})
    
    return await get_plant(id, current_user)

async def delete_plant(id: str, current_user: UserModel) -> Dict[str, bool]:
    """Delete a plant and update associated transit mixers"""
    # Verify plant exists and user has access
    plant = await get_plant(id, current_user)
    if not plant:
        return {"success": False}
    
    # First, update any transit mixers that belong to this plant
    await transit_mixers.update_many(
        {"plant_id": ObjectId(id)},
        {"$set": {"plant_id": None}}
    )
    
    # Then delete the plant
    query = {"_id": ObjectId(id)}
    if current_user.role != "super_admin":
        query["company_id"] = ObjectId(current_user.company_id)
    
    result = await plants.delete_one(query)
    
    return {"success": result.deleted_count > 0}

async def get_plant_tms(id: str, current_user: UserModel) -> Dict:
    """Get all transit mixers for a specific plant"""
    plant = await get_plant(id, current_user)
    if not plant:
        return {"plant": None, "transit_mixers": []}
    
    query = {"plant_id": ObjectId(id)}
    # Filter by company_id if not super admin
    if current_user.role != "super_admin":
        if not current_user.company_id:
            return {"plant": plant.model_dump(by_alias=True), "transit_mixers": []}
        query["company_id"] = ObjectId(current_user.company_id)
    
    tm_list = []
    async for tm in transit_mixers.find(query):
        tm_list.append(tm)
    
    return {
        "plant": plant.model_dump(by_alias=True),
        "transit_mixers": tm_list
    } 