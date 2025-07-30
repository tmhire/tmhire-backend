from app.models.project import ProjectModel, ProjectCreate, ProjectUpdate
from app.db.mongodb import projects, schedules
from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime
from app.services.client_service import get_client

async def get_all_projects(user_id: str) -> List[ProjectModel]:
    """Get all projects for a user"""
    project_list = []
    async for project in projects.find({"user_id": ObjectId(user_id)}):
        project_list.append(ProjectModel(**project))
    return project_list

async def get_project(id: str, user_id: str) -> Optional[ProjectModel]:
    """Get a specific project by ID"""
    if id is None:
        return None
    project = await projects.find_one({"_id": ObjectId(id), "user_id": ObjectId(user_id)})
    if project:
        return ProjectModel(**project)
    return None

async def create_project(project: ProjectCreate, user_id: str) -> ProjectModel:
    """Create a new project"""
    project_data = project.model_dump()
    project_data["user_id"] = ObjectId(user_id)
    client = await get_client(str(project.client_id), user_id)
    if client is None:
        raise ValueError("Client ID does not exist")
    project_data["created_at"] = datetime.utcnow()
    project_data["last_updated"] = datetime.utcnow()
    
    result = await projects.insert_one(project_data)
    
    new_project = await projects.find_one({"_id": result.inserted_id})
    return ProjectModel(**new_project)

async def update_project(id: str, project: ProjectUpdate, user_id: str) -> Optional[ProjectModel]:
    """Update a project"""
    project_data = {k: v for k, v in project.model_dump().items() if v is not None}
    
    if not project_data:
        return await get_project(id, user_id)
    
    project_data["last_updated"] = datetime.utcnow()
    
    await projects.update_one(
        {"_id": ObjectId(id), "user_id": ObjectId(user_id)},
        {"$set": project_data}
    )
    
    return await get_project(id, user_id)

async def delete_project(id: str, user_id: str) -> Dict[str, bool]:
    """Delete a project and check for dependencies"""
    # Check if this project has any associated schedules
    has_schedules = await schedules.find_one({
        "user_id": ObjectId(user_id),
        "project_id": ObjectId(id)
    })
    
    if has_schedules:
        return {
            "success": False,
            "message": "Cannot delete project with associated schedules"
        }
    
    # Delete the project if no dependencies
    result = await projects.delete_one({
        "_id": ObjectId(id),
        "user_id": ObjectId(user_id)
    })
    
    return {
        "success": result.deleted_count > 0,
        "message": "Project deleted successfully" if result.deleted_count > 0 else "Project not found"
    }

async def get_all_projects_for_client(user_id: str, client_id: str) -> List[ProjectModel]:
    "Get all projects for a user's client"
    project_list = []
    async for project in projects.find({"client_id": ObjectId(client_id), "user_id": ObjectId(user_id)}):
        project_list.append(ProjectModel(**project))
    return project_list

async def get_project_schedules(id: str, user_id: str) -> Dict:
    """Get all schedules for a specific project"""
    project = await get_project(id, user_id)
    if not project:
        return {"project": None, "schedules": []}
    
    schedule_list = []
    async for schedule in schedules.find({"project_id": ObjectId(id), "user_id": ObjectId(user_id)}):
        schedule_list.append(schedule)
    
    return {
        "project": project.model_dump(by_alias=True),
        "schedules": schedule_list
    }

async def get_client_from_project(project_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Get client information from a project"""
    project = await get_project(project_id, user_id)
    if not project:
        return {
            "client": None,
            "project": None
        }
    
    client = await get_client(str(project.client_id), user_id)
    if client:
        return {
            "client": client,
            "project": project
        }
    
    return {
            "client": None,
            "project": None
        }


async def get_project_stats(id: str, user_id: str) -> Dict[str, Any]:
    """Get statistics for a specific project including volume metrics and trip summaries"""
    project_schedule_list = await get_project_schedules(id, user_id)
    project = project_schedule_list["project"]
    all_schedules = project_schedule_list["schedules"]
    if not project:
        return {}
    
    # Initialize stats
    total_scheduled = 0
    total_delivered = 0
    pending_volume = 0
    trips = []
    
    # Query for all schedules for this project
    async for schedule in all_schedules:
        # Sum up scheduled volume from input parameters
        client_name = schedule.get("client_name", "")
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
        "client_id": client_name,
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