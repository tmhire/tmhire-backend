from app.db.mongodb import schedule_calendar, transit_mixers, plants, schedules, PyObjectId
from app.models.schedule_calendar import DailySchedule, TimeSlot, TMAvailabilitySlot, ScheduleCalendarQuery, GanttMixer, GanttTask
from app.models.schedule import ScheduleModel
from datetime import datetime, date, time, timedelta, timezone
from bson import ObjectId
from typing import List, Dict, Optional, Any
from app.services.plant_service import get_plant

# Constants for calendar setup
CALENDAR_START_HOUR = 8  # 8AM
CALENDAR_END_HOUR = 20   # 8PM
SLOT_DURATION_MINUTES = 30
IST = timezone(timedelta(hours=5, minutes=30))

def _get_valid_date(date: date) -> date:
    # If date is a string, parse it
    if isinstance(date, str):
        try:
            date = datetime.fromisoformat(date).date()
        except ValueError:
            try:
                date = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                date = datetime.now().date()
    return date

async def get_calendar_for_date_range(
    query: ScheduleCalendarQuery, 
    user_id: str
) -> List[DailySchedule]:
    """Get calendar data for a date range with 30-minute time slots from 8AM to 8PM"""
    calendar_data = []
    
    # Ensure dates are valid date objects
    start_date = _get_valid_date(query.start_date)
    end_date = _get_valid_date(query.end_date)
    
    # Convert date objects to datetime objects for MongoDB compatibility
    start_datetime = datetime.combine(start_date, time.min)
    end_datetime = datetime.combine(end_date, time.max)
    
    print(f"Fetching calendar for date range: {start_datetime} to {end_datetime}, user_id: {user_id}")
    
    # Find all calendar entries in the given date range
    query_filter = {
        "user_id": ObjectId(user_id),
        "date": {
            "$gte": start_datetime,
            "$lte": end_datetime
        }
    }
    
    # Add plant or TM filter if provided
    if query.plant_id:
        query_filter["time_slots.tm_availability.plant_id"] = query.plant_id
    if query.tm_id:
        query_filter["time_slots.tm_availability.tm_id"] = query.tm_id
    
    print(f"Calendar query filter: {query_filter}")
    
    entry_count = 0
    async for day_schedule in schedule_calendar.find(query_filter).sort("date", 1):
        entry_count += 1
        print(f"Found calendar entry for date: {day_schedule.get('date')}")
        calendar_data.append(DailySchedule(**day_schedule))
    
    print(f"Found {entry_count} existing calendar entries")
    
    # If no entries found for some dates, initialize them
    existing_dates = {cal.date.date() if isinstance(cal.date, datetime) else cal.date for cal in calendar_data}
    print(f"Existing dates: {existing_dates}")
    
    current_date = start_date
    initialized_count = 0
    while current_date <= end_date:
        print(f"Checking if date {current_date} exists in calendar")
        if current_date not in existing_dates:
            print(f"Date {current_date} not found in calendar, initializing...")
            # Initialize new calendar day with TMs
            new_day = await initialize_calendar_day(current_date, user_id)
            if new_day:
                print(f"Successfully initialized calendar for date {current_date}")
                calendar_data.append(new_day)
                initialized_count += 1
            else:
                print(f"Failed to initialize calendar for date {current_date}")
        current_date += timedelta(days=1)
    
    print(f"Initialized {initialized_count} new calendar days")
    
    # Sort by date
    calendar_data.sort(key=lambda x: x.date)
    
    print(f"Returning {len(calendar_data)} calendar days in total")
    return calendar_data

