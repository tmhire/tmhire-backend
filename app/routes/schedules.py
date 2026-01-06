from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Dict, Any, Optional, Union
from datetime import date, datetime

from pydantic import BaseModel
from app.models.schedule import CancelReason, Cancelation, CanceledBy, DeleteType, GenerateScheduleBody, GetScheduleResponse, ScheduleCreate, ScheduleModel, ScheduleType, ScheduleUpdate
from app.models.user import UserModel
from app.services.schedule_service import (
    get_all_schedules,
    get_schedule,
    keep_first_and_last_trip,
    update_schedule,
    delete_schedule,
    create_schedule_draft,
    generate_schedule,
    get_daily_schedule,
    toggle_burst_model
)
from app.services.auth_service import get_current_user
from app.schemas.response import StandardResponse
from app.schemas.utils import safe_serialize

router = APIRouter(tags=["Schedules"])

@router.get("/", response_model=StandardResponse[List[ScheduleModel]])
async def read_schedules(
    type: ScheduleType = Query(ScheduleType.pumping, description="Filter schedules by type: 'supply' or 'pumping'"),
    current_user: UserModel = Depends(get_current_user)
):
    """Get all schedules for the current user"""
    schedules = await get_all_schedules(current_user=current_user, type=type)
    
    schedules = keep_first_and_last_trip(schedules=schedules)
    
    # Safely serialize to handle any date/datetime objects
    schedule_list = [schedule.model_dump() for schedule in schedules]
    safe_data = safe_serialize(schedule_list)
    
    return StandardResponse(
        success=True,
        message="Schedules retrieved successfully",
        data=safe_data
    )

@router.get("/reports", response_model=StandardResponse[List[ScheduleModel]])
async def read_schedules(
    type: ScheduleType = Query(ScheduleType.all, description="Filter schedules by type: 'supply' or 'pumping'"),
    from_date: Union[date, str] = Query(datetime.now().date(), description="Filter schedules by from date"),
    to_date: Union[date, str] = Query(datetime.now().date(), description="Filter schedules by to date"),
    current_user: UserModel = Depends(get_current_user)
):
    """Get all schedules for the current user"""
    if not to_date:
        to_date = from_date

    schedules = await get_all_schedules(current_user=current_user, type=type, from_date=from_date, to_date=to_date, isFromReports=True)
        
    # Safely serialize to handle any date/datetime objects
    schedule_list = [schedule.model_dump() for schedule in schedules]
    safe_data = safe_serialize(schedule_list)
    
    return StandardResponse(
        success=True,
        message="Schedules retrieved successfully",
        data=safe_data
    )

@router.get("/daily", response_model=StandardResponse[List[Dict[str, Any]]])
async def read_daily_schedule(
    date: date = Query(..., description="Date in YYYY-MM-DD format"),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Retrieve all scheduled trips for a specific date, grouped by transit mixer.
    
    Query parameters:
    - date: The date in YYYY-MM-DD format
    
    Returns a Gantt-chart friendly array of TM schedules for the day.
    Each TM has an array of trips with their start/end times and client info.
    """
    daily_schedule = await get_daily_schedule(date, current_user)
    
    # Safely serialize to handle any date/datetime objects
    safe_data = safe_serialize(daily_schedule)
    
    return StandardResponse(
        success=True,
        message="Daily schedule retrieved successfully",
        data=safe_data
    )

@router.get("/{schedule_id}", response_model=StandardResponse[GetScheduleResponse])
async def read_schedule(
    schedule_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Get a schedule by ID"""
    if schedule_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Schedule ID is required"
        )
    schedule = await get_schedule(schedule_id, current_user)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    
    # Safely serialize to handle any date/datetime objects
    safe_data = safe_serialize(schedule.model_dump())
    
    return StandardResponse(
        success=True,
        message="Schedule retrieved successfully",
        data=safe_data
    )

@router.post("/", response_model=StandardResponse[ScheduleModel])
async def create_schedule(
    schedule: ScheduleCreate,
    current_user: UserModel = Depends(get_current_user)
):
    """Create a new schedule. Requires both client_id and project_id."""
    if not schedule.project_id or not schedule.client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both project_id and client_id are required to create a schedule."
        )
    result = await create_schedule_draft(schedule, current_user)
    return StandardResponse(
        success=True,
        message="Transit mixer count calculated successfully",
        data=result
    )

@router.put("/{schedule_id}", response_model=StandardResponse[GetScheduleResponse])
async def update_existing_schedule(
    schedule_id: str,
    schedule: ScheduleUpdate,
    current_user: UserModel = Depends(get_current_user)
):
    """Update a schedule by ID. Requires both client_id and project_id if updating project."""
    if schedule.project_id and not schedule.client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="client_id is required when updating project_id."
        )
    updated_schedule = await update_schedule(schedule_id, schedule, current_user)
    if not updated_schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    
    # Safely serialize to handle any date/datetime objects
    safe_data = safe_serialize(updated_schedule.model_dump())
    
    return StandardResponse(
        success=True,
        message="Schedule updated successfully",
        data=safe_data
    )

