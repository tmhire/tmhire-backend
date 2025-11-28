import asyncio
from app.db.mongodb import pumps, schedules
from app.models.pump import PumpModel, PumpCreate, PumpUpdate
from app.models.user import UserModel
from bson import ObjectId
from typing import List, Optional
from datetime import datetime, time, timedelta
from app.models.schedule_calendar import GanttPump, GanttTask
from app.services.plant_service import get_plant
from app.services.team_service import get_team_member
from pymongo import DESCENDING
from fastapi import HTTPException

async def get_all_pumps(current_user: UserModel) -> List[PumpModel]:
    """Get all pumps for the current user's company"""
    query = {}
    
    # Super admin can see all pumps
    if current_user.role != "super_admin":
        if not current_user.company_id:
            return []
        query["company_id"] = ObjectId(current_user.company_id)
    
    result = []
    async for pump in pumps.find(query).sort("created_at", DESCENDING):
        # Convert empty string or None plant_id to None
        if "plant_id" in pump and (not pump["plant_id"] or pump["plant_id"] == ""):
            pump["plant_id"] = None
        result.append(PumpModel(**pump))
    return result

async def get_pump(id: str, current_user: UserModel) -> Optional[PumpModel]:
    """Get a specific pump by ID"""
    query = {"_id": ObjectId(id)}
    
    # Super admin can see all pumps
    if current_user.role != "super_admin":
        if not current_user.company_id:
            return None
        query["company_id"] = ObjectId(current_user.company_id)
    
    pump = await pumps.find_one(query)
    if pump:
        return PumpModel(**pump)
    return None

