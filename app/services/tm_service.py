from app.db.mongodb import transit_mixers, schedules
from app.models.transit_mixer import TransitMixerModel, TransitMixerCreate, TransitMixerUpdate
from bson import ObjectId
from typing import List, Optional, Dict, Any
# from app.services.schedule_calendar_service import get_tm_availability
from datetime import datetime, date, time, timedelta
from pymongo import DESCENDING

async def get_all_tms(user_id: str) -> List[TransitMixerModel]:
    """Get all transit mixers for a user"""
    tms = []
    async for tm in transit_mixers.find({"user_id": ObjectId(user_id)}).sort("created_at", DESCENDING):
        tms.append(TransitMixerModel(**tm))
    return tms

async def get_tm(id: str, user_id: str) -> Optional[TransitMixerModel]:
    """Get a specific transit mixer by ID"""
    tm = await transit_mixers.find_one({"_id": ObjectId(id), "user_id": ObjectId(user_id)})
    if tm:
        return TransitMixerModel(**tm)
    return None

async def create_tm(tm: TransitMixerCreate, user_id: str) -> TransitMixerModel:
    """Create a new transit mixer"""
    tm_data = tm.model_dump()
    tm_data["user_id"] = ObjectId(user_id)
    tm_data["created_at"] = datetime.utcnow()
    tm_data["last_updated"] = datetime.utcnow()
    
    # Convert plant_id to ObjectId if it exists
    if "plant_id" in tm_data and tm_data["plant_id"]:
        tm_data["plant_id"] = ObjectId(tm_data["plant_id"])
    
    result = await transit_mixers.insert_one(tm_data)
    
    new_tm = await transit_mixers.find_one({"_id": result.inserted_id})
    return TransitMixerModel(**new_tm)

async def update_tm(id: str, tm: TransitMixerUpdate, user_id: str) -> Optional[TransitMixerModel]:
    """Update a transit mixer"""
    tm_data = {k: v for k, v in tm.model_dump().items() if v is not None}
    
    if not tm_data:
        return await get_tm(id, user_id)
    
    # Convert plant_id to ObjectId if it exists
    if "plant_id" in tm_data and tm_data["plant_id"]:
        tm_data["plant_id"] = ObjectId(tm_data["plant_id"])
    
    await transit_mixers.update_one(
        {"_id": ObjectId(id), "user_id": ObjectId(user_id)},
        {"$set": tm_data}
    )
    
    return await get_tm(id, user_id)

async def delete_tm(id: str, user_id: str) -> bool:
    """Delete a transit mixer"""
    result = await transit_mixers.delete_one({"_id": ObjectId(id), "user_id": ObjectId(user_id)})
    return result.deleted_count > 0

async def get_average_capacity(user_id: str) -> float:
    """Get the average capacity of all transit mixers for a user"""
    result = await transit_mixers.aggregate([
        {"$match": {"user_id": ObjectId(user_id)}},
        {"$group": {"_id": None, "avg_capacity": {"$avg": "$capacity"}}}
    ]).to_list(1)
    
    if result:
        return result[0]["avg_capacity"]
    return 0.0

async def get_tms_by_plant(plant_id: str, user_id: str) -> List[TransitMixerModel]:
    """Get all transit mixers for a specific plant"""
    tms = []
    async for tm in transit_mixers.find({"plant_id": ObjectId(plant_id), "user_id": ObjectId(user_id)}):
        tms.append(TransitMixerModel(**tm))
    return tms

# async def get_available_tms(date_val: Any, user_id: str) -> List[TransitMixerModel]:
#     """Get all transit mixers that are available on the given date."""
#     # Parse the date if it's a string, otherwise use as-is if it's already a date object
#     date_obj = None
#     if isinstance(date_val, str):
#         try:
#             date_obj = datetime.strptime(date_val, "%Y-%m-%d").date()
#         except ValueError:
#             # Fallback to today if date format is invalid
#             date_obj = datetime.now().date()
#     elif isinstance(date_val, date):
#         date_obj = date_val
#     else:
#         # Fallback to today for any other type
#         date_obj = datetime.now().date()
    
#     # Get all TMs for this user
#     tms = await get_all_tms(user_id)
#     available_tms = []
    
