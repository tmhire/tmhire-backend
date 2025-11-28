from app.models.project import ProjectModel, ProjectCreate, ProjectUpdate
from app.models.user import UserModel
from app.db.mongodb import projects, schedules
from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime
from app.services.client_service import get_client
from app.services.plant_service import get_plant
from app.services.team_service import get_team_member
from pymongo import DESCENDING
from fastapi import HTTPException

async def get_all_projects(current_user: UserModel) -> List[ProjectModel]:
    """Get all projects for the current user's company"""
    query = {}
    
    # Super admin can see all projects
    if current_user.role != "super_admin":
        if not current_user.company_id:
            return []
        query["company_id"] = ObjectId(current_user.company_id)
    
    project_list = []
    async for project in projects.find(query).sort("created_at", DESCENDING):
        project_list.append(ProjectModel(**project))
    return project_list

async def get_project(id: str, current_user: UserModel) -> Optional[ProjectModel]:
    """Get a specific project by ID"""
    if id is None:
        return None
    
    query = {"_id": ObjectId(id)}
    # Super admin can see all projects
    if current_user.role != "super_admin":
        if not current_user.company_id:
            return None
        query["company_id"] = ObjectId(current_user.company_id)
    
    project = await projects.find_one(query)
    if project:
        return ProjectModel(**project)
    return None

