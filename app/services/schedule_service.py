from pymongo import DESCENDING
from app.db.mongodb import schedules, PyObjectId, transit_mixers, clients
from app.models.schedule import GetScheduleResponse, InputParams, ScheduleModel, CalculateTM, ScheduleUpdate, Trip
from app.services.plant_service import get_plant
from app.services.project_service import get_client_from_project
from app.services.pump_service import get_all_pumps
from app.services.tm_service import get_all_tms, get_average_capacity, get_tm
from app.services.client_service import get_client
from app.services.schedule_calendar_service import update_calendar_after_schedule, get_tm_availability
from datetime import datetime, timedelta, date, time
from bson import ObjectId
from typing import List, Optional, Dict, Any
from app.schemas.utils import safe_serialize
import math

# Unloading time lookup table
UNLOADING_TIME_LOOKUP = {
    4: 7,
    6: 10,
    7: 12,
    8: 14,
    9: 15,
    10: 17,
    12: 20
}

async def get_all_schedules(user_id: str) -> List[ScheduleModel]:
    schedule_list = []
    async for schedule in schedules.find({"user_id": ObjectId(user_id)}).sort("created_at", DESCENDING):
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

async def get_schedule(id: str, user_id: str) -> Optional[GetScheduleResponse]:
    schedule = await schedules.find_one({"_id": ObjectId(id), "user_id": ObjectId(user_id)})
    if schedule:
        # Get the tm_identifiers map for any TMs in the output_table
        tm_ids = []
        for trip in schedule.get("output_table", []):
            tm_id = trip.get("tm_id")
            if tm_id and ObjectId.is_valid(tm_id):
                tm_ids.append(ObjectId(tm_id))
        
        # If we have TM IDs, look up their identifiers
        if tm_ids:
            tm_map = {}
            async for tm in transit_mixers.find({"_id": {"$in": tm_ids}}):
                plant = (await get_plant(tm["plant_id"], user_id)).model_dump()
                tm_map[str(tm["_id"])] = {"identifier": tm["identifier"], "plant_name": plant["name"]}

            # Replace the TM IDs with their identifiers in the output_table
            for trip in schedule.get("output_table", []):
                tm_id = trip.get("tm_id")
                if tm_id and tm_id in tm_map:
                    trip["tm_no"] = tm_map[tm_id]["identifier"]
                    trip["plant_name"] = tm_map[tm_id]["plant_name"]
        
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
        
        # Add cycle_time and trip_no_for_tm to each trip in output_table
        tm_trip = {}
        for trip in schedule.get("output_table", []):
            # Calculate cycle_time
            plant_start = trip.get("plant_start")
            return_at = trip.get("return")
            # Convert to datetime if needed
            if isinstance(plant_start, str):
                try:
                    plant_start = datetime.fromisoformat(plant_start)
                except Exception:
                    plant_start = None
            if isinstance(return_at, str):
                try:
                    return_at = datetime.fromisoformat(return_at)
                except Exception:
                    return_at = None
            if plant_start and return_at:
                trip["cycle_time"] = (return_at - plant_start).total_seconds()
            else:
                trip["cycle_time"] = None

            tm_id = trip.get("tm_id")
            trip["cushion_time"] = 0
            # Calculate trip_no_for_tm
            if tm_id not in tm_trip:
                tm_trip[tm_id] = {"last_return": None, "trip_count": 1}
            else:
                tm_trip[tm_id]["trip_count"] += 1
                if tm_trip[tm_id]["last_return"] and plant_start:
                    trip["cushion_time"] = (plant_start - tm_trip[tm_id]["last_return"]).total_seconds()
            if return_at:
                tm_trip[tm_id]["last_return"] = return_at
            trip["trip_no_for_tm"] = tm_trip[tm_id]["trip_count"]

        input_params = InputParams(**schedule["input_params"])
        tm_suggestion = await calculate_tm_suggestions(user_id=user_id, input_params=input_params)
        tm_suggestion.pop("tm_count", None)
        available_tms, available_pumps = await get_available_tms_pumps(user_id, schedule["input_params"]["schedule_date"])
        pump_type = schedule.get("pump_type")
        for index, pump in enumerate(available_pumps):
            if pump.get("type") != pump_type:
                available_pumps.pop(index)

        return GetScheduleResponse(**schedule, **tm_suggestion, available_tms=available_tms, available_pumps=available_pumps)
    return None