async def initialize_calendar_day(
    day_date: date, 
    user_id: str
) -> Optional[DailySchedule]:
    """Initialize calendar data for a specific date with 30-minute time slots from 8AM to 8PM"""
    # Ensure day_date is a date object
    if isinstance(day_date, str):
        try:
            # Try ISO format first (YYYY-MM-DD)
            day_date = datetime.fromisoformat(day_date).date()
        except ValueError:
            try:
                day_date = datetime.strptime(day_date, "%Y-%m-%d").date()
            except ValueError:
                try:
                    # Try parsing with different formats
                    day_date = datetime.strptime(day_date, "%Y-%m-%dT%H:%M:%S").date()
                except ValueError:
                    # As a last resort, use today's date
                    day_date = datetime.now().date()
    elif isinstance(day_date, datetime):
        day_date = day_date.date()
    
    print(f"Initializing calendar day for date: {day_date}, user_id: {user_id}")
    
    # Get all TMs for this user
    tm_list = []
    
    # Get TMs and their corresponding plants
    tm_plants = {}
    async for plant in plants.find({"user_id": ObjectId(user_id)}):
        plant_id = str(plant["_id"])
        async for tm in transit_mixers.find({"user_id": ObjectId(user_id), "plant_id": plant["_id"]}):
            tm_plants[str(tm["_id"])] = {
                "tm_id": str(tm["_id"]),
                "tm_identifier": tm["identifier"],
                "plant_id": plant_id,
                "plant_name": plant["name"]
            }
            
    # Also get TMs with no plant assigned
    async for tm in transit_mixers.find({"user_id": ObjectId(user_id), "plant_id": None}):
        tm_plants[str(tm["_id"])] = {
            "tm_id": str(tm["_id"]),
            "tm_identifier": tm["identifier"],
            "plant_id": None,
            "plant_name": None
        }
    
    if not tm_plants:
        print(f"No transit mixers found for user {user_id}")
        return None
        
    # Use datetime object for MongoDB compatibility
    day_datetime = datetime.combine(day_date, time.min)
    
    # Create a new calendar day with time slots from 8AM to 8PM
    calendar_day = {
        "user_id": ObjectId(user_id),
        "date": day_datetime,
        "time_slots": [],
        "created_at": datetime.utcnow(),
        "last_updated": datetime.utcnow()
    }
    
    # Create time slots for every 30 minutes from 8AM to 8PM
    for hour in range(CALENDAR_START_HOUR, CALENDAR_END_HOUR):
        for minute in [0, 30]:
            start_time = datetime.combine(day_date, time(hour, minute))
            end_time = start_time + timedelta(minutes=SLOT_DURATION_MINUTES)
            
            # Create a time slot with all TMs available
            time_slot = {
                "start_time": start_time,
                "end_time": end_time,
                "tm_availability": []
            }
            
            # Add all TMs as available for this time slot
            for tm_data in tm_plants.values():
                time_slot["tm_availability"].append({
                    "tm_id": tm_data["tm_id"],
                    "tm_identifier": tm_data["tm_identifier"],
                    "plant_id": tm_data["plant_id"],
                    "plant_name": tm_data["plant_name"],
                    "status": "available",
                    "schedule_id": None
                })
            
            calendar_day["time_slots"].append(time_slot)
    
    # Find existing schedules for this date and update the time slots
    day_datetime_start = datetime.combine(day_date, time(0, 0))
    day_datetime_end = datetime.combine(day_date, time(23, 59, 59))
    
    print(f"Searching for schedules from {day_datetime_start} to {day_datetime_end}")
    
    # Get all schedules for this day
    schedule_query = {
        "user_id": ObjectId(user_id),
        "$or": [
            # Match strings in ISO format
            {"output_table.plant_start": {"$regex": f"{day_date.isoformat()}"}},
            {"output_table.return": {"$regex": f"{day_date.isoformat()}"}},
            # Match actual datetime objects
            {"output_table.plant_start": {"$gte": day_datetime_start, "$lte": day_datetime_end}},
            {"output_table.return": {"$gte": day_datetime_start, "$lte": day_datetime_end}}
        ]
    }
    
    print(f"Schedule query: {schedule_query}")
    
    schedule_count = 0
    async for schedule in schedules.find(schedule_query):
        schedule_count += 1
        print(f"Found schedule: {schedule['_id']}")
        # For each trip in the schedule, mark the TM as busy
        for trip in schedule.get("output_table", []):
            tm_id = trip.get("tm_id")
            if not tm_id:
                continue
                
            # Get the start and end times for this trip
            plant_start = trip.get("plant_start")
            return_time = trip.get("return")
            
            print(f"Processing trip for TM {tm_id}, plant_start: {plant_start}, return: {return_time}")
            
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
            
            # Handle if the values are already datetime objects from MongoDB
            if isinstance(plant_start, dict) and "$date" in plant_start:
                plant_start = datetime.fromtimestamp(plant_start["$date"] / 1000)
                
            if isinstance(return_time, dict) and "$date" in return_time:
                return_time = datetime.fromtimestamp(return_time["$date"] / 1000)
            
            print(f"Parsed times - plant_start: {plant_start}, return: {return_time}")
            
            # Update all time slots that overlap with this trip
            for time_slot in calendar_day["time_slots"]:
                slot_start = time_slot["start_time"]
                slot_end = time_slot["end_time"]
                
                # Check if this time slot overlaps with the trip
                if (plant_start < slot_end and return_time > slot_start):
                    # Find the TM in this time slot
                    for i, tm_avail in enumerate(time_slot["tm_availability"]):
                        if tm_avail["tm_id"] == tm_id:
                            # Mark the TM as booked
                            time_slot["tm_availability"][i]["status"] = "booked"
                            time_slot["tm_availability"][i]["schedule_id"] = str(schedule["_id"])
                            print(f"Marked TM {tm_id} as booked for slot {slot_start}-{slot_end}")
                            break
    
    print(f"Found {schedule_count} schedules for day {day_date}")
    
    # Save to database
    result = await schedule_calendar.insert_one(calendar_day)
    print(f"Calendar day saved with ID: {result.inserted_id}")
    
    # Return the calendar day
    return DailySchedule(**await schedule_calendar.find_one({"_id": result.inserted_id}))

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

