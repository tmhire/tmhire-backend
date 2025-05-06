from fastapi import APIRouter, Depends, HTTPException, status
from app.models.transit_mixer import TransitMixerModel, TransitMixerCreate, TransitMixerUpdate, AverageCapacity
from app.models.user import UserModel
from app.services.tm_service import (
    get_all_tms, get_tm, create_tm, update_tm, delete_tm, get_average_capacity
)
from app.services.auth_service import get_current_user
from typing import List

router = APIRouter()

@router.get("/", response_model=List[TransitMixerModel])
async def read_tms(current_user: UserModel = Depends(get_current_user)):
    """Get all transit mixers for the current user"""
    return await get_all_tms(str(current_user.id))

@router.post("/", response_model=TransitMixerModel, status_code=status.HTTP_201_CREATED)
async def create_transit_mixer(
    tm: TransitMixerCreate,
    current_user: UserModel = Depends(get_current_user)
):
    """Create a new transit mixer"""
    return await create_tm(tm, str(current_user.id))

@router.get("/average-capacity", response_model=AverageCapacity)
async def read_average_capacity(current_user: UserModel = Depends(get_current_user)):
    """Get average capacity of all transit mixers for the current user"""
    avg_capacity = await get_average_capacity(str(current_user.id))
    return {"average_capacity": avg_capacity}

@router.get("/{tm_id}", response_model=TransitMixerModel)
async def read_tm(
    tm_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Get a specific transit mixer by ID"""
    tm = await get_tm(tm_id, str(current_user.id))
    if not tm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transit mixer not found"
        )
    return tm

@router.put("/{tm_id}", response_model=TransitMixerModel)
async def update_transit_mixer(
    tm_id: str,
    tm: TransitMixerUpdate,
    current_user: UserModel = Depends(get_current_user)
):
    """Update a transit mixer"""
    updated_tm = await update_tm(tm_id, tm, str(current_user.id))
    if not updated_tm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transit mixer not found"
        )
    return updated_tm

@router.delete("/{tm_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transit_mixer(
    tm_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Delete a transit mixer"""
    deleted = await delete_tm(tm_id, str(current_user.id))
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transit mixer not found"
        )
    return None 