async def update_schedule(id: str, schedule: ScheduleUpdate, user_id: str) -> Optional[ScheduleModel]:
    schedule_data = {k: v for k, v in schedule.model_dump().items() if v is not None}

    if not schedule_data:
        return await get_schedule(id, user_id)

    # Always require project_id and update client_id accordingly
    if "project_id" in schedule_data:
        from app.services.project_service import get_project
        project = await get_project(schedule_data["project_id"], user_id)
        if not project:
            raise ValueError("Project not found or does not belong to user.")
        client_id = getattr(project, "client_id", None)
        if not client_id:
            raise ValueError("Project does not have a client_id.")
        from app.services.client_service import get_client
        client = await get_client(str(client_id), user_id)
        if not client:
            raise ValueError("Client not found for the given project.")
        schedule_data["project_id"] = ObjectId(schedule_data["project_id"])
        schedule_data["client_id"] = ObjectId(str(client_id))
        schedule_data["client_name"] = client.name

    schedule_data["last_updated"] = datetime.utcnow()

    if "input_params" in schedule_data:
        quantity = schedule_data["input_params"]["quantity"]
        pumping_speed = schedule_data["input_params"]["pumping_speed"]
        schedule_data["pumping_time"] = quantity / pumping_speed
        schedule_data["status"] = "draft"
        schedule_data["output_table"] = []

    if "schedule_date" in schedule_data["input_params"]:
        if isinstance(schedule_data["input_params"]["schedule_date"], date):
            schedule_date = schedule_data["input_params"]["schedule_date"]
            schedule_data["input_params"]["schedule_date"] = schedule_date.isoformat()
        elif isinstance(schedule_data["input_params"]["schedule_date"], str):
            try:
                schedule_date = datetime.fromisoformat(schedule_data["input_params"]["schedule_date"]).date()
            except ValueError:
                try:
                    schedule_date = datetime.strptime(schedule_data["input_params"]["schedule_date"], "%Y-%m-%d").date()
                except ValueError:
                    schedule_date = datetime.now().date()
            schedule_data["input_params"]["schedule_date"] = schedule_date.isoformat()

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

async def calculate_tm_suggestions(user_id: str, input_params: InputParams) -> Dict:
    avg_capacity = await get_average_capacity(user_id)
    if avg_capacity == 0:
        raise ValueError("Cannot calculate TM count, average capacity is 0. Add TMs first.")
    
    onward_time = input_params.onward_time
    return_time = input_params.return_time
    buffer_time = input_params.buffer_time
    quantity = input_params.quantity
    pumping_speed = input_params.pumping_speed
    pump_start_from_plant = input_params.pump_start_time_from_plant

    # Calculate cycle time components
    unloading_time = get_unloading_time(avg_capacity)
    cycle_time = (onward_time + return_time + buffer_time + unloading_time)/60
    
    # Calculate pumping time
    pumping_time = quantity / pumping_speed
    
    # Calculate required number of TMs using the formula:
    # TMs = (Quantity × Cycle Time) / (Pumping Time × TM Capacity)
    tm_count = math.ceil((quantity * cycle_time) / (pumping_time * avg_capacity))
    
    # Calculate total trips needed
    total_trips = math.ceil(quantity / avg_capacity)
    
    # Calculate trips per TM and remaining trips
    base_trips_per_tm = total_trips // tm_count
    remaining_trips = total_trips % tm_count

    return {
        # "schedule_id": str(tm_id),
        "tm_count": tm_count,
        "total_trips": total_trips,
        "trips_per_tm": base_trips_per_tm,
        "remaining_trips": remaining_trips,
        "cycle_time": cycle_time
    }

async def _get_tm_ids_and_pump_ids_by_schedule_date(target_date: date, user_id: str) -> set[str]:
    target_date = _ensure_dateobj(target_date)
    tm_ids, pump_ids = set(), set()
    async for schedule in schedules.find({
        "input_params.schedule_date": target_date.isoformat(),
        "status": "generated",
        "user_id": ObjectId(user_id)
    }):
        for trip in schedule.get("output_table", []):
            tm_id = trip.get("tm_id")
            if tm_id:
                tm_ids.add(tm_id)
        if ("status" in schedule and schedule["status"] == "draft") or "pump" not in schedule:
            continue
        pump_id = schedule.get("pump")
        if pump_id:
            pump_ids.add(str(pump_id))
    return tm_ids, pump_ids