async def get_tm_availability(
    date_val: date,
    tm_id: str,
    user_id: str
) -> List[Dict[str, Any]]:
    """
    Get availability slots for a specific TM on a specific date.
    Returns the status for each time slot from 8AM to 8PM.
    """
    # Ensure date_val is a date object
    date_val = _ensure_dateobj(date_val)
        
    # Generate default availability time slots (all available)
    availability_slots = generate_default_availability()
    
    # Convert date to date range for the day
    day_start = datetime.combine(date_val, time(0, 0))
    day_end = datetime.combine(date_val, time(23, 59, 59))
    
    # Find all schedules that have this TM occupied on this date
    from app.db.mongodb import schedules
    
    try:
        # Query schedules collection directly
        async for schedule in schedules.find({
            "user_id": ObjectId(user_id),
            "output_table": {
                "$elemMatch": {
                    "tm_id": tm_id,
                    "$or": [
                        {"plant_start": {"$gte": day_start, "$lte": day_end}},
                        {"return": {"$gte": day_start, "$lte": day_end}},
                        # Handle trips that span across the day
                        # {"plant_start": {"$lt": day_start}, "return": {"$gt": day_end}}
                    ]
                }
            }
        }):
            # For each trip in this schedule involving this TM
            for trip in schedule.get("output_table", []):
                if trip.get("tm_id") != tm_id:
                    continue
                    
                # Get departure and return times
                plant_start = trip.get("plant_start")
                return_time = trip.get("return")
                
                # Convert to datetime if needed
                if isinstance(plant_start, str):
                    try:
                        plant_start = datetime.fromisoformat(plant_start)
                    except ValueError:
                        continue
                        
                if isinstance(return_time, str):
                    try:
                        return_time = datetime.fromisoformat(return_time)
                    except ValueError:
                        continue
                
                # Check if the trip is on this day
                if plant_start.date() > date_val or return_time.date() < date_val:
                    continue
                    
                # Trim times to day boundaries if they extend beyond
                if plant_start < day_start:
                    plant_start = day_start
                if return_time > day_end:
                    return_time = day_end
                
                # Mark all slots that overlap with this trip as "booked"
                for i, slot in enumerate(availability_slots):
                    # Convert slot times to datetime objects
                    slot_start_str = slot["start_time"]
                    slot_end_str = slot["end_time"]
                    
                    slot_start = datetime.combine(
                        date_val, 
                        datetime.strptime(slot_start_str, "%H:%M").time()
                    )
                    slot_end = datetime.combine(
                        date_val,
                        datetime.strptime(slot_end_str, "%H:%M").time()
                    )
                    
                    # If this slot overlaps with the trip time, mark as booked
                    if plant_start < slot_end and return_time > slot_start:
                        availability_slots[i]["status"] = "booked"
                        # Convert ObjectId to string for JSON serialization
                        schedule_id = schedule.get("_id")
                        if isinstance(schedule_id, ObjectId):
                            schedule_id = str(schedule_id)
                        availability_slots[i]["schedule_id"] = schedule_id
    except Exception as e:
        print(f"Error checking TM availability: {str(e)}")
        # If there's an error, return default availability
        import logging
        logging.error(f"Error in get_tm_availability: {str(e)}")
        
    # Return the availability slots
    return availability_slots

