from app.db.mongodb import schedule_calendar, transit_mixers, plants, schedules, PyObjectId
from app.models.schedule_calendar import DailySchedule, TimeSlot, TMAvailabilitySlot, ScheduleCalendarQuery
from app.models.schedule import ScheduleModel
from datetime import datetime, date, time, timedelta
from bson import ObjectId
from typing import List, Dict, Optional, Any

# Constants for calendar setup
CALENDAR_START_HOUR = 8  # 8AM
CALENDAR_END_HOUR = 20   # 8PM
SLOT_DURATION_MINUTES = 30

async def get_calendar_for_date_range(
    query: ScheduleCalendarQuery, 
    user_id: str
) -> List[DailySchedule]:
    """Get calendar data for a date range with 30-minute time slots from 8AM to 8PM"""
    calendar_data = []
    
    # Convert date objects to datetime objects for MongoDB compatibility
    start_datetime = datetime.combine(query.start_date, time.min)
    end_datetime = datetime.combine(query.end_date, time.max)
    
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
    
    async for day_schedule in schedule_calendar.find(query_filter).sort("date", 1):
        calendar_data.append(DailySchedule(**day_schedule))
    
    # If no entries found for some dates, initialize them
    existing_dates = {cal.date.date() if isinstance(cal.date, datetime) else cal.date for cal in calendar_data}
    
    current_date = query.start_date
    while current_date <= query.end_date:
        if current_date not in existing_dates:
            # Initialize new calendar day with TMs
            new_day = await initialize_calendar_day(current_date, user_id)
            if new_day:
                calendar_data.append(new_day)
        current_date += timedelta(days=1)
    
    # Sort by date
    calendar_data.sort(key=lambda x: x.date)
    
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
                # As a last resort, use today's date
                day_date = datetime.now().date()
    elif isinstance(day_date, datetime):
        day_date = day_date.date()
    
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
    
    # Get all schedules for this day
    async for schedule in schedules.find({
        "user_id": ObjectId(user_id),
        "$or": [
            {"output_table.plant_start": {"$gte": day_datetime_start, "$lte": day_datetime_end}},
            {"output_table.return": {"$gte": day_datetime_start, "$lte": day_datetime_end}}
        ]
    }):
        # For each trip in the schedule, mark the TM as busy
        for trip in schedule.get("output_table", []):
            tm_id = trip.get("tm_id")
            if not tm_id:
                continue
                
            # Get the start and end times for this trip
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
                            break
    
    # Save to database
    result = await schedule_calendar.insert_one(calendar_day)
    
    # Return the calendar day
    return DailySchedule(**await schedule_calendar.find_one({"_id": result.inserted_id}))

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
    if isinstance(date_val, str):
        try:
            # Try ISO format first (YYYY-MM-DD)
            date_val = datetime.fromisoformat(date_val).date()
        except ValueError:
            try:
                date_val = datetime.strptime(date_val, "%Y-%m-%d").date()
            except ValueError:
                # As a last resort, use today's date
                date_val = datetime.now().date()
    elif isinstance(date_val, datetime):
        date_val = date_val.date()
        
    # Convert date to datetime for MongoDB compatibility
    date_datetime = datetime.combine(date_val, time.min)
    
    # Try both date and datetime formats
    calendar = await schedule_calendar.find_one({
        "date": date_datetime,
        "user_id": ObjectId(user_id)
    })
    
    if not calendar:
        # Initialize calendar day
        calendar_day = await initialize_calendar_day(date_val, user_id)
        if not calendar_day:
            return []
        
        # Extract availability data for this TM
        tm_availability = []
        for time_slot in calendar_day.time_slots:
            for tm_avail in time_slot.tm_availability:
                if tm_avail.tm_id == tm_id:
                    tm_availability.append({
                        "start_time": time_slot.start_time,
                        "end_time": time_slot.end_time,
                        "status": tm_avail.status,
                        "schedule_id": tm_avail.schedule_id
                    })
                    break
        
        return tm_availability
    
    # Extract availability data for this TM
    tm_availability = []
    for time_slot in calendar["time_slots"]:
        for tm_avail in time_slot["tm_availability"]:
            if tm_avail["tm_id"] == tm_id:
                tm_availability.append({
                    "start_time": time_slot["start_time"],
                    "end_time": time_slot["end_time"],
                    "status": tm_avail["status"],
                    "schedule_id": tm_avail["schedule_id"]
                })
                break
    
    return tm_availability

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