async def get_available_tms_pumps(user_id: str, schedule_date: date) -> List[Dict[str, Any]]:
    tms = await get_all_tms(user_id)
    pumps = await get_all_pumps(user_id)
    used_tms, used_pumps = await _get_tm_ids_and_pump_ids_by_schedule_date(schedule_date, user_id)
    available_tm_list, available_pump_list = [], []

    for tm in tms:
        available_tm_list.append({
            "id": str(tm.id),
            "identifier": tm.identifier,
            "capacity": tm.capacity,
            "plant_id": str(tm.plant_id) if tm.plant_id else None,
            "availability": str(tm.id) not in used_tms
        })
    for pump in pumps:
        available_pump_list.append({
            **pump.model_dump(by_alias=True),
            "id": str(pump.id),
            "availability": str(pump.id) not in used_pumps
        })


    return available_tm_list, available_pump_list

async def create_schedule_draft(schedule: CalculateTM, user_id: str) -> ScheduleModel:
    """Calculate the required Transit Mixer count and create a draft schedule. Always require both client and project."""
    # Validate and fetch project
    if not schedule.project_id:
        raise ValueError("A project_id is required to create a schedule.")
    from app.services.project_service import get_project
    project = await get_project(schedule.project_id, user_id)
    if not project:
        raise ValueError("Project not found or does not belong to user.")
    client_id = getattr(project, "client_id", None)
    if not client_id:
        raise ValueError("Project does not have a client_id.")
    from app.services.client_service import get_client
    client = await get_client(str(client_id), user_id)
    if not client:
        raise ValueError("Client not found for the given project.")
    # Prepare schedule data
    schedule_data = schedule.model_dump()
    schedule_data["user_id"] = ObjectId(user_id)
    schedule_data["created_at"] = datetime.utcnow()
    schedule_data["last_updated"] = datetime.utcnow()
    schedule_data["status"] = "draft"
    schedule_data["output_table"] = []
    # Store both client_id and project_id
    schedule_data["project_id"] = ObjectId(schedule.project_id)
    schedule_data["client_id"] = ObjectId(str(client_id))
    schedule_data["client_name"] = client.name
    # Ensure input_params is included in the draft schedule and pump_start is a datetime
    input_params = schedule.input_params.model_dump()
    # Extract and standardize schedule_date
    schedule_date = None
    if "schedule_date" in input_params:
        if isinstance(input_params["schedule_date"], date):
            schedule_date = input_params["schedule_date"]
            input_params["schedule_date"] = schedule_date.isoformat()
        elif isinstance(input_params["schedule_date"], str):
            try:
                schedule_date = datetime.fromisoformat(input_params["schedule_date"]).date()
            except ValueError:
                try:
                    schedule_date = datetime.strptime(input_params["schedule_date"], "%Y-%m-%d").date()
                except ValueError:
                    schedule_date = datetime.now().date()
            input_params["schedule_date"] = schedule_date.isoformat()
    else:
        schedule_date = datetime.now().date()
        input_params["schedule_date"] = schedule_date.isoformat()
    # Process pump_start time
    pump_start_time = None
    if "pump_start" in input_params:
        if isinstance(input_params["pump_start"], datetime):
            pump_start_time = input_params["pump_start"].time()
        elif isinstance(input_params["pump_start"], dict) and "$date" in input_params["pump_start"]:
            if isinstance(input_params["pump_start"]["$date"], str):
                date_str = input_params["pump_start"]["$date"]
                pump_start_time = datetime.fromisoformat(date_str.replace("Z", "+00:00")).time()
            else:
                pump_start_time = datetime.fromtimestamp(input_params["pump_start"]["$date"] / 1000).time()
        elif isinstance(input_params["pump_start"], str):
            try:
                if "T" in input_params["pump_start"]:
                    pump_start_time = datetime.fromisoformat(input_params["pump_start"]).time()
                else:
                    pump_start_time = datetime.strptime(input_params["pump_start"], "%H:%M").time()
            except ValueError:
                pump_start_time = time(8, 0)
    if not pump_start_time:
        pump_start_time = time(8, 0)
    input_params["pump_start"] = datetime.combine(schedule_date, pump_start_time)
    schedule_data["input_params"] = input_params
    tm_suggestion = await calculate_tm_suggestions(user_id, InputParams(**input_params))
    schedule_data["tm_count"] = tm_suggestion["tm_count"]
    result = await schedules.insert_one(schedule_data)
    new_schedule = await schedules.find_one({"_id": result.inserted_id, "user_id": ObjectId(user_id)})
    if new_schedule:
        return ScheduleModel(**new_schedule)
    return None