#     for tm in tms:
#         try:
#             # Check availability for this TM
#             availability = await get_tm_availability(date_obj, str(tm.id), user_id)
            
#             # If any time slot is available, consider the TM available
#             tm_is_available = False
#             for slot in availability:
#                 if slot.get("status") == "available":
#                     tm_is_available = True
#                     break
            
#             if tm_is_available:
#                 available_tms.append(tm)
#         except Exception as e:
#             import logging
#             logging.error(f"Error checking availability for TM {tm.id}: {str(e)}")
#             # Continue with the next TM if there's an error
#             continue
    
#     return available_tms

async def get_tm_availability_slots(tm_id: str, date_val: date, user_id: str) -> Dict[str, Any]:
    """
    Get availability for a specific TM on a specific date in 30-minute intervals.
    Returns an object with tm_id and availability array with slots for the entire day.
    """
    # Get the TM details to verify it exists and belongs to the user
    tm = await get_tm(tm_id, user_id)
    if not tm:
        return {"tm_id": tm_id, "availability": []}
    
    # Start with a full day of 30-minute intervals
    availability = []
    current_time = datetime.combine(date_val, time(0, 0))
    end_of_day = datetime.combine(date_val, time(23, 59, 59))
    
    # Create all 30-minute slots for the day (48 slots)
    while current_time < end_of_day:
        slot_start = current_time
        slot_end = current_time + timedelta(minutes=30)
        
        availability.append({
            "start": slot_start.strftime("%H:%M"),
            "end": slot_end.strftime("%H:%M"),
            "status": "available"
        })
        
        current_time = slot_end
    
    # Get all schedules that involve this TM on the specified date
    day_start = datetime.combine(date_val, time(0, 0))
    day_end = datetime.combine(date_val, time(23, 59, 59))
    
    # Find all schedules with trips involving this TM on the given date
    async for schedule in schedules.find({
        "user_id": ObjectId(user_id),
        "$or": [
            {
                "output_table": {
                    "$elemMatch": {
                        "tm_id": tm_id,
                        "$or": [
                            {"plant_start": {"$gte": day_start, "$lte": day_end}},
                            {"return": {"$gte": day_start, "$lte": day_end}},
                            # Handle case where trip spans across the day
                            {"plant_start": {"$lte": day_start}, "return": {"$gte": day_end}}
                        ]
                    }
                }
            },
            {
                "burst_table": {
                    "$elemMatch": {
                        "tm_id": tm_id,
                        "$or": [
                            {"plant_start": {"$gte": day_start, "$lte": day_end}},
                            {"return": {"$gte": day_start, "$lte": day_end}},
                            # Handle case where trip spans across the day
                            {"plant_start": {"$lte": day_start}, "return": {"$gte": day_end}}
                        ]
                    }
                }
            }
        ]
    }):
        # Check if this schedule uses burst model
        is_burst_model = schedule.get("input_params", {}).get("is_burst_model", False)
        
        # Choose the appropriate table based on is_burst_model
        trips_table = schedule.get("burst_table", []) if is_burst_model else schedule.get("output_table", [])
        
        # For each trip in this schedule that involves the TM
        for trip in trips_table:
            if trip.get("tm_id") != tm_id:
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
            
            # Make sure the trip is on this day
            if plant_start.date() > date_val or return_time.date() < date_val:
                continue
                
            # Adjust times if they span beyond this day
            if plant_start.date() < date_val:
                plant_start = day_start
                
            if return_time.date() > date_val:
                return_time = day_end
            
            # Mark all slots that overlap with this trip as "booked"
            for i, slot in enumerate(availability):
                slot_start_time = datetime.strptime(slot["start"], "%H:%M").time()
                slot_end_time = datetime.strptime(slot["end"], "%H:%M").time()
                
                slot_start_dt = datetime.combine(date_val, slot_start_time)
                slot_end_dt = datetime.combine(date_val, slot_end_time)
                
                # If this slot overlaps with the trip, mark it as booked
                if (plant_start < slot_end_dt and return_time > slot_start_dt):
                    availability[i]["status"] = "booked"
    
    return {
        "tm_id": tm.identifier,  # Use the TM identifier (registration number) instead of internal ID
        "availability": availability
    } 