from app.db.mongodb import schedules, PyObjectId, transit_mixers, clients
from app.models.schedule import ScheduleModel, ScheduleCreate, ScheduleUpdate, Trip
from app.services.tm_service import get_average_capacity, get_tm
from app.services.client_service import get_client
from app.services.schedule_calendar_service import update_calendar_after_schedule, get_tm_availability
from datetime import datetime, timedelta, date
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
        # Convert string time values to datetime objects if they are in old format
        current_date = datetime.now().date()
        
        for trip in schedule.get("output_table", []):
            # Fields that need conversion
            time_fields = ["plant_start", "pump_start", "unloading_time", "return"]
            
            for field in time_fields:
                # Skip if field doesn't exist
                if field not in trip:
                    continue
                
                # Skip if it's already a datetime
                if isinstance(trip[field], datetime):
                    continue
                
                # If it's a string in HH:MM format (legacy format)
                if isinstance(trip[field], str) and ":" in trip[field] and len(trip[field]) <= 5:
                    try:
                        time_obj = datetime.strptime(trip[field], "%H:%M").time()
                        trip[field] = datetime.combine(current_date, time_obj)
                    except ValueError:
                        # If can't parse, just leave as is and let Pydantic handle the error
                        pass
        
        schedule_list.append(ScheduleModel(**schedule))
    return schedule_list

async def get_schedule(id: str, user_id: str) -> Optional[ScheduleModel]:
    schedule = await schedules.find_one({"_id": ObjectId(id), "user_id": ObjectId(user_id)})
    if schedule:
        # Get the tm_identifiers map for any TMs in the output_table
        tm_ids = []
        for trip in schedule.get("output_table", []):
            tm_id = trip.get("tm_no")
            if tm_id and ObjectId.is_valid(tm_id):
                tm_ids.append(ObjectId(tm_id))
        
        # If we have TM IDs, look up their identifiers
        if tm_ids:
            tm_map = {}
            async for tm in transit_mixers.find({"_id": {"$in": tm_ids}}):
                tm_map[str(tm["_id"])] = tm["identifier"]
            
            # Replace the TM IDs with their identifiers in the output_table
            for trip in schedule.get("output_table", []):
                tm_id = trip.get("tm_no")
                if tm_id and tm_id in tm_map:
                    trip["tm_no"] = tm_map[tm_id]
        
        # Convert string time values to datetime objects if they are in old format
        current_date = datetime.now().date()
        for trip in schedule.get("output_table", []):
            # Fields that need conversion
            time_fields = ["plant_start", "pump_start", "unloading_time", "return"]
            
            for field in time_fields:
                # Skip if field doesn't exist
                if field not in trip:
                    continue
                
                # Skip if it's already a datetime
                if isinstance(trip[field], datetime):
                    continue
                
                # If it's a string in HH:MM format (legacy format)
                if isinstance(trip[field], str) and ":" in trip[field] and len(trip[field]) <= 5:
                    try:
                        time_obj = datetime.strptime(trip[field], "%H:%M").time()
                        trip[field] = datetime.combine(current_date, time_obj)
                    except ValueError:
                        # If can't parse, just leave as is and let Pydantic handle the error
                        pass
        
        return ScheduleModel(**schedule)
    return None

async def update_schedule(id: str, schedule: ScheduleUpdate, user_id: str) -> Optional[ScheduleModel]:
    schedule_data = {k: v for k, v in schedule.model_dump().items() if v is not None}

    if not schedule_data:
        return await get_schedule(id, user_id)

    # If client_id is updated, fetch the client information
    if "client_id" in schedule_data:
        client = await get_client(schedule_data["client_id"], user_id)
        if client:
            schedule_data["client_id"] = ObjectId(schedule_data["client_id"])
            # If client_name is not provided, use the client name from the client object
            if "client_name" not in schedule_data:
                schedule_data["client_name"] = client.name

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

    updated_schedule = await get_schedule(id, user_id)
    
    # Update calendar if schedule has changes
    if updated_schedule and updated_schedule.output_table:
        await update_calendar_after_schedule(updated_schedule)
        
    return updated_schedule

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

    # Get client information
    client_name = schedule.client_name
    if schedule.client_id:
        client = await get_client(schedule.client_id, user_id)
        if client:
            client_name = client.name

    # Create a draft schedule in the database
    schedule_data = schedule.model_dump()
    schedule_data["user_id"] = ObjectId(user_id)
    schedule_data["created_at"] = datetime.utcnow()
    schedule_data["last_updated"] = datetime.utcnow()
    schedule_data["status"] = "draft"
    schedule_data["tm_count"] = tm_count
    schedule_data["output_table"] = []
    
    # Convert client_id to ObjectId
    if "client_id" in schedule_data and schedule_data["client_id"]:
        schedule_data["client_id"] = ObjectId(schedule_data["client_id"])
    
    # If client_name not provided, use name from the client
    if not client_name and "client_id" in schedule_data and schedule_data["client_id"]:
        client = await get_client(str(schedule_data["client_id"]), user_id)
        if client:
            schedule_data["client_name"] = client.name
    elif client_name:
        schedule_data["client_name"] = client_name
    
    # Ensure input_params is included in the draft schedule and pump_start is a datetime
    input_params = schedule.input_params.model_dump()
    if isinstance(input_params.get("schedule_date"), date):
        input_params["schedule_date"] = input_params["schedule_date"].isoformat()

    schedule_data["input_params"] = input_params
    
    # Make sure pump_start is a datetime object if it exists in input_params
    if "pump_start" not in schedule_data["input_params"] or not isinstance(schedule_data["input_params"]["pump_start"], datetime):
        # Set default to today 8AM if not provided
        schedule_data["input_params"]["pump_start"] = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)

    result = await schedules.insert_one(schedule_data)
    
    return {
        "schedule_id": str(result.inserted_id),
        "tm_count": tm_count,
        "tm_identifiers": tm_identifiers
    }