async def create_project(project: ProjectCreate, current_user: UserModel) -> ProjectModel:
    """Create a new project"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    project_data = project.model_dump()
    project_data["company_id"] = ObjectId(current_user.company_id)
    project_data["created_by"] = ObjectId(current_user.id)
    project_data["user_id"] = ObjectId(current_user.id)  # Keep for compatibility
    
    # Validate client exists
    client = await get_client(str(project.client_id), current_user)
    if client is None:
        raise ValueError("Client ID does not exist")
    
    # Validate mother plant exists
    mother_plant = await get_plant(str(project.mother_plant_id), current_user)
    if mother_plant is None:
        raise ValueError("Mother Plant ID does not exist")

    # Validate sales engineer exists
    if project.sales_engineer_id:
        sales_engineer = await get_team_member(str(project.sales_engineer_id), current_user)
        if sales_engineer is None:
            raise ValueError("Sales Engineer ID does not exist")
    
    project_data["created_at"] = datetime.utcnow()
    project_data["last_updated"] = datetime.utcnow()
    
    result = await projects.insert_one(project_data)
    
    new_project = await projects.find_one({"_id": result.inserted_id})
    return ProjectModel(**new_project)

async def update_project(id: str, project: ProjectUpdate, current_user: UserModel) -> Optional[ProjectModel]:
    """Update a project"""
    project_data = {k: v for k, v in project.model_dump().items() if v is not None}
    
    if not project_data:
        return await get_project(id, current_user)
    
    # Validate client exists if being updated
    if "client_id" in project_data:
        client = await get_client(str(project_data["client_id"]), current_user)
        if client is None:
            raise ValueError("Client ID does not exist")
    
    # Validate mother plant exists if being updated
    if "mother_plant_id" in project_data:
        mother_plant = await get_plant(str(project_data["mother_plant_id"]), current_user)
        if mother_plant is None:
            raise ValueError("Mother Plant ID does not exist")
    
    # Validate sales engineer exists if being updated
    if project.sales_engineer_id:
        sales_engineer = await get_team_member(str(project.sales_engineer_id), current_user)
        if sales_engineer is None:
            raise ValueError("Sales Engineer ID does not exist")
    
    project_data["last_updated"] = datetime.utcnow()
    
    query = {"_id": ObjectId(id)}
    # Super admin can update any project
    if current_user.role != "super_admin":
        if not current_user.company_id:
            raise HTTPException(status_code=403, detail="User must belong to a company")
        query["company_id"] = ObjectId(current_user.company_id)
    
    await projects.update_one(query, {"$set": project_data})
    
    return await get_project(id, current_user)

async def delete_project(id: str, current_user: UserModel) -> Dict[str, bool]:
    """Delete a project and check for dependencies"""
    # Verify project exists and user has access
    project = await get_project(id, current_user)
    if not project:
        return {
            "success": False,
            "message": "Project not found"
        }
    
    # Check if this project has any associated schedules
    schedule_query = {"project_id": ObjectId(id)}
    if current_user.role != "super_admin":
        schedule_query["company_id"] = ObjectId(current_user.company_id)
    
    has_schedules = await schedules.find_one(schedule_query)
    
    if has_schedules:
        return {
            "success": False,
            "message": "Cannot delete project with associated schedules"
        }
    
    # Delete the project if no dependencies
    query = {"_id": ObjectId(id)}
    if current_user.role != "super_admin":
        query["company_id"] = ObjectId(current_user.company_id)
    
    result = await projects.delete_one(query)
    
    return {
        "success": result.deleted_count > 0,
        "message": "Project deleted successfully" if result.deleted_count > 0 else "Project not found"
    }

async def get_all_projects_for_client(current_user: UserModel, client_id: str) -> List[ProjectModel]:
    "Get all projects for the current user's company's client"
    query = {"client_id": ObjectId(client_id)}
    
    if current_user.role != "super_admin":
        if not current_user.company_id:
            return []
        query["company_id"] = ObjectId(current_user.company_id)
    
    project_list = []
    async for project in projects.find(query):
        project_list.append(ProjectModel(**project))
    return project_list

async def get_all_projects_for_mother_plant(current_user: UserModel, mother_plant_id: str) -> List[ProjectModel]:
    "Get all projects for the current user's company's mother plant"
    query = {"mother_plant_id": ObjectId(mother_plant_id)}
    
    if current_user.role != "super_admin":
        if not current_user.company_id:
            return []
        query["company_id"] = ObjectId(current_user.company_id)
    
    project_list = []
    async for project in projects.find(query):
        project_list.append(ProjectModel(**project))
    return project_list

async def get_project_schedules(id: str, current_user: UserModel) -> Dict:
    """Get all schedules for a specific project"""
    project = await get_project(id, current_user)
    if not project:
        return {"project": None, "schedules": []}
    
    schedule_query = {"project_id": ObjectId(id)}
    if current_user.role != "super_admin":
        if not current_user.company_id:
            return {"project": project.model_dump(by_alias=True), "schedules": []}
        schedule_query["company_id"] = ObjectId(current_user.company_id)
    
    schedule_list = []
    async for schedule in schedules.find(schedule_query):
        schedule_list.append(schedule)
    
    return {
        "project": project.model_dump(by_alias=True),
        "schedules": schedule_list
    }

async def get_client_from_project(project_id: str, current_user: UserModel) -> Optional[Dict[str, Any]]:
    """Get client information from a project"""
    project = await get_project(project_id, current_user)
    if not project:
        return {
            "client": None,
            "project": None
        }
    
    client = await get_client(str(project.client_id), current_user)
    if client:
        return {
            "client": client,
            "project": project
        }
    
    return {
            "client": None,
            "project": None
        }


async def get_project_stats(id: str, current_user: UserModel) -> Dict[str, Any]:
    """Get statistics for a specific project including volume metrics and trip summaries"""
    project_schedule_list = await get_project_schedules(id, current_user)
    project = project_schedule_list["project"]
    all_schedules = project_schedule_list["schedules"]
    if not project:
        return {}
    
    # Get mother plant information
    mother_plant_name = "Not Assigned"
    if project.get("mother_plant_id"):
        mother_plant = await get_plant(str(project["mother_plant_id"]), current_user)
        mother_plant_name = mother_plant.name if mother_plant else "Unknown Plant"
    
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
        "client_id": client_name,
        "mother_plant": mother_plant_name,
        "total_scheduled": f"{total_scheduled} m³",
        "total_delivered": f"{total_delivered} m³",
        "pending_volume": f"{pending_volume} m³",
        "trips": trips
    }

async def get_tm_identifier(tm_id: str, current_user: UserModel) -> str:
    """Helper function to get the TM identifier (registration number) from its ID"""
    from app.services.tm_service import get_tm
    
    # Try to get the TM identifier from the database
    tm = await get_tm(tm_id, current_user)
    if tm:
        return tm.identifier
    return tm_id

async def migrate_projects_with_mother_plant(current_user: UserModel, mother_plant_id: str) -> Dict[str, Any]:
    """Migrate existing projects to assign a mother plant"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    query = {
        "company_id": ObjectId(current_user.company_id),
        "mother_plant_id": {"$exists": False}
    }
    
    # Find all projects without mother_plant_id
    result = await projects.update_many(
        query,
        {
            "$set": {
                "mother_plant_id": ObjectId(mother_plant_id),
                "last_updated": datetime.utcnow()
            }
        }
    )
    
    return {
        "success": True,
        "message": f"Updated {result.modified_count} projects with mother plant",
        "modified_count": result.modified_count
    }

async def get_projects_without_mother_plant(current_user: UserModel) -> List[ProjectModel]:
    """Get all projects that don't have a mother plant assigned"""
    query = {
        "$or": [
            {"mother_plant_id": {"$exists": False}},
            {"mother_plant_id": None}
        ]
    }
    
    if current_user.role != "super_admin":
        if not current_user.company_id:
            return []
        query["company_id"] = ObjectId(current_user.company_id)
    
    project_list = []
    async for project in projects.find(query):
        project_list.append(ProjectModel(**project))
    return project_list 