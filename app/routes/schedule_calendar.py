from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import date
from app.models.user import UserModel
from app.models.schedule_calendar import DailySchedule, ScheduleCalendarQuery
from app.services.schedule_calendar_service import (
    get_calendar_for_date_range,
    get_tm_availability
)
from app.services.auth_service import get_current_user
from typing import List, Dict, Any
from app.schemas.response import StandardResponse

router = APIRouter(tags=["Schedule Calendar"])

@router.post("/", response_model=StandardResponse[List[DailySchedule]])
async def get_calendar(
    query: ScheduleCalendarQuery,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get calendar data for a date range.
    
    Request body:
    - start_date: Beginning date for the calendar range (required)
    - end_date: End date for the calendar range (required)
    - tm_id: Optional filter for a specific transit mixer
    
    Returns a list of daily schedules containing:
    - date: The calendar date
    - booked_tms: List of transit mixers that have schedules on this date
    - booked_count: Number of booked transit mixers
    - total_count: Total number of transit mixers available
    - schedules: List of schedule summaries for this date
    
    This endpoint is used to populate calendar views showing daily TM availability.
    """
    print(f"Calendar query: start_date={query.start_date}, end_date={query.end_date}")
    calendar_data = await get_calendar_for_date_range(query, str(current_user.id))
    return StandardResponse(
        success=True,
        message="Calendar data retrieved successfully",
        data=calendar_data
    )

@router.get("/tm/{tm_id}", response_model=StandardResponse[List[Dict[str, Any]]])
async def get_tm_availability_slots(
    tm_id: str,
    date_val: date,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get availability slots for a specific TM on a specific date.
    
    Path parameter:
    - tm_id: ID of the transit mixer to check
    
    Query parameter:
    - date_val: The date to check availability for (YYYY-MM-DD format)
    
    Returns a list of time slots with status information:
    - start_time: Start time of the slot
    - end_time: End time of the slot
    - status: 'available' or 'booked'
    - schedule_id: ID of the booking schedule (if booked)
    
    This endpoint is used to determine when a specific transit mixer is free or busy
    on a given date, to assist with scheduling decisions.
    """
    availability_data = await get_tm_availability(date_val, tm_id, str(current_user.id))
    return StandardResponse(
        success=True,
        message="Transit mixer availability slots retrieved successfully",
        data=availability_data
    ) 