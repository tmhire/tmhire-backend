from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional, Dict
from app.models.schedule import ScheduleModel, ScheduleCreate, ScheduleUpdate
from app.models.user import UserModel
from app.services.schedule_service import (
    get_all_schedules,
    get_schedule,
    update_schedule,
    delete_schedule,
    calculate_tm_count,
    generate_schedule
)
from app.services.auth_service import get_current_user
from app.schemas.response import StandardResponse

router = APIRouter(tags=["Schedules"])

@router.get("/", response_model=StandardResponse[List[ScheduleModel]])
async def read_schedules(current_user: UserModel = Depends(get_current_user)):
    """Retrieve all schedules for the current user"""
    schedules = await get_all_schedules(str(current_user.id))
    return StandardResponse(
        success=True,
        message="Schedules retrieved successfully",
        data=schedules
    )


@router.get("/{schedule_id}", response_model=StandardResponse[ScheduleModel])
async def read_schedule(
    schedule_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Get details of a specific schedule by ID"""
    schedule = await get_schedule(schedule_id, str(current_user.id))
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    return StandardResponse(
        success=True,
        message="Schedule retrieved successfully",
        data=schedule
    )


@router.put("/{schedule_id}", response_model=StandardResponse[ScheduleModel])
async def update_existing_schedule(
    schedule_id: str,
    schedule: ScheduleUpdate,
    current_user: UserModel = Depends(get_current_user)
):
    """Update a schedule by ID"""
    updated_schedule = await update_schedule(schedule_id, schedule, str(current_user.id))
    if not updated_schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found or no changes detected"
        )
    return StandardResponse(
        success=True,
        message="Schedule updated successfully",
        data=updated_schedule
    )


@router.delete("/{schedule_id}", response_model=StandardResponse, status_code=status.HTTP_200_OK)
async def delete_existing_schedule(
    schedule_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Delete a schedule by ID"""
    result = await delete_schedule(schedule_id, str(current_user.id))
    if not result["deleted"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    return StandardResponse(
        success=True,
        message="Schedule deleted successfully",
        data={"schedule_id": schedule_id}
    )


@router.post("/calculate-tm", response_model=StandardResponse[Dict])
async def calculate_tm(
    schedule: ScheduleCreate,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Calculate the required Transit Mixer count and create a draft schedule.
    
    Request body:
    - client_id: ID of the client for this schedule
    - client_name: Name of the client (optional if client_id is provided)
    - site_location: Location of the construction site
    - input_params: Contains scheduling parameters including:
      - quantity: Total concrete quantity needed (in cubic meters)
      - pumping_speed: Concrete pumping speed (cubic meters per hour)
      - onward_time: Travel time from plant to site (minutes)
      - return_time: Travel time from site back to plant (minutes)
      - buffer_time: Buffer time between trips (minutes)
      - pump_start: When pumping should start (datetime)
      - schedule_date: Date for the schedule (date)
    
    Returns:
    - schedule_id: ID of the created draft schedule
    - tm_count: Number of transit mixers required
    - tm_identifiers: List of transit mixer identifiers (A, B, C, ...)
    """
    result = await calculate_tm_count(schedule, str(current_user.id))
    return StandardResponse(
        success=True,
        message="Transit mixer count calculated successfully",
        data=result
    )


@router.post("/{schedule_id}/generate-schedule", response_model=StandardResponse[ScheduleModel])
async def generate_schedule_endpoint(
    schedule_id: str,
    selected_tms: List[str],
    current_user: UserModel = Depends(get_current_user)
):
    """
    Generate the detailed schedule based on selected Transit Mixers.
    
    Path parameter:
    - schedule_id: ID of the draft schedule to generate
    
    Request body:
    - selected_tms: List of transit mixer IDs to use for this schedule
    
    The function checks TM availability, optimizes the schedule based on TM capacity,
    and returns a complete schedule with trip details including departure/arrival times.
    
    Returns the complete schedule model with output_table containing all trips.
    Each trip includes:
    - trip_no: Trip number
    - tm_no: Transit mixer identifier
    - tm_id: Transit mixer ID
    - plant_start: Departure time from plant
    - pump_start: Arrival time at site
    - unloading_time: Estimated completion time for unloading
    - return: Estimated return time to plant
    - completed_capacity: Cumulative capacity delivered
    """
    result = await generate_schedule(schedule_id, selected_tms, str(current_user.id))
    return StandardResponse(
        success=True,
        message="Schedule generated successfully",
        data=result
    )