def extract_tm_availability(calendar: Dict, tm_id: str) -> List[Dict[str, Any]]:
    """Helper function to extract TM availability from calendar data"""
    from app.schemas.utils import safe_serialize
    
    tm_availability = []
    
    # Handle both model objects and raw dictionaries
    time_slots = calendar.get("time_slots", [])
    if hasattr(calendar, "time_slots"):
        time_slots = calendar.time_slots
        
    for time_slot in time_slots:
        # Handle both model objects and raw dictionaries
        start_time = time_slot.get("start_time") if isinstance(time_slot, dict) else time_slot.start_time
        end_time = time_slot.get("end_time") if isinstance(time_slot, dict) else time_slot.end_time
        tm_avail_list = time_slot.get("tm_availability", []) if isinstance(time_slot, dict) else time_slot.tm_availability
        
        # Convert datetime objects to strings to ensure JSON serialization
        if isinstance(start_time, (datetime, date)):
            if isinstance(start_time, datetime):
                start_time = start_time.strftime("%H:%M")
            else:
                start_time = datetime.combine(start_time, time(0, 0)).strftime("%H:%M")
                
        if isinstance(end_time, (datetime, date)):
            if isinstance(end_time, datetime):
                end_time = end_time.strftime("%H:%M")
            else:
                end_time = datetime.combine(end_time, time(0, 0)).strftime("%H:%M")
        
        # Find availability for this specific TM
        found = False
        for tm_avail in tm_avail_list:
            # Handle both model objects and raw dictionaries
            current_tm_id = tm_avail.get("tm_id") if isinstance(tm_avail, dict) else tm_avail.tm_id
            
            # Convert ObjectId to string for comparison if needed
            if isinstance(current_tm_id, ObjectId):
                current_tm_id = str(current_tm_id)
                
            if current_tm_id == tm_id:
                status = tm_avail.get("status") if isinstance(tm_avail, dict) else tm_avail.status
                schedule_id = tm_avail.get("schedule_id") if isinstance(tm_avail, dict) else tm_avail.schedule_id
                
                # Convert ObjectId to string if needed
                if isinstance(schedule_id, ObjectId):
                    schedule_id = str(schedule_id)
                
                slot_data = {
                    "start_time": start_time,
                    "end_time": end_time,
                    "status": status,
                    "schedule_id": schedule_id
                }
                
                tm_availability.append(slot_data)
                found = True
                break
        
        # If TM not found in this slot, mark as unknown/error
        if not found:
            tm_availability.append({
                "start_time": start_time,
                "end_time": end_time,
                "status": "unknown",
                "schedule_id": None
            })
    
    return tm_availability

def generate_default_availability() -> List[Dict[str, Any]]:
    """Generate default availability time slots if calendar isn't available"""
    default_slots = []
    
    # Generate hourly slots from 8AM to 8PM
    start_hour = 8
    end_hour = 20
    
    for hour in range(start_hour, end_hour):
        # Create slot in HH:MM format
        slot_start = f"{hour:02d}:00"
        slot_end = f"{hour+1:02d}:00"
        
        default_slots.append({
            "start_time": slot_start,
            "end_time": slot_end,
            "status": "available",
            "schedule_id": None
        })
    
    return default_slots

