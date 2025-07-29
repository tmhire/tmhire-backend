from app.db.mongodb import clients, projects, schedules
from app.models.client import ClientModel, ClientCreate, ClientUpdate
from bson import ObjectId
from datetime import datetime
from typing import List, Optional, Dict, Any

async def get_all_clients(user_id: str) -> List[ClientModel]:
    """Get all clients for a user"""
    client_list = []
    async for client in clients.find({"user_id": ObjectId(user_id)}):
        client_list.append(ClientModel(**client))
    return client_list

async def get_client(id: str, user_id: str) -> Optional[ClientModel]:
    """Get a specific client by ID"""
    if id is None:
        return None
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
    async for project in projects.find({"client_id": ObjectId(id), "user_id": ObjectId(user_id)}):
        async for schedule in schedules.find({"project_id": ObjectId(project["_id"]), "user_id": ObjectId(user_id)}):
            schedule_list.append(schedule)
    
    return {
        "client": client.model_dump(by_alias=True),
        "schedules": schedule_list
    }

async def get_client_stats(id: str, user_id: str) -> Dict[str, Any]:
    """Get statistics for a specific client including volume metrics and trip summaries"""
    client_schedule_list = await get_client_schedules(id, user_id)
    client = client_schedule_list["client"]
    all_schedules = client_schedule_list["schedules"]
    if not client:
        return {}
    
    # Initialize stats
    total_scheduled = 0
    total_delivered = 0
    pending_volume = 0
    trips = []
    
    # Query for all schedules for this client
    async for schedule in all_schedules:
        # Sum up scheduled volume from input parameters
        input_params = schedule.get("input_params", {})
        quantity = input_params.get("quantity", 0)
        total_scheduled += quantity
        
        # Get completed trips (delivered volume)
        completed_volume = 0
        schedule_trips = []
        
        for trip in schedule.get("output_table", []):
            # Extract relevant trip information
            trip_date = None
            trip_tm = trip.get("tm_id", "")
            trip_volume = 0
            
            # Get trip date
            plant_start = trip.get("plant_start")
            if isinstance(plant_start, datetime):
                trip_date = plant_start.date()
            elif isinstance(plant_start, str):
                try:
                    trip_date = datetime.fromisoformat(plant_start).date()
                except ValueError:
                    pass
            
            # Get trip volume (use capacity progression)
            completed_capacity = trip.get("completed_capacity", 0)
            trip_volume = completed_capacity - completed_volume
            completed_volume = completed_capacity
            
            # Add to trip list if we have enough information
            if trip_date and trip_tm and trip_volume > 0:
                tm = await get_tm_identifier(trip_tm, user_id)
                schedule_trips.append({
                    "date": trip_date.strftime("%Y-%m-%d"),
                    "tm": tm,
                    "volume": f"{trip_volume} m³"
                })
        
        # Add to totals
        if schedule.get("status") == "completed":
            total_delivered += completed_volume
        else:
            # For incomplete schedules, use the completed capacity from the last trip
            if schedule.get("output_table"):
                last_trip = schedule["output_table"][-1]
                delivered = last_trip.get("completed_capacity", 0)
                total_delivered += delivered
                pending_volume += (quantity - delivered)
            else:
                pending_volume += quantity
        
        # Add trips to the overall list (limit to most recent ones)
        trips.extend(schedule_trips)
    
    # Sort trips by date (most recent first) and limit to 10
    trips.sort(key=lambda x: x["date"], reverse=True)
    trips = trips[:10]
    
    return {
        "client_id": client.name,
        "total_scheduled": f"{total_scheduled} m³",
        "total_delivered": f"{total_delivered} m³",
        "pending_volume": f"{pending_volume} m³",
        "trips": trips
    }

async def get_tm_identifier(tm_id: str, user_id: str) -> str:
    """Helper function to get the TM identifier (registration number) from its ID"""
    from app.db.mongodb import transit_mixers
    
    # Try to get the TM identifier from the database
    tm = await transit_mixers.find_one({"_id": ObjectId(tm_id), "user_id": ObjectId(user_id)})
    if tm:
        return tm.get("identifier", tm_id)
    return tm_id 