async def create_pump(pump: PumpCreate, current_user: UserModel) -> PumpModel:
    """Create a new pump"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    pump_data = pump.model_dump()
    if "identifier" not in pump_data or not pump_data["identifier"]:
        raise ValueError("Pump identifier is required")
    pump_data["company_id"] = ObjectId(current_user.company_id)
    pump_data["created_by"] = ObjectId(current_user.id)
    pump_data["user_id"] = ObjectId(current_user.id)  # Keep for compatibility
    if "plant_id" in pump_data and pump_data["plant_id"]:
        pump_data["plant_id"] = ObjectId(pump_data["plant_id"])

    
    # Validate pump operator exists
    pump_operator, pipeline_gang = await asyncio.gather(
        get_team_member(str(pump_data["pump_operator_id"]), current_user), 
        get_team_member(str(pump_data["pipeline_gang_id"]), current_user)
    )
    if pump_operator is None:
        raise ValueError("Pump Operator ID does not exist")
    if pipeline_gang is None:
        raise ValueError("Pipeline Gang ID does not exist")

    pump_data["created_at"] = datetime.utcnow()
    pump_data["last_updated"] = datetime.utcnow()
    result = await pumps.insert_one(pump_data)
    new_pump = await pumps.find_one({"_id": result.inserted_id})
    return PumpModel(**new_pump)

async def update_pump(id: str, pump: PumpUpdate, current_user: UserModel) -> Optional[PumpModel]:
    """Update a pump"""
    pump_data = {k: v for k, v in pump.model_dump().items() if v is not None}
    if "plant_id" in pump_data and pump_data["plant_id"]:
        pump_data["plant_id"] = ObjectId(pump_data["plant_id"])
    if not pump_data:
        return await get_pump(id, current_user)

    # Validate pump operator exists if provided
    if "pump_operator_id" in pump_data or "pipeline_gang_id" in pump_data:
        pump_operator, pipeline_gang = await asyncio.gather(
            get_team_member(str(pump_data.get("pump_operator_id")), current_user) if pump_data.get("pump_operator_id") else None,
            get_team_member(str(pump_data.get("pipeline_gang_id")), current_user) if pump_data.get("pipeline_gang_id") else None
        )
        if pump_data.get("pump_operator_id") and pump_operator is None:
            raise ValueError("Pump Operator ID does not exist")
        if pump_data.get("pipeline_gang_id") and pipeline_gang is None:
            raise ValueError("Pipeline Gang ID does not exist")

    query = {"_id": ObjectId(id)}
    # Super admin can update any pump
    if current_user.role != "super_admin":
        if not current_user.company_id:
            raise HTTPException(status_code=403, detail="User must belong to a company")
        query["company_id"] = ObjectId(current_user.company_id)

    await pumps.update_one(query, {"$set": pump_data})
    return await get_pump(id, current_user)

async def delete_pump(id: str, current_user: UserModel) -> bool:
    """Delete a pump"""
    # Verify pump exists and user has access
    pump = await get_pump(id, current_user)
    if not pump:
        return False
    
    query = {"_id": ObjectId(id)}
    if current_user.role != "super_admin":
        query["company_id"] = ObjectId(current_user.company_id)
    
    result = await pumps.delete_one(query)
    return result.deleted_count > 0

async def get_pumps_by_plant(plant_id: str, current_user: UserModel) -> List[PumpModel]:
    """Get all pumps for a specific plant"""
    query = {"plant_id": ObjectId(plant_id)}
    
    # Filter by company_id if not super admin
    if current_user.role != "super_admin":
        if not current_user.company_id:
            return []
        query["company_id"] = ObjectId(current_user.company_id)
    
    result = []
    async for pump in pumps.find(query):
        result.append(PumpModel(**pump))
    return result

def get_date_from_iso(iso_str):
            if isinstance(iso_str, str):
                    try:
                        return datetime.fromisoformat(iso_str)
                    except Exception:
                        return None

async def get_pump_gantt_data(query_date: datetime.date, current_user: UserModel) -> List[GanttPump]:
    """Get Gantt chart data for all pumps for a given date."""
    # Get all pumps for the user's company
    query = {}
    if current_user.role != "super_admin":
        if not current_user.company_id:
            return []
        query["company_id"] = ObjectId(current_user.company_id)
    
    pump_map = {}
    for pump in await pumps.find(query).to_list(length=None):
        pump_id = str(pump["_id"])
        plant_id = str(pump.get("plant_id", ""))
        pump_type = pump.get("type")
        plant_name = None
        if plant_id:
            plant = await get_plant(plant_id, current_user)
            plant_name = plant.name if plant else "Unknown Plant"
        pump_map[pump_id] = GanttPump(
            id=pump_id,
            name=pump.get("identifier", "Unknown"),
            plant=plant_name,
            type = pump_type,
            tasks=[]
        )

    # Define the start and end of the day
    start_datetime = datetime.combine(query_date, time.min)
    end_datetime = datetime.combine(query_date, time.max)

    # Find all schedules for this company and date
    schedule_query = {
        "status": "generated",
        "input_params.schedule_date": query_date.isoformat()
    }
    if current_user.role != "super_admin":
        schedule_query["company_id"] = ObjectId(current_user.company_id)
    
    async for schedule in schedules.find(schedule_query):
        pump_id = str(schedule.get("pump"))
        client_name = schedule.get("client_name")
        schedule_id = str(schedule["_id"])
        if not pump_id or pump_id not in pump_map:
            continue

        # Check if this schedule uses burst model
        is_burst_model = schedule.get("input_params", {}).get("is_burst_model", False)
        
        # Choose the appropriate table based on is_burst_model
        trips = schedule.get("burst_table", []) if is_burst_model else schedule.get("output_table", [])
        if not trips:
            continue
        start_time = trips[0].get("pump_start")
        end_time = trips[-1].get("unloading_time")
        if not start_time or not end_time:
            continue
        start_time = get_date_from_iso(start_time)
        end_time = get_date_from_iso(end_time)
        if start_time == None or end_time == None:
            continue
        pump_onward_time = schedule.get("input_params", {}).get("pump_onward_time", 0)
        pump_fixing_time = schedule.get("input_params", {}).get("pump_fixing_time", 0)
        start_time = start_time - timedelta(minutes=pump_onward_time + pump_fixing_time)
        task = GanttTask(
            id=f"task-{schedule_id}-{pump_id}",
            start=start_time.strftime("%H:%M"),
            end=end_time.strftime("%H:%M"),
            client=client_name
        )
        pump_map[pump_id].tasks.append(task)
    print(f"Pump Gantt data for {query_date} retrieved: {pump_map}")
    return list(pump_map.values())

