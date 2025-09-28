import asyncio
from app.db.mongodb import pumps, schedules
from app.models.pump import PumpModel, PumpCreate, PumpUpdate
from bson import ObjectId
from typing import List, Optional
from datetime import datetime, time, timedelta
from app.models.schedule_calendar import GanttPump, GanttTask
from app.services.plant_service import get_plant
from app.services.team_service import get_team_member
from pymongo import DESCENDING

async def get_all_pumps(user_id: str) -> List[PumpModel]:
    """Get all pumps for a user"""
    result = []
    async for pump in pumps.find({"user_id": ObjectId(user_id)}).sort("created_at", DESCENDING):
        # Convert empty string or None plant_id to None
        if "plant_id" in pump and (not pump["plant_id"] or pump["plant_id"] == ""):
            pump["plant_id"] = None
        result.append(PumpModel(**pump))
    return result

async def get_pump(id: str, user_id: str) -> Optional[PumpModel]:
    """Get a specific pump by ID"""
    pump = await pumps.find_one({"_id": ObjectId(id), "user_id": ObjectId(user_id)})
    if pump:
        return PumpModel(**pump)
    return None

async def create_pump(pump: PumpCreate, user_id: str) -> PumpModel:
    """Create a new pump"""
    pump_data = pump.model_dump()
    if "identifier" not in pump_data or not pump_data["identifier"]:
        raise ValueError("Pump identifier is required")
    pump_data["user_id"] = ObjectId(user_id)
    if "plant_id" in pump_data and pump_data["plant_id"]:
        pump_data["plant_id"] = ObjectId(pump_data["plant_id"])

    
    # Validate pump operator exists
    pump_operator, pipeline_gang = await asyncio.gather(
        get_team_member(str(pump_data["pump_operator_id"]), user_id), 
        get_team_member(str(pump_data["pipeline_gang_id"]), user_id)
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

async def update_pump(id: str, pump: PumpUpdate, user_id: str) -> Optional[PumpModel]:
    """Update a pump"""
    pump_data = {k: v for k, v in pump.model_dump().items() if v is not None}
    if "plant_id" in pump_data and pump_data["plant_id"]:
        pump_data["plant_id"] = ObjectId(pump_data["plant_id"])
    if not pump_data:
        return await get_pump(id, user_id)

    # Validate pump operator exists
    pump_operator, pipeline_gang = await asyncio.gather(
        get_team_member(str(pump_data["pump_operator_id"]), user_id), 
        get_team_member(str(pump_data["pipeline_gang_id"]), user_id)
    )
    if pump_operator is None:
        raise ValueError("Pump Operator ID does not exist")
    if pipeline_gang is None:
        raise ValueError("Pipeline Gang ID does not exist")

    await pumps.update_one(
        {"_id": ObjectId(id), "user_id": ObjectId(user_id)},
        {"$set": pump_data}
    )
    return await get_pump(id, user_id)

async def delete_pump(id: str, user_id: str) -> bool:
    """Delete a pump"""
    result = await pumps.delete_one({"_id": ObjectId(id), "user_id": ObjectId(user_id)})
    return result.deleted_count > 0

async def get_pumps_by_plant(plant_id: str, user_id: str) -> List[PumpModel]:
    """Get all pumps for a specific plant"""
    result = []
    async for pump in pumps.find({"plant_id": ObjectId(plant_id), "user_id": ObjectId(user_id)}):
        result.append(PumpModel(**pump))
    return result

def get_date_from_iso(iso_str):
            if isinstance(iso_str, str):
                    try:
                        return datetime.fromisoformat(iso_str)
                    except Exception:
                        return None

async def get_pump_gantt_data(query_date: datetime.date, user_id: str) -> List[GanttPump]:
    """Get Gantt chart data for all pumps for a given date."""
    # Get all pumps for the user
    pump_map = {}
    for pump in await pumps.find({"user_id": ObjectId(user_id)}).to_list(length=None):
        pump_id = str(pump["_id"])
        plant_id = str(pump.get("plant_id", ""))
        pump_type = pump.get("type")
        plant_name = None
        if plant_id:
            plant = await get_plant(plant_id, user_id)
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

    # Find all schedules for this user and date
    async for schedule in schedules.find({
        "user_id": ObjectId(user_id),
        "status": "generated",
        "input_params.schedule_date": query_date.isoformat()
    }):
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

