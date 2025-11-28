from app.db.mongodb import clients, projects, schedules
from app.models.client import ClientModel, ClientCreate, ClientUpdate
from app.models.user import UserModel
from bson import ObjectId
from datetime import datetime
from typing import List, Optional, Dict, Any
from pymongo import DESCENDING
from fastapi import HTTPException

async def get_all_clients(current_user: UserModel) -> List[ClientModel]:
    """Get all clients for the current user's company"""
    query = {}
    
    # Super admin can see all clients
    if current_user.role != "super_admin":
        if not current_user.company_id:
            return []
        query["company_id"] = ObjectId(current_user.company_id)
    
    client_list = []
    async for client in clients.find(query).sort("created_at", DESCENDING):
        client_list.append(ClientModel(**client))
    return client_list

async def get_client(id: str, current_user: UserModel) -> Optional[ClientModel]:
    """Get a specific client by ID"""
    if id is None:
        return None
    
    query = {"_id": ObjectId(id)}
    # Super admin can see all clients
    if current_user.role != "super_admin":
        if not current_user.company_id:
            return None
        query["company_id"] = ObjectId(current_user.company_id)
    
    client = await clients.find_one(query)
    if client:
        return ClientModel(**client)
    return None

async def create_client(client: ClientCreate, current_user: UserModel) -> ClientModel:
    """Create a new client"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    client_data = client.model_dump()
    client_data["company_id"] = ObjectId(current_user.company_id)
    client_data["created_by"] = ObjectId(current_user.id)
    client_data["user_id"] = ObjectId(current_user.id)  # Keep for compatibility
    client_data["created_at"] = datetime.utcnow()
    client_data["last_updated"] = datetime.utcnow()
    
    result = await clients.insert_one(client_data)
    
    new_client = await clients.find_one({"_id": result.inserted_id})
    return ClientModel(**new_client)

async def update_client(id: str, client: ClientUpdate, current_user: UserModel) -> Optional[ClientModel]:
    """Update a client"""
    client_data = {k: v for k, v in client.model_dump().items() if v is not None}
    
    if not client_data:
        return await get_client(id, current_user)
    
    client_data["last_updated"] = datetime.utcnow()
    
    query = {"_id": ObjectId(id)}
    # Super admin can update any client
    if current_user.role != "super_admin":
        if not current_user.company_id:
            raise HTTPException(status_code=403, detail="User must belong to a company")
        query["company_id"] = ObjectId(current_user.company_id)
    
    await clients.update_one(query, {"$set": client_data})
    
    return await get_client(id, current_user)

async def delete_client(id: str, current_user: UserModel) -> Dict[str, bool]:
    """Delete a client and check for dependencies"""
    # Verify client exists and user has access
    client = await get_client(id, current_user)
    if not client:
        return {
            "success": False,
            "message": "Client not found"
        }
    
    # Check if this client has any associated schedules
    schedule_query = {"client_id": ObjectId(id)}
    if current_user.role != "super_admin":
        schedule_query["company_id"] = ObjectId(current_user.company_id)
    
    has_schedules = await schedules.find_one(schedule_query)
    
    if has_schedules:
        return {
            "success": False,
            "message": "Cannot delete client with associated schedules"
        }
    
    # Delete the client if no dependencies
    query = {"_id": ObjectId(id)}
    if current_user.role != "super_admin":
        query["company_id"] = ObjectId(current_user.company_id)
    
    result = await clients.delete_one(query)
    
    return {
        "success": result.deleted_count > 0,
        "message": "Client deleted successfully" if result.deleted_count > 0 else "Client not found"
    }

async def get_client_schedules(id: str, current_user: UserModel) -> Dict:
    """Get all schedules for a specific client"""
    client = await get_client(id, current_user)
    if not client:
        return {"client": None, "schedules": []}
    
    project_query = {"client_id": ObjectId(id)}
    schedule_query_base = {}
    
    if current_user.role != "super_admin":
        if not current_user.company_id:
            return {"client": client.model_dump(by_alias=True), "schedules": []}
        company_id_obj = ObjectId(current_user.company_id)
        project_query["company_id"] = company_id_obj
        schedule_query_base["company_id"] = company_id_obj
    
    schedule_list = []
    async for project in projects.find(project_query):
        schedule_query = {"project_id": ObjectId(project["_id"]), **schedule_query_base}
        async for schedule in schedules.find(schedule_query):
            schedule_list.append(schedule)
    
    return {
        "client": client.model_dump(by_alias=True),
        "schedules": schedule_list
    }

async def get_client_stats(id: str, current_user: UserModel) -> Dict[str, Any]:
    """Get statistics for a specific client including volume metrics and trip summaries"""
    client_schedule_list = await get_client_schedules(id, current_user)
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
                tm = await get_tm_identifier(trip_tm, current_user)
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

async def get_tm_identifier(tm_id: str, current_user: UserModel) -> str:
    """Helper function to get the TM identifier (registration number) from its ID"""
    from app.db.mongodb import transit_mixers
    from app.services.tm_service import get_tm
    
    # Try to get the TM identifier from the database
    tm = await get_tm(tm_id, current_user)
    if tm:
        return tm.identifier
    return tm_id 