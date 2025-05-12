from app.db.mongodb import clients, PyObjectId, schedules
from app.models.client import ClientModel, ClientCreate, ClientUpdate
from bson import ObjectId
from datetime import datetime
from typing import List, Optional, Dict

async def get_all_clients(user_id: str) -> List[ClientModel]:
    """Get all clients for a user"""
    client_list = []
    async for client in clients.find({"user_id": ObjectId(user_id)}):
        client_list.append(ClientModel(**client))
    return client_list

async def get_client(id: str, user_id: str) -> Optional[ClientModel]:
    """Get a specific client by ID"""
    client = await clients.find_one({"_id": ObjectId(id), "user_id": ObjectId(user_id)})
    if client:
        return ClientModel(**client)
    return None

async def create_client(client: ClientCreate, user_id: str) -> ClientModel:
    """Create a new client"""
    client_data = client.model_dump()
    client_data["user_id"] = ObjectId(user_id)
    client_data["created_at"] = datetime.utcnow()
    client_data["last_updated"] = datetime.utcnow()
    
    result = await clients.insert_one(client_data)
    
    new_client = await clients.find_one({"_id": result.inserted_id})
    return ClientModel(**new_client)

async def update_client(id: str, client: ClientUpdate, user_id: str) -> Optional[ClientModel]:
    """Update a client"""
    client_data = {k: v for k, v in client.model_dump().items() if v is not None}
    
    if not client_data:
        return await get_client(id, user_id)
    
    client_data["last_updated"] = datetime.utcnow()
    
    await clients.update_one(
        {"_id": ObjectId(id), "user_id": ObjectId(user_id)},
        {"$set": client_data}
    )
    
    return await get_client(id, user_id)

async def delete_client(id: str, user_id: str) -> Dict[str, bool]:
    """Delete a client and check for dependencies"""
    # Check if this client has any associated schedules
    has_schedules = await schedules.find_one({
        "user_id": ObjectId(user_id),
        "client_id": ObjectId(id)
    })
    
    if has_schedules:
        return {
            "success": False,
            "message": "Cannot delete client with associated schedules"
        }
    
    # Delete the client if no dependencies
    result = await clients.delete_one({
        "_id": ObjectId(id),
        "user_id": ObjectId(user_id)
    })
    
    return {
        "success": result.deleted_count > 0,
        "message": "Client deleted successfully" if result.deleted_count > 0 else "Client not found"
    }

async def get_client_schedules(id: str, user_id: str) -> Dict:
    """Get all schedules for a specific client"""
    client = await get_client(id, user_id)
    if not client:
        return {"client": None, "schedules": []}
    
    schedule_list = []
    async for schedule in schedules.find({"client_id": ObjectId(id), "user_id": ObjectId(user_id)}):
        schedule_list.append(schedule)
    
    return {
        "client": client.model_dump(by_alias=True),
        "schedules": schedule_list
    } 