async def update_calendar_after_schedule(schedule: ScheduleModel) -> bool:
    """
    Update the schedule calendar after a schedule has been created or updated.
    Updates the time slots for all days that this schedule spans.
    """
    # Get all days that this schedule spans
    affected_days = set()
    
    for trip in schedule.output_table:
        # Get plant start and return times
        plant_start = trip.plant_start
        return_time = trip.return_
        
        # Convert to datetime if needed
        if isinstance(plant_start, str):
            try:
                plant_start = datetime.fromisoformat(plant_start)
            except ValueError:
                continue
                
        if isinstance(return_time, str):
            try:
                return_time = datetime.fromisoformat(return_time)
            except ValueError:
                continue
        
        # Add all days between plant_start and return_time
        current_date = plant_start.date()
        end_date = return_time.date()
        
        while current_date <= end_date:
            affected_days.add(current_date)
            current_date += timedelta(days=1)
    
    # Update the calendar for each affected day
    for day_date in affected_days:
        # Get the calendar day
        day_datetime = datetime.combine(day_date, time.min)
        calendar = await schedule_calendar.find_one({
            "date": day_datetime,
            "user_id": schedule.user_id
        })
        
        if not calendar:
            # Initialize the calendar day
            await initialize_calendar_day(day_date, str(schedule.user_id))
            continue
        
        # Process each trip in the schedule
        for trip in schedule.output_table:
            tm_id = trip.tm_id
            
            # Get plant start and return times
            plant_start = trip.plant_start
            return_time = trip.return_
            
            # Convert to datetime if needed
            if isinstance(plant_start, str):
                try:
                    plant_start = datetime.fromisoformat(plant_start)
                except ValueError:
                    continue
                    
            if isinstance(return_time, str):
                try:
                    return_time = datetime.fromisoformat(return_time)
                except ValueError:
                    continue
            
            # Skip if this trip doesn't affect this day
            if plant_start.date() > day_date or return_time.date() < day_date:
                continue
            
            # Update all time slots that overlap with this trip
            for i, time_slot in enumerate(calendar["time_slots"]):
                slot_start = time_slot["start_time"]
                slot_end = time_slot["end_time"]
                
                # Skip if the slot doesn't overlap with the trip
                if plant_start >= slot_end or return_time <= slot_start:
                    continue
                
                # Find the TM in this time slot
                for j, tm_avail in enumerate(time_slot["tm_availability"]):
                    if tm_avail["tm_id"] == tm_id:
                        # Mark the TM as booked
                        calendar["time_slots"][i]["tm_availability"][j]["status"] = "booked"
                        calendar["time_slots"][i]["tm_availability"][j]["schedule_id"] = str(schedule.id)
                        break
        
        # Update the calendar in the database
        await schedule_calendar.update_one(
            {"_id": calendar["_id"]},
            {"$set": {
                "time_slots": calendar["time_slots"],
                "last_updated": datetime.utcnow()
            }}
        )
    
    return True 

async def debug_schedule(schedule_id: str):
    """Debug function to inspect schedule data"""
    schedule = await schedules.find_one({"_id": ObjectId(schedule_id)})
    if schedule:
        print("\nSchedule Debug Info:")
        print(f"ID: {schedule['_id']}")
        print(f"Client: {schedule.get('client_name')}")
        print(f"Status: {schedule.get('status')}")
        print("\nOutput Table:")
        for trip in schedule.get("output_table", []):
            print(f"\nTrip:")
            print(f"TM ID: {trip.get('tm_id')}")
            print(f"Plant Start: {trip.get('plant_start')}")
            print(f"Return: {trip.get('return')}")
    else:
        print(f"Schedule {schedule_id} not found")

def _parse_datetime_with_timezone(dt_str: str) -> datetime:
    """
    Parses a datetime string and assigns timezone if missing.
    Assumes naive datetimes are in UTC.
    """
    try:
        dt = datetime.fromisoformat(dt_str)
    except ValueError:
        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%fZ")
            dt = dt.replace(tzinfo=timezone.utc)
        except ValueError:
            print(f"❌ Failed to parse datetime string: {dt_str}")
            return None

    # If datetime is naive (no tzinfo), assume it's UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt

