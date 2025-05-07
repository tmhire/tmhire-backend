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

async def create_schedule_and_generate_table(schedule: ScheduleCreate, user_id: str) -> ScheduleModel:
    schedule_data = schedule.model_dump()
    schedule_data["user_id"] = ObjectId(user_id)
    schedule_data["created_at"] = datetime.utcnow()
    schedule_data["last_updated"] = datetime.utcnow()
    schedule_data["output_table"] = []

    # Calculate pumping time
    quantity = schedule_data["input_params"]["quantity"]
    pumping_speed = schedule_data["input_params"]["pumping_speed"]
    schedule_data["pumping_time"] = quantity / pumping_speed

    # Insert the schedule into the database
    result = await schedules.insert_one(schedule_data)
    new_schedule = await schedules.find_one({"_id": result.inserted_id})

    # Now, generate the output table based on this new schedule
    avg_capacity = await get_average_capacity(user_id)
    if avg_capacity == 0:
        raise ValueError("Cannot generate schedule table, average capacity is 0.")

    import math
    tm_count = math.ceil(schedule_data["input_params"]["quantity"] / avg_capacity)

    # Update the schedule with the Transit Mixer count
    await schedules.update_one(
        {"_id": ObjectId(result.inserted_id)},
        {"$set": {"tm_count": tm_count}}
    )

    # Unloading time and base time setup
    unloading_time_min = get_unloading_time(avg_capacity)
    base_time = datetime.strptime(schedule_data["input_params"]["start_time"], "%H:%M")

    trips = []
    tm_identifiers = [chr(65 + i) for i in range(tm_count)]

    total_quantity = schedule_data["input_params"]["quantity"]
    remaining_quantity = total_quantity
    trip_no = 1

    # Generate the trips and schedule table
    while remaining_quantity > 0:
        for tm_idx, tm_id in enumerate(tm_identifiers):
            if remaining_quantity <= 0:
                break

            # Calculate start times for plant, pump, unloading, and return
            if trip_no == 1 and tm_idx == 0:
                plant_start = base_time
                pump_start = base_time + timedelta(minutes=schedule_data["input_params"]["onward_time"])
            else:
                prev_trip = next((t for t in reversed(trips) if t.tm_no == tm_id), None)
                if prev_trip:
                    prev_return = datetime.strptime(prev_trip.return_, "%H:%M")
                    plant_start = prev_return + timedelta(minutes=schedule_data["input_params"]["buffer_time"])
                else:
                    plant_start = base_time
                pump_start = plant_start + timedelta(minutes=schedule_data["input_params"]["onward_time"])

            # Calculate unloading and return times
            unloading_end = pump_start + timedelta(minutes=unloading_time_min)
            return_time = unloading_end + timedelta(minutes=schedule_data["input_params"]["return_time"])

            # Create a trip object
            trip = Trip(
                trip_no=trip_no,
                tm_no=tm_id,
                plant_start=plant_start.strftime("%H:%M"),
                pump_start=pump_start.strftime("%H:%M"),
                unloading_time=unloading_end.strftime("%H:%M"),
                return_=return_time.strftime("%H:%M")
            )

            trips.append(trip)
            trip_no += 1
            remaining_quantity -= avg_capacity

    # After generating the table, update the schedule document
    await schedules.update_one(
        {"_id": ObjectId(result.inserted_id)},
        {"$set": {
            "output_table": [trip.model_dump(by_alias=True) for trip in trips],
            "status": "generated",
            "last_updated": datetime.utcnow()
        }}
    )

    # Return the schedule with the generated table
    return ScheduleModel(**await schedules.find_one({"_id": result.inserted_id}))


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
    """Generate the schedule based on selected Transit Mixers."""
    schedule = await schedules.find_one({"_id": ObjectId(schedule_id), "user_id": ObjectId(user_id)})
    if not schedule:
        raise ValueError("Schedule not found.")

    avg_capacity = await get_average_capacity(user_id)
    if avg_capacity == 0:
        raise ValueError("Cannot generate schedule, average capacity is 0.")

    unloading_time_min = get_unloading_time(avg_capacity)
    base_time = datetime.strptime("08:00", "%H:%M")

    trips = []
    total_quantity = schedule["input_params"]["quantity"]
    remaining_quantity = total_quantity
    trip_no = 1

    # Generate trips based on selected TMs
    while remaining_quantity > 0:
        for tm_idx in selected_tms:
            if remaining_quantity <= 0:
                break

            # Calculate start times for plant, pump, unloading, and return
            if trip_no == 1 and tm_idx == selected_tms[0]:
                plant_start = base_time
                pump_start = base_time + timedelta(minutes=schedule["input_params"]["onward_time"])
            else:
                prev_trip = next((t for t in reversed(trips) if t.tm_no == tm_idx), None)
                if prev_trip:
                    prev_return = datetime.strptime(prev_trip.return_, "%H:%M")
                    plant_start = prev_return + timedelta(minutes=schedule["input_params"]["buffer_time"])
                else:
                    plant_start = base_time
                pump_start = plant_start + timedelta(minutes=schedule["input_params"]["onward_time"])

            # Calculate unloading and return times
            unloading_end = pump_start + timedelta(minutes=unloading_time_min)
            return_time = unloading_end + timedelta(minutes=schedule["input_params"]["return_time"])

            # Create a trip object
            trip = Trip(
                trip_no=trip_no,
                tm_no=tm_idx,
                plant_start=plant_start.strftime("%H:%M"),
                pump_start=pump_start.strftime("%H:%M"),
                unloading_time=unloading_end.strftime("%H:%M"),
                return_=return_time.strftime("%H:%M")
            )

            trips.append(trip)
            trip_no += 1
            remaining_quantity -= avg_capacity

    # Update the schedule with the generated table
    await schedules.update_one(
        {"_id": ObjectId(schedule_id)},
        {"$set": {
            "output_table": [trip.model_dump(by_alias=True) for trip in trips],
            "status": "generated",
            "last_updated": datetime.utcnow()
        }}
    )

    return ScheduleModel(**await schedules.find_one({"_id": ObjectId(schedule_id)}))

