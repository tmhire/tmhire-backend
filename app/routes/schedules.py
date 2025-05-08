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

router = APIRouter( tags=["Schedules"])

@router.get("/", response_model=List[ScheduleModel])
async def read_schedules(current_user: UserModel = Depends(get_current_user)):
    """Retrieve all schedules for the current user"""
    return await get_all_schedules(str(current_user.id))


@router.get("/{schedule_id}", response_model=ScheduleModel)
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
    return schedule


@router.put("/{schedule_id}", response_model=ScheduleModel)
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
    return updated_schedule


@router.delete("/{schedule_id}", status_code=status.HTTP_200_OK)
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
    return {
        "deleted": True,
        "schedule_id": schedule_id
    }


@router.post("/calculate-tm", response_model=Dict)
async def calculate_tm(
    schedule: ScheduleCreate,
    current_user: UserModel = Depends(get_current_user)
):
    """Calculate the required Transit Mixer count and create a draft schedule."""
    return await calculate_tm_count(schedule, str(current_user.id))


@router.post("/{schedule_id}/generate-schedule", response_model=ScheduleModel)
async def generate_schedule_endpoint(
    schedule_id: str,
    selected_tms: List[str],
    current_user: UserModel = Depends(get_current_user)
):
    """Generate the schedule based on selected Transit Mixers."""
    return await generate_schedule(schedule_id, selected_tms, str(current_user.id))
