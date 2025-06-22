from app.db.mongodb import pumps, PyObjectId, schedules
from app.models.pump import PumpModel, PumpCreate, PumpUpdate
from bson import ObjectId
from typing import List, Optional
from datetime import datetime, time
from app.models.schedule_calendar import GanttTask, GanttMixer

async def get_all_pumps(user_id: str) -> List[PumpModel]:
    """Get all pumps for a user"""
    result = []
    async for pump in pumps.find({"user_id": ObjectId(user_id)}):
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
    pump_data["user_id"] = ObjectId(user_id)
    if "plant_id" in pump_data and pump_data["plant_id"]:
        pump_data["plant_id"] = ObjectId(pump_data["plant_id"])
    pump_data["created_at"] = datetime.utcnow()
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

async def get_pump_gantt_data(query_date: datetime.date, user_id: str) -> List[GanttMixer]:
    """Get Gantt chart data for all pumps for a given date."""
    # Get all pumps for the user
    pump_map = {}
    async for pump in pumps.find({"user_id": ObjectId(user_id)}):
        pump_id = str(pump["_id"])
        plant_id = str(pump.get("plant_id", ""))
        pump_map[pump_id] = GanttMixer(
            id=pump_id,
            name=pump.get("identifier", "Unknown"),
            plant=plant_id,
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

        # Find the earliest pump_start and latest return in output_table
        trips = schedule.get("output_table", [])
        if not trips:
            continue
        pump_starts = []
        returns = []
        for trip in trips:
            ps = trip.get("pump_start")
            if ps:
                if isinstance(ps, str):
                    try:
                        ps = datetime.fromisoformat(ps)
                    except Exception:
                        continue
                pump_starts.append(ps)
            rt = trip.get("return")
            if rt:
                if isinstance(rt, str):
                    try:
                        rt = datetime.fromisoformat(rt)
                    except Exception:
                        continue
                returns.append(rt)
        if not pump_starts or not returns:
            continue
        start_time = min(pump_starts)
        end_time = max(returns)
        task = GanttTask(
            id=f"task-{schedule_id}-{pump_id}",
            start=start_time.strftime("%H:%M"),
            end=end_time.strftime("%H:%M"),
            client=client_name
        )
        pump_map[pump_id].tasks.append(task)

    return list(pump_map.values())

