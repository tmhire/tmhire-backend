from app.db.mongodb import schedules, PyObjectId
from app.models.schedule import ScheduleModel, ScheduleCreate, ScheduleUpdate, Trip
from app.services.tm_service import get_average_capacity
from datetime import datetime, timedelta
from bson import ObjectId
from typing import List, Optional, Dict

# Unloading time lookup table
UNLOADING_TIME_LOOKUP = {
    6: 10,
    7: 12,
    8: 14,
    9: 16,
    10: 18
}

async def get_all_schedules(user_id: str) -> List[ScheduleModel]:
    schedule_list = []
    async for schedule in schedules.find({"user_id": ObjectId(user_id)}):
        schedule_list.append(ScheduleModel(**schedule))
    return schedule_list

async def get_schedule(id: str, user_id: str) -> Optional[ScheduleModel]:
    schedule = await schedules.find_one({"_id": ObjectId(id), "user_id": ObjectId(user_id)})
    if schedule:
        return ScheduleModel(**schedule)
    return None

async def update_schedule(id: str, schedule: ScheduleUpdate, user_id: str) -> Optional[ScheduleModel]:
    schedule_data = {k: v for k, v in schedule.model_dump().items() if v is not None}

    if not schedule_data:
        return await get_schedule(id, user_id)

    schedule_data["last_updated"] = datetime.utcnow()

    if "input_params" in schedule_data:
        quantity = schedule_data["input_params"]["quantity"]
        pumping_speed = schedule_data["input_params"]["pumping_speed"]
        schedule_data["pumping_time"] = quantity / pumping_speed
        schedule_data["status"] = "draft"
        schedule_data["output_table"] = []

    await schedules.update_one(
        {"_id": ObjectId(id), "user_id": ObjectId(user_id)},
        {"$set": schedule_data}
    )

    return await get_schedule(id, user_id)

async def delete_schedule(id: str, user_id: str) -> Dict[str, str | bool]:
    result = await schedules.delete_one({
        "_id": ObjectId(id),
        "user_id": ObjectId(user_id)
    })

    return {
        "deleted": result.deleted_count > 0,
        "schedule_id": id
    }

def get_unloading_time(capacity: float) -> int:
    rounded_capacity = round(capacity)
    if rounded_capacity < 6:
        rounded_capacity = 6
    elif rounded_capacity > 10:
        rounded_capacity = 10
    return UNLOADING_TIME_LOOKUP[rounded_capacity]

async def calculate_tm_count(schedule: ScheduleCreate, user_id: str) -> Dict:
    """Calculate the required Transit Mixer count and create a draft schedule."""
    avg_capacity = await get_average_capacity(user_id)
    if avg_capacity == 0:
        raise ValueError("Cannot calculate TM count, average capacity is 0. Add TMs first.")

    import math
    tm_count = math.ceil(schedule.input_params.quantity / avg_capacity)
    tm_identifiers = [chr(65 + i) for i in range(tm_count)]  # Generate TM identifiers (A, B, C, ...)

    # Create a draft schedule in the database
    schedule_data = schedule.model_dump()
    schedule_data["user_id"] = ObjectId(user_id)
    schedule_data["created_at"] = datetime.utcnow()
    schedule_data["last_updated"] = datetime.utcnow()
    schedule_data["status"] = "draft"
    schedule_data["tm_count"] = tm_count
    schedule_data["output_table"] = []

    # Ensure input_params is included in the draft schedule
    schedule_data["input_params"] = schedule.input_params.dict()

    result = await schedules.insert_one(schedule_data)
    
    return {
        "schedule_id": str(result.inserted_id),
        "tm_count": tm_count,
        "tm_identifiers": tm_identifiers
    }

async def generate_schedule(schedule_id: str, selected_tms: List[str], user_id: str) -> ScheduleModel:
    """Generate the schedule based on selected Transit Mixers with single pump constraint."""
    schedule = await schedules.find_one({"_id": ObjectId(schedule_id), "user_id": ObjectId(user_id)})
    if not schedule:
        raise ValueError("Schedule not found.")

    avg_capacity = await get_average_capacity(user_id)
    if avg_capacity == 0:
        raise ValueError("Cannot generate schedule, average capacity is 0.")

    unloading_time_min = get_unloading_time(avg_capacity)
    base_time = datetime.strptime(schedule["input_params"].get("pump_start", "08:00"), "%H:%M")

    onward_time = schedule["input_params"]["onward_time"]
    return_time = schedule["input_params"]["return_time"]
    buffer_time = schedule["input_params"]["buffer_time"]

    trips = []
    total_quantity = schedule["input_params"]["quantity"]
    remaining_quantity = total_quantity
    trip_no = 1
    tm_counters = {tm: 0 for tm in selected_tms}  # count trips per TM
    pump_available_time = base_time  # pump is free at this time

    while remaining_quantity > 0:
        for tm_no in selected_tms:
            if remaining_quantity <= 0:
                break

            # The next unloading start must be after pump is free + buffer
            unloading_start = pump_available_time
            plant_start = unloading_start - timedelta(minutes=onward_time + unloading_time_min)

            # Make sure plant start is not earlier than base time (you can skip this if unnecessary)
            if plant_start < base_time:
                plant_start = base_time
                unloading_start = plant_start + timedelta(minutes=onward_time)

            pump_start = unloading_start
            unloading_end = pump_start + timedelta(minutes=unloading_time_min)
            return_at = unloading_end + timedelta(minutes=return_time)

            trip = Trip(
                trip_no=trip_no,
                tm_no=tm_no,
                plant_start=plant_start.strftime("%H:%M"),
                pump_start=pump_start.strftime("%H:%M"),
                unloading_time=unloading_end.strftime("%H:%M"),
                return_=return_at.strftime("%H:%M")
            )

            trips.append(trip)
            remaining_quantity -= avg_capacity
            trip_no += 1
            tm_counters[tm_no] += 1

            # Update pump availability
            pump_available_time = unloading_end + timedelta(minutes=buffer_time)

    # Update schedule
    await schedules.update_one(
        {"_id": ObjectId(schedule_id)},
        {"$set": {
            "output_table": [trip.model_dump(by_alias=True) for trip in trips],
            "status": "generated",
            "last_updated": datetime.utcnow()
        }}
    )

    return ScheduleModel(**await schedules.find_one({"_id": ObjectId(schedule_id)}))