async def get_gantt_data(
    query_date: date,
    user_id: str
) -> List[GanttMixer]:
    """Get calendar data in Gantt chart format with multiple segments per trip"""
    print(f"Getting Gantt data for date: {query_date}")
    
    # Get all TMs first
    tm_map = {}
    tm_count = 0
    async for tm in transit_mixers.find({"user_id": ObjectId(user_id)}):
        tm_count += 1
        tm_id = str(tm["_id"])
        plant = await get_plant(tm["plant_id"], user_id)
        plant_name = getattr(plant, "name", "Unknown Plant")
        tm_map[tm_id] = GanttMixer(
            id=tm_id,
            name=tm.get("identifier", "Unknown"),
            plant=plant_name,
            client=None,
            tasks=[]
        )
    print(f"Found {tm_count} TMs")
        
    query_date = _get_valid_date(query_date)

    # Define the start and end of the day in UTC
    start_datetime = datetime.combine(query_date, time.min).replace(tzinfo=timezone.utc)
    end_datetime = datetime.combine(query_date + timedelta(days=1), time.min).replace(tzinfo=timezone.utc)
    print("dates: ", query_date, start_datetime, end_datetime)

    # Find all schedules in the date range
    schedule_query = {
        "user_id": ObjectId(user_id),
        "status": "generated",  # Only get generated schedules
        "$or": [
        {
            "output_table.plant_start": {
                "$gte": start_datetime.isoformat(),
                "$lt": end_datetime.isoformat()
            }
        },
        {
            "output_table.return": {
                "$gte": start_datetime.isoformat(),
                "$lt": end_datetime.isoformat()
            }
        }
    ]
    }
    
    print(f"Schedule query: {schedule_query}")
    
    schedule_count = 0
    task_count = 0
    async for schedule in schedules.find(schedule_query):
        schedule_count += 1
        print(f"\nProcessing schedule {schedule['_id']}")
        
        client_name = schedule.get("client_name")
        schedule_id = str(schedule["_id"])
        
        # Group trips by tm_id for this schedule
        trips_by_tm = {}
        for trip in schedule.get("output_table", []):
            tm_id = trip.get("tm_id")
            if not tm_id:
                continue
            trips_by_tm.setdefault(tm_id, []).append(trip)
        
        for tm_id, trips in trips_by_tm.items():
            if tm_id not in tm_map:
                print(f"Skipping trip for unknown TM: {tm_id}")
                continue
            # Sort trips by plant_start
            def get_dt(val):
                v = val.get("plant_start")
                return _parse_datetime_with_timezone(v) if isinstance(v, str) else v
            trips = sorted(trips, key=get_dt)
            for i, trip in enumerate(trips):
                # Parse all relevant datetimes
                plant_start = trip.get("plant_start")
                pump_start = trip.get("pump_start")
                unloading_time = trip.get("unloading_time")
                return_time = trip.get("return")
                plant_start_dt = _parse_datetime_with_timezone(plant_start) if isinstance(plant_start, str) else plant_start
                pump_start_dt = _parse_datetime_with_timezone(pump_start) if isinstance(pump_start, str) else pump_start
                unloading_time_dt = _parse_datetime_with_timezone(unloading_time) if isinstance(unloading_time, str) else unloading_time
                return_time_dt = _parse_datetime_with_timezone(return_time) if isinstance(return_time, str) else return_time
                # Only add segments if both times are present and on the query_date
                # Onward
                if plant_start_dt and pump_start_dt and plant_start_dt.date() == query_date and pump_start_dt.date() == query_date:
                    task_id = f"onward-{schedule_id}-{tm_id}"
                    tm_map[tm_id].tasks.append(GanttTask(
                        id=task_id,
                        start=plant_start_dt.strftime("%H:%M"),
                        end=pump_start_dt.strftime("%H:%M"),
                        client=client_name
                    ))
                    task_count += 1
                # Work
                if pump_start_dt and unloading_time_dt and pump_start_dt.date() == query_date and unloading_time_dt.date() == query_date:
                    task_id = f"work-{schedule_id}-{tm_id}"
                    tm_map[tm_id].tasks.append(GanttTask(
                        id=task_id,
                        start=pump_start_dt.strftime("%H:%M"),
                        end=unloading_time_dt.strftime("%H:%M"),
                        client=client_name
                    ))
                    task_count += 1
                # Return
                if unloading_time_dt and return_time_dt and unloading_time_dt.date() == query_date and return_time_dt.date() == query_date:
                    task_id = f"return-{schedule_id}-{tm_id}"
                    tm_map[tm_id].tasks.append(GanttTask(
                        id=task_id,
                        start=unloading_time_dt.strftime("%H:%M"),
                        end=return_time_dt.strftime("%H:%M"),
                        client=client_name
                    ))
                    task_count += 1
                # Cushion (gap to next trip)
                if return_time_dt and i+1 < len(trips):
                    next_trip = trips[i+1]
                    next_plant_start = next_trip.get("plant_start")
                    next_plant_start_dt = _parse_datetime_with_timezone(next_plant_start) if isinstance(next_plant_start, str) else next_plant_start
                    if next_plant_start_dt and return_time_dt.date() == query_date and next_plant_start_dt.date() == query_date and next_plant_start_dt > return_time_dt:
                        task_id = f"cushion-{schedule_id}-{tm_id}"
                        tm_map[tm_id].tasks.append(GanttTask(
                            id=task_id,
                            start=return_time_dt.strftime("%H:%M"),
                            end=next_plant_start_dt.strftime("%H:%M"),
                            client=client_name
                        ))
                        task_count += 1
    
    print(f"Processed {schedule_count} schedules and created {task_count} tasks")
    
    # Convert map to list
    return list(tm_map.values()) 