def _ensure_dateobj(date: datetime | str) -> date:
    # Convert date to date object if it's a string
    if date and isinstance(date, str):
        try:
            # Try ISO format first (YYYY-MM-DD)
            date = datetime.fromisoformat(date).date()
        except ValueError:
            # If that fails, try other common formats
            try:
                date = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                # As a last resort, use today's date
                date = datetime.now().date()
    elif date and isinstance(date, datetime):
        # Extract just the date part if it's a datetime
        date = date.date()
    else:
        # If no date is provided, use today's date
        date = datetime.now().date()
        
    return date

async def check_tm_availability(schedule_date: date, selected_tms: List[str], user_id: str) -> Dict:
    """Check if selected TMs are available for the given date."""
    unavailable_tms = []
    
    # Ensure schedule_date is a date object (not a string or datetime)
    schedule_date = _ensure_dateobj(schedule_date)
    
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

async def generate_schedule(schedule_id: str, selected_tms: List[str], pump_id: str, user_id: str) -> ScheduleModel:
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
    schedule_date = _ensure_dateobj(schedule_date)
    
    print(f"Using schedule_date: {schedule_date} for all datetime fields")
    
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
    # If it's already a datetime object, extract the time component
    pump_start_time = None
    if isinstance(schedule["input_params"].get("pump_start"), datetime):
        pump_start_time = schedule["input_params"]["pump_start"].time()
    else:
        # Try to parse from string if it's not a datetime
        try:
            # Handle MongoDB $date object format
            if isinstance(schedule["input_params"].get("pump_start"), dict) and "$date" in schedule["input_params"]["pump_start"]:
                if isinstance(schedule["input_params"]["pump_start"]["$date"], str):
                    date_str = schedule["input_params"]["pump_start"]["$date"]
                    pump_start_time = datetime.fromisoformat(date_str.replace("Z", "+00:00")).time()
                else:
                    pump_start_time = datetime.fromtimestamp(schedule["input_params"]["pump_start"]["$date"] / 1000).time()
            else:
                # Try parsing time string
                time_str = schedule["input_params"].get("pump_start", "08:00")
                if isinstance(time_str, str):
                    if "T" in time_str:  # ISO format with date and time
                        pump_start_time = datetime.fromisoformat(time_str).time()
                    else:  # Just time component
                        pump_start_time = datetime.strptime(time_str, "%H:%M").time()
        except (ValueError, TypeError):
            # Default to 8:00 AM if parsing fails
            pump_start_time = time(8, 0)
    
    # If we couldn't get a time, default to 8:00 AM
    if not pump_start_time:
        pump_start_time = time(8, 0)
        
    # Combine the schedule date with the pump start time
    base_time = datetime.combine(schedule_date, pump_start_time)
    print(f"Base time set to: {base_time}")

    onward_time = schedule["input_params"]["onward_time"]  # Always use TM onward_time for TM trips
    return_time = schedule["input_params"]["return_time"]
    buffer_time = schedule["input_params"]["buffer_time"]

    trips = []
    total_quantity = schedule["input_params"]["quantity"]
    remaining_quantity = total_quantity
    completed_quantity = 0  # Track how much has been completed
    trip_no = 0
    
    # Track usage count for each TM to ensure even distribution
    tm_usage_count = {tm: 0 for tm in selected_tms}
    # Track trip number for each TM
    tm_trip_counter = {tm: 0 for tm in selected_tms}
    # Track when each TM becomes available (returns from its last trip)
    tm_available_times = {tm: datetime.combine(schedule_date, time.min) for tm in selected_tms}
    
    pump_available_time = base_time  # pump is free at this time
    
    # Maximum time to wait for a previously used TM before using a different one (in minutes)
    max_wait_time = 15

    if schedule["type"] == "supply":
        selected_tm = selected_tms[0]  # For supply schedules, we only use one TM
        tm_identifier = tm_map.get(selected_tm, selected_tm)
        tm_capacity = tm_capacities.get(selected_tm, avg_capacity)
        # if tm_capacity < total_quantity:
        #     raise ValueError(f"Selected TM {tm_identifier} capacity {tm_capacity} is less than total quantity {total_quantity}.")
        
        tm_unloading_time = UNLOADING_TIME_LOOKUP.get(tm_capacity)
        if tm_unloading_time is None:
            tm_unloading_time = get_unloading_time(tm_capacity)

        pump_start = base_time
        plant_start = pump_start - timedelta(minutes=onward_time)
        unloading_end = pump_start + timedelta(minutes=tm_unloading_time)
        return_at = unloading_end + timedelta(minutes=return_time)

        tm_usage_count[selected_tm] += 1
        tm_trip_counter[selected_tm] += 1

        completed_quantity = tm_capacity

        cycle_time = (return_at - plant_start).total_seconds()
        trip_no_for_tm = tm_trip_counter[selected_tm]

        # Use datetime objects directly
        trip = Trip(
            trip_no=trip_no,
            tm_no=tm_identifier,
            tm_id=selected_tm,
            plant_start=plant_start,
            pump_start=pump_start,
            unloading_time=unloading_end,
            return_=return_at,
            completed_capacity=completed_quantity,
            cycle_time=cycle_time,
            trip_no_for_tm=trip_no_for_tm
        )

        trips.append(trip)

        # Safely serialize the trips to ensure all datetimes are properly converted
        serialized_trips = safe_serialize([trip.model_dump(by_alias=True) for trip in trips])

        # Update schedule
        await schedules.update_one(
            {"_id": ObjectId(schedule_id)},
            {"$set": {
                "output_table": serialized_trips,
                "status": "generated",
                "last_updated": datetime.utcnow()
            }}
        )

        updated_schedule = await schedules.find_one({"_id": ObjectId(schedule_id)})
        schedule_model = ScheduleModel(**updated_schedule)
        
        # Update the calendar for this schedule
        await update_calendar_after_schedule(schedule_model)
        
        return await get_schedule(schedule_id, user_id)
    
    
    if pump_id is None:
        raise ValueError("pump ID is required to generate the schedule")

    while completed_quantity < total_quantity:
        trip_no += 1
        selected_tm = None
        earliest_effective_site_arrival_for_best_tm = datetime.max 

        target_site_arrival_for_current_trip = unloading_end + timedelta(minutes=1) if trip_no > 1 else pump_available_time

        for tm in selected_tms:
            # Calculate when TM becomes available after buffer time
            min_tm_departure_time = tm_available_times[tm]
            # Add buffer time to determine when TM is actually available for next trip
            tm_available_time = min_tm_departure_time + timedelta(minutes=buffer_time)
            potential_tm_arrival_time = tm_available_time + timedelta(minutes=onward_time)
            effective_site_arrival = max(target_site_arrival_for_current_trip, potential_tm_arrival_time)

            if effective_site_arrival < earliest_effective_site_arrival_for_best_tm:
                earliest_effective_site_arrival_for_best_tm = effective_site_arrival
                selected_tm = tm
            elif effective_site_arrival == earliest_effective_site_arrival_for_best_tm:
                if selected_tm is None or tm_usage_count[tm] < tm_usage_count[selected_tm]:
                    selected_tm = tm

        if selected_tm is None:
            print(f"Warning: Could not find a suitable TM for overall trip {trip_no}. Scheduling stopped.")
            raise ValueError(f"Could not find suitable TM for trip number: {trip_no}")
        
        tm_identifier = tm_map.get(selected_tm, selected_tm)
        tm_capacity = tm_capacities.get(selected_tm, avg_capacity)
        tm_unloading_time = UNLOADING_TIME_LOOKUP.get(tm_capacity)

        if tm_unloading_time is None:
            tm_unloading_time = get_unloading_time(tm_capacity)

        pump_start = earliest_effective_site_arrival_for_best_tm
        plant_start = pump_start - timedelta(minutes=onward_time)
        unloading_end = pump_start + timedelta(minutes=tm_unloading_time)
        return_at = unloading_end + timedelta(minutes=return_time)

        # Update next available time to include buffer time
        tm_available_times[selected_tm] = return_at
        tm_usage_count[selected_tm] += 1
        tm_trip_counter[selected_tm] += 1
        
        volume_pumped = tm_capacity
        completed_quantity += tm_capacity
        if completed_quantity > total_quantity:
            volume_pumped = remaining_quantity
            completed_quantity = total_quantity

        remaining_quantity -= volume_pumped

        # Calculate cycle_time (return_ - plant_start in seconds)
        cycle_time = (return_at - plant_start).total_seconds()
        trip_no_for_tm = tm_trip_counter[selected_tm]

        # Use datetime objects directly
        trip = Trip(
            trip_no=trip_no,
            tm_no=tm_identifier,
            tm_id=selected_tm,
            plant_start=plant_start,
            pump_start=pump_start,
            unloading_time=unloading_end,
            return_=return_at,
            completed_capacity=completed_quantity,
            cycle_time=cycle_time,
            trip_no_for_tm=trip_no_for_tm
        )

        trips.append(trip)

    # Safely serialize the trips to ensure all datetimes are properly converted
    serialized_trips = safe_serialize([trip.model_dump(by_alias=True) for trip in trips])

    # Update schedule
    await schedules.update_one(
        {"_id": ObjectId(schedule_id)},
        {"$set": {
            "pump": ObjectId(pump_id) if ObjectId(pump_id) else None,
            "output_table": serialized_trips,
            "status": "generated",
            "last_updated": datetime.utcnow()
        }}
    )

    updated_schedule = await schedules.find_one({"_id": ObjectId(schedule_id)})
    schedule_model = ScheduleModel(**updated_schedule)
    
    # Update the calendar for this schedule
    await update_calendar_after_schedule(schedule_model)
    
    return await get_schedule(schedule_id, user_id)