@router.put("/{schedule_id}/toggle-burst-model", response_model=StandardResponse[GetScheduleResponse])
async def toggle_schedule_burst_model(
    schedule_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Toggle the is_burst_model flag for a schedule by ID."""
    updated_schedule = await toggle_burst_model(schedule_id, current_user)
    if not updated_schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    
    # Safely serialize to handle any date/datetime objects
    safe_data = safe_serialize(updated_schedule.model_dump())
    
    return StandardResponse(
        success=True,
        message="Burst model toggled successfully",
        data=safe_data
    )

@router.delete("/{schedule_id}", response_model=StandardResponse, status_code=status.HTTP_200_OK)
async def delete_existing_schedule(
    schedule_id: str,
    delete_type: DeleteType = Query(DeleteType.permanent, description="Specify 'permanently' to delete permanently or 'temporarily' to soft delete"),
    canceled_by: CanceledBy = Query(CanceledBy.client, description="Specify who is canceling: 'client' or 'company'"),
    cancel_reason: CancelReason = Query(CancelReason.ecl, description="Specify 'permanently' to delete permanently or 'temporarily' to soft delete"),
    current_user: UserModel = Depends(get_current_user)
):
    print(cancel_reason)
    """Delete a schedule by ID"""
    result = await delete_schedule(
        id=schedule_id, 
        delete_type=delete_type, 
        cancelation={ "canceled_by": canceled_by, "reason": cancel_reason }, 
        current_user=current_user
    )
    
    type = "canceled" if delete_type == DeleteType.cancel else "deleted"
    if type not in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    return StandardResponse(
        success=True,
        message="Schedule deleted successfully",
        data={"schedule_id": schedule_id}
    )

# @router.post("/calculate-tm", response_model=StandardResponse[Dict])
# async def calculate_tm(
#     schedule: CalculateTM,
#     current_user: UserModel = Depends(get_current_user)
# ):
#     """
#     Calculate the required Transit Mixer count and create a draft schedule.
    
#     Request body:
#     - client_id: ID of the client for this schedule
#     - client_name: Name of the client (optional if client_id is provided)
#     - site_address: Location of the construction site
#     - input_params: Contains scheduling parameters including:
#       - quantity: Total concrete quantity needed (in cubic meters)
#       - pumping_speed: Concrete pumping speed (cubic meters per hour)
#       - onward_time: Travel time from plant to site (minutes)
#       - return_time: Travel time from site back to plant (minutes)
#       - buffer_time: Buffer time between trips (minutes)
#       - load_time: Loading time between trips (minutes)
#       - pump_start: When pumping should start (datetime)
#       - schedule_date: Date for the schedule (date)
    
#     Returns:
#     - schedule_id: ID of the created draft schedule
#     - tm_count: Number of transit mixers required
#     - tm_identifiers: List of transit mixer identifiers (A, B, C, ...)
#     """
#     result = await create_schedule_draft(schedule, current_user)
#     return StandardResponse(
#         success=True,
#         message="Transit mixer count calculated successfully",
#         data=result
#     )

@router.post("/{schedule_id}/generate-schedule", response_model=StandardResponse[GetScheduleResponse])
async def generate_schedule_endpoint(
    schedule_id: str,
    body: GenerateScheduleBody,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Generate a detailed schedule with assigned TMs and optimized trips.
    
    Path Parameter:
    - schedule_id: ID of the draft schedule to generate
    
    Request Body:
    - selected_tms: List of TM IDs to use for this schedule
    
    Returns the generated schedule with its output table of trips.
    Each trip includes TM assignment, timings, and concrete volumes.
    """
    try:
        selected_tms = body.selected_tms
        if not selected_tms or not isinstance(selected_tms, list):
            raise ValueError("selected_tms must be a non-empty list of TM IDs")
        
        pump_id = body.pump
        if pump_id is None and body.type == "pumping":
            raise ValueError("pump ID is required to generate the schedule")

        schedule = await generate_schedule(
            schedule_id=schedule_id, 
            selected_tms=selected_tms, 
            pump_id=pump_id, 
            current_user=current_user, 
            type=body.type, 
            partially_available_tm=body.partially_available_tm, 
            partially_available_pump=body.partially_available_pump
        )
        
        # Convert the schedule to a dict for safer serialization
        schedule_dict = {}
        if schedule:
            # Use the model's own serialization method first
            schedule_dict = schedule.model_dump()
            
            # Additional processing for trip datetime fields if needed
            if "output_table" in schedule_dict:
                for trip in schedule_dict["output_table"]:
                    for field in ["plant_start", "pump_start", "unloading_time", "return"]:
                        if field in trip and hasattr(trip[field], "isoformat"):
                            trip[field] = trip[field].isoformat()
        
        # Safely serialize to handle any date/datetime objects
        safe_data = safe_serialize(schedule_dict)
        
        return StandardResponse(
            success=True,
            message="Schedule generated successfully",
            data=safe_data
        )
    except ValueError as e:
        # This will handle cases like "Schedule not found" or TM availability errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