async def check_tm_availability(schedule_date: date, selected_tms: List[str], user_id: str) -> Dict:
    """Check if selected TMs are available for the given date."""
    unavailable_tms = []
    
    # Ensure schedule_date is a date object (not a string or datetime)
    if isinstance(schedule_date, str):
        try:
            # Try ISO format first (YYYY-MM-DD)
            schedule_date = datetime.fromisoformat(schedule_date).date()
        except ValueError:
            try:
                schedule_date = datetime.strptime(schedule_date, "%Y-%m-%d").date()
            except ValueError:
                # As a last resort, use today's date
                schedule_date = datetime.now().date()
    elif isinstance(schedule_date, datetime):
        schedule_date = schedule_date.date()
    
    for tm_id in selected_tms:
        # Get TM availability for this date
        availability = await get_tm_availability(schedule_date, tm_id, user_id)
        
        # Check if any slot has "booked" status
        has_available_slot = False
        for slot in availability:
            if slot["status"] == "available":
                has_available_slot = True
                break
        
        if not has_available_slot:
            # Get TM details for better error message
            tm = await get_tm(tm_id, user_id)
            if tm:
                unavailable_tms.append({
                    "tm_id": tm_id,
                    "identifier": tm.identifier
                })
            else:
                unavailable_tms.append({
                    "tm_id": tm_id,
                    "identifier": "Unknown TM"
                })
    
    return {
        "all_available": len(unavailable_tms) == 0,
        "unavailable_tms": unavailable_tms
    }

async def generate_schedule(schedule_id: str, selected_tms: List[str], user_id: str) -> ScheduleModel:
    """Generate the schedule based on selected Transit Mixers with single pump constraint."""
    schedule = await schedules.find_one({"_id": ObjectId(schedule_id), "user_id": ObjectId(user_id)})
    if not schedule:
        raise ValueError("Schedule not found.")

    avg_capacity = await get_average_capacity(user_id)
    if avg_capacity == 0:
        raise ValueError("Cannot generate schedule, average capacity is 0.")

    # Check TM availability for the schedule date and convert to date object if it's a string
    schedule_date = schedule["input_params"].get("schedule_date")
    
    # Convert schedule_date to date object if it's a string
    if schedule_date and isinstance(schedule_date, str):
        try:
            # Try ISO format first (YYYY-MM-DD)
            schedule_date = datetime.fromisoformat(schedule_date).date()
        except ValueError:
            # If that fails, try other common formats
            try:
                schedule_date = datetime.strptime(schedule_date, "%Y-%m-%d").date()
            except ValueError:
                # As a last resort, use today's date
                schedule_date = datetime.now().date()
    elif schedule_date and isinstance(schedule_date, datetime):
        # Extract just the date part if it's a datetime
        schedule_date = schedule_date.date()
    
    if schedule_date:
        availability_check = await check_tm_availability(schedule_date, selected_tms, user_id)
        if not availability_check["all_available"]:
            unavailable_tms = ", ".join([tm["identifier"] for tm in availability_check["unavailable_tms"]])
            raise ValueError(f"Some selected Transit Mixers are not available for this date: {unavailable_tms}")

    # Get the actual TM identifiers and capacities from the database
    tm_map = {}  # Maps TM ID to identifier
    tm_capacities = {}  # Maps TM ID to capacity
    async for tm in transit_mixers.find({"_id": {"$in": [ObjectId(tm_id) for tm_id in selected_tms]}}):
        tm_map[str(tm["_id"])] = tm["identifier"]
        tm_capacities[str(tm["_id"])] = tm["capacity"]

    # Use avg_capacity for unloading time calculation only
    unloading_time_min = get_unloading_time(avg_capacity)
    
    # Get pump start time from the schedule input parameters
    # If it's already a datetime object, use it directly
    if isinstance(schedule["input_params"].get("pump_start"), datetime):
        base_time = schedule["input_params"]["pump_start"]
    else:
        # Try to parse from string if it's not a datetime
        try:
            base_time = datetime.strptime(schedule["input_params"].get("pump_start", "08:00"), "%H:%M")
            # Set today's date if only time is provided
            current_date = schedule_date if schedule_date else datetime.now().date()
            base_time = datetime.combine(current_date, base_time.time())
        except (ValueError, TypeError):
            # Default to today 8:00 AM if parsing fails
            current_date = schedule_date if schedule_date else datetime.now().date()
            base_time = datetime.combine(current_date, datetime.now().time().replace(hour=8, minute=0, second=0, microsecond=0))

    onward_time = schedule["input_params"]["onward_time"]
    return_time = schedule["input_params"]["return_time"]
    buffer_time = schedule["input_params"]["buffer_time"]

    trips = []
    total_quantity = schedule["input_params"]["quantity"]
    remaining_quantity = total_quantity
    completed_quantity = 0  # Track how much has been completed
    trip_no = 1
    
    # Track when each TM becomes available (returns from its last trip)
    tm_available_times = {tm: base_time for tm in selected_tms}
    
    pump_available_time = base_time  # pump is free at this time

    while remaining_quantity > 0:
        # Find all TMs that are available, sorted by availability time
        available_tms = sorted(
            [tm for tm in selected_tms if tm_available_times[tm] <= pump_available_time + timedelta(minutes=30)],
            key=lambda tm: tm_available_times[tm]
        )
        
        if not available_tms:
            # If no TMs are available within 30 minutes of when the pump is available,
            # just take the earliest available TM
            available_tms = sorted(selected_tms, key=lambda tm: tm_available_times[tm])

        # For the final trips, try to find a TM that can exactly match or get closest to remaining quantity
        if remaining_quantity <= max(tm_capacities.values()):
            # Sort TMs by how closely their capacity matches the remaining quantity
            available_tms = sorted(
                available_tms,
                key=lambda tm: abs(tm_capacities.get(tm, avg_capacity) - remaining_quantity)
            )
        else:
            # For non-final trips, prioritize TMs with larger capacities to minimize total trips
            available_tms = sorted(
                available_tms,
                key=lambda tm: (-tm_capacities.get(tm, avg_capacity), tm_available_times[tm])
            )
            
        for tm_id in available_tms:
            if remaining_quantity <= 0:
                break

            # Get this TM's specific capacity
            tm_capacity = tm_capacities.get(tm_id, avg_capacity)

            # Calculate earliest possible plant_start time (can't be earlier than when TM is available)
            # This ensures a TM doesn't leave for a trip before returning from previous one
            plant_start = tm_available_times[tm_id]
            
            # Calculate when this trip would reach the pump
            unloading_start = plant_start + timedelta(minutes=onward_time)
            
            # If pump isn't available at calculated unloading_start, adjust times
            if unloading_start < pump_available_time:
                unloading_start = pump_available_time
                plant_start = unloading_start - timedelta(minutes=onward_time)
                
                # Double-check plant_start isn't before TM is available
                if plant_start < tm_available_times[tm_id]:
                    plant_start = tm_available_times[tm_id]
                    unloading_start = plant_start + timedelta(minutes=onward_time)
            
            # Calculate remaining timings
            pump_start = unloading_start
            unloading_end = pump_start + timedelta(minutes=unloading_time_min)
            return_at = unloading_end + timedelta(minutes=return_time)
            
            # Use the TM identifier instead of just the ID
            tm_identifier = tm_map.get(tm_id, tm_id)
            
            # Update completed quantity and calculate capacity for this trip
            # Use the TM's actual capacity, but don't exceed remaining quantity
            trip_capacity = min(tm_capacity, remaining_quantity)
            
            # Check if we'd exceed the total required quantity
            if completed_quantity + trip_capacity > total_quantity:
                trip_capacity = total_quantity - completed_quantity
                
            completed_quantity += trip_capacity

            # Use datetime objects directly
            trip = Trip(
                trip_no=trip_no,
                tm_no=tm_identifier,
                tm_id=tm_id,
                plant_start=plant_start,
                pump_start=pump_start,
                unloading_time=unloading_end,
                return_=return_at,
                completed_capacity=completed_quantity
            )

            trips.append(trip)
            remaining_quantity -= trip_capacity
            trip_no += 1
            
            # Update when this TM will be available next
            tm_available_times[tm_id] = return_at
            
            # Update pump availability
            pump_available_time = unloading_end + timedelta(minutes=buffer_time)
            
            # Break after scheduling one trip with the current TM
            break

    # Update schedule
    await schedules.update_one(
        {"_id": ObjectId(schedule_id)},
        {"$set": {
            "output_table": [trip.model_dump(by_alias=True) for trip in trips],
            "status": "generated",
            "last_updated": datetime.utcnow()
        }}
    )

    updated_schedule = await schedules.find_one({"_id": ObjectId(schedule_id)})
    schedule_model = ScheduleModel(**updated_schedule)
    
    # Update the calendar for this schedule
    await update_calendar_after_schedule(schedule_model)
    
    return schedule_model