async def get_daily_schedule(date_val: date, user_id: str) -> List[Dict[str, Any]]:
    """
    Get all scheduled trips for a specific date, grouped by transit mixer.
    Returns a Gantt-chart friendly format for visualizing the day's schedule.
    """
    # Ensure date_val is a date object
    if isinstance(date_val, str):
        try:
            date_val = datetime.fromisoformat(date_val).date()
        except ValueError:
            try:
                date_val = datetime.strptime(date_val, "%Y-%m-%d").date()
            except ValueError:
                date_val = datetime.now().date()
    
    print(f"Getting daily schedule for date: {date_val}, user_id: {user_id}")
    
    # Convert date to datetime range for the day
    day_start = datetime.combine(date_val, time(0, 0))
    day_end = datetime.combine(date_val, time(23, 59, 59))
    
    print(f"Day range: {day_start} to {day_end}")
    
    # Data structure to hold TM schedules
    tm_schedules = {}
    
    # Create a query that handles both string dates and MongoDB dates
    query = {
        "user_id": ObjectId(user_id),
        "$or": [
            # Match string date format in ISO format
            {"output_table.plant_start": {"$regex": f"{date_val.isoformat()}"}},
            {"output_table.return": {"$regex": f"{date_val.isoformat()}"}},
            # Match datetime objects
            {"output_table.plant_start": {"$gte": day_start, "$lte": day_end}},
            {"output_table.return": {"$gte": day_start, "$lte": day_end}},
            # Handle case where trip spans across the day
            {
                "output_table.plant_start": {"$lt": day_start},
                "output_table.return": {"$gt": day_end}
            }
        ]
    }
    
    print(f"Schedule query: {query}")
    
    # Find all schedules that have trips on this day
    schedule_count = 0
    async for schedule in schedules.find(query):
        schedule_count += 1
        client_name = schedule.get("client_name", "Unknown Client")
        print(f"Found schedule: {schedule['_id']} for client: {client_name}")
        
        # For each trip in the schedule
        trip_count = 0
        for trip in schedule.get("output_table", []):
            trip_count += 1
            tm_id = trip.get("tm_id")
            if not tm_id:
                print(f"Trip has no TM ID: {trip}")
                continue
                
            # Get the trip times
            plant_start = trip.get("plant_start")
            return_time = trip.get("return")
            completed_capacity = trip.get("completed_capacity", 0)
            prev_capacity = 0
            
            print(f"Processing trip for TM {tm_id}, plant_start: {plant_start}, return: {return_time}")
            
            # Find the previous trip for this TM to calculate the volume for this trip
            for i, prev_trip in enumerate(schedule.get("output_table", [])):
                if prev_trip.get("tm_id") == tm_id:
                    if prev_trip == trip:
                        break
                    prev_capacity = prev_trip.get("completed_capacity", 0)
            
            trip_volume = completed_capacity - prev_capacity
            
            # Convert to datetime if needed
            if isinstance(plant_start, str):
                try:
                    plant_start = datetime.fromisoformat(plant_start)
                except ValueError:
                    try:
                        # Try parsing with different formats if fromisoformat fails
                        plant_start = datetime.strptime(plant_start, "%Y-%m-%dT%H:%M:%S")
                    except ValueError:
                        try:
                            # Try with timezone format
                            plant_start = datetime.strptime(plant_start, "%Y-%m-%dT%H:%M:%S.%fZ")
                        except ValueError:
                            print(f"Could not parse plant_start: {plant_start}")
                            continue
                    
            if isinstance(return_time, str):
                try:
                    return_time = datetime.fromisoformat(return_time)
                except ValueError:
                    try:
                        # Try parsing with different formats if fromisoformat fails
                        return_time = datetime.strptime(return_time, "%Y-%m-%dT%H:%M:%S")
                    except ValueError:
                        try:
                            # Try with timezone format
                            return_time = datetime.strptime(return_time, "%Y-%m-%dT%H:%M:%S.%fZ")
                        except ValueError:
                            print(f"Could not parse return_time: {return_time}")
                            continue
            
            # Handle if the values are MongoDB date objects
            if isinstance(plant_start, dict) and "$date" in plant_start:
                if isinstance(plant_start["$date"], str):
                    plant_start = datetime.fromisoformat(plant_start["$date"].replace("Z", "+00:00"))
                else:
                    plant_start = datetime.fromtimestamp(plant_start["$date"] / 1000)
                
            if isinstance(return_time, dict) and "$date" in return_time:
                if isinstance(return_time["$date"], str):
                    return_time = datetime.fromisoformat(return_time["$date"].replace("Z", "+00:00"))
                else:
                    return_time = datetime.fromtimestamp(return_time["$date"] / 1000)
            
            print(f"Parsed times - plant_start: {plant_start}, return: {return_time}")
            
            # Check if trip overlaps with our target day
            if (plant_start > day_end) or (return_time < day_start):
                print(f"Trip does not overlap with target day")
                continue
                
            # Adjust times if they span beyond this day
            if plant_start < day_start:
                plant_start = day_start
                
            if return_time > day_end:
                return_time = day_end
            
            # Get the TM identifier
            tm_identifier = await get_tm_identifier(tm_id, user_id)
            
            # Add to the data structure
            if tm_id not in tm_schedules:
                tm_schedules[tm_id] = {
                    "tm": tm_identifier,
                    "trips": []
                }
                
            # Add this trip
            tm_schedules[tm_id]["trips"].append({
                "client": client_name,
                "start": plant_start.strftime("%H:%M"),
                "end": return_time.strftime("%H:%M"),
                "volume": f"{trip_volume} m³"
            })
            print(f"Added trip to TM {tm_id}: {plant_start.strftime('%H:%M')} - {return_time.strftime('%H:%M')}")
        
        print(f"Processed {trip_count} trips for schedule {schedule['_id']}")
    
    print(f"Found {schedule_count} schedules for date {date_val}")
    
    # Convert to list and sort
    result = list(tm_schedules.values())
    
    # Sort by TM identifier
    result.sort(key=lambda x: x["tm"])
    
    print(f"Returning {len(result)} TM schedules")
    return result

async def get_tm_identifier(tm_id: str, user_id: str) -> str:
    """Helper function to get the TM identifier (registration number) from its ID"""
    from app.db.mongodb import transit_mixers
    
    # Try to get the TM identifier from the database
    tm = await transit_mixers.find_one({"_id": ObjectId(tm_id), "user_id": ObjectId(user_id)})
    if tm:
        return tm.get("identifier", tm_id)
    return tm_id

