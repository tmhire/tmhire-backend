from fastapi import APIRouter, Depends
from datetime import date
from app.models.user import UserModel
from app.models.schedule_calendar import DailySchedule, GanttRequest, GanttResponse, ScheduleCalendarQuery, PlantGanttResponse
from app.services.schedule_calendar_service import (
    get_calendar_for_date_range,
    get_tm_availability,
    get_gantt_data,
    get_plant_gantt_data
)
from app.services.auth_service import get_current_user
from typing import List, Dict, Any
from app.schemas.response import StandardResponse

router = APIRouter(tags=["Schedule Calendar"])

@router.post("/gantt", response_model=StandardResponse[GanttResponse])
async def get_gantt_calendar(
    query: GanttRequest,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get calendar data in Gantt chart format.
    
    Request body:
    - start_date: Beginning date for the calendar range (required)
    - end_date: End date for the calendar range (required)
    - plant_id: Optional filter for a specific plant
    - tm_id: Optional filter for a specific transit mixer
    
    Returns a list of mixers with their tasks:
    - id: Mixer ID
    - name: Mixer name
    - plant: Plant name
    - client: Current client (if any)
    - tasks: List of tasks for this mixer
        - id: Task ID
        - start: Start hour (0-23)
        - duration: Duration in hours
        - color: Task color
        - client: Client name
        - type: Task type (production, cleaning, setup, quality, maintenance)
    """
    gantt_data = await get_gantt_data(query.query_date, str(current_user.id))
    return StandardResponse(
        success=True,
        message="Gantt calendar data retrieved successfully",
        data=gantt_data
    )

@router.post("/gantt/plants", response_model=StandardResponse[PlantGanttResponse])
async def get_plant_gantt_calendar(
    query: GanttRequest,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get plant-based gantt data with hourly TM utilization.

    Request body:
    - query_date: Start of the 24-hour window (supports custom start hour)

    Returns plant rows with:
    - tm_per_hour: theoretical TM capacity per hour
    - tasks: list of load segments with TM id and metadata
    - hourly_utilization: per-hour TM count and TM ids
    """
    data = await get_plant_gantt_data(query.query_date, str(current_user.id))
    return StandardResponse(
        success=True,
        message="Plant-based gantt data retrieved successfully",
        data=data
    )

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
    - plant_id: Optional filter for a specific plant
    - tm_id: Optional filter for a specific transit mixer
    
    Returns a list of daily schedules containing:
    - date: The calendar date
    - time_slots: List of time slots with TM availability
    """
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
    """
    availability_data = await get_tm_availability(date_val, tm_id, str(current_user.id))
    return StandardResponse(
        success=True,
        message="Transit mixer availability slots retrieved successfully",
        data=availability_data
    ) 