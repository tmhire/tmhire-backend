from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.models.transit_mixer import TransitMixerModel, TransitMixerCreate, TransitMixerUpdate, AverageCapacity
from app.models.user import UserModel
from app.services.tm_service import (
    get_all_tms, get_tm, create_tm, update_tm, delete_tm, get_average_capacity,
    get_available_tms, get_tm_availability_slots
)
from app.services.auth_service import get_current_user
from typing import List, Dict, Any
from app.schemas.response import StandardResponse
from datetime import date, datetime
from app.schemas.utils import safe_serialize

router = APIRouter(tags=["Transit Mixers"])

@router.get("/", response_model=StandardResponse[List[TransitMixerModel]])
async def read_tms(current_user: UserModel = Depends(get_current_user)):
    """
    Retrieve all transit mixers for the current user.
    
    Returns a list of all transit mixers with their details including capacity,
    identifier, and plant association.
    """
    tms = await get_all_tms(str(current_user.id))
    return StandardResponse(
        success=True,
        message="Transit mixers retrieved successfully",
        data=tms
    )

@router.post("/", response_model=StandardResponse[TransitMixerModel], status_code=status.HTTP_201_CREATED)
async def create_transit_mixer(
    tm: TransitMixerCreate,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Create a new transit mixer.
    
    Request body:
    - identifier: Unique identifier for the transit mixer
    - capacity: Concrete capacity in cubic meters
    - plant_id: ID of the plant this transit mixer belongs to (optional)
    - notes: Additional notes about this transit mixer (optional)
    
    Returns the newly created transit mixer with its ID.
    """
    new_tm = await create_tm(tm, str(current_user.id))
    return StandardResponse(
        success=True,
        message="Transit mixer created successfully",
        data=new_tm
    )

@router.get("/average-capacity", response_model=StandardResponse[AverageCapacity])
async def read_average_capacity(current_user: UserModel = Depends(get_current_user)):
    """
    Get average capacity of all transit mixers for the current user.
    
    Returns a single value representing the average capacity across all
    transit mixers owned by the user.
    """
    avg_capacity = await get_average_capacity(str(current_user.id))
    return StandardResponse(
        success=True,
        message="Average capacity retrieved successfully",
        data={"average_capacity": avg_capacity}
    )

@router.get("/available", response_model=StandardResponse[List[TransitMixerModel]])
async def read_available_tms(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Retrieve all transit mixers available on the specified date.
    
    Query parameter:
    - date: The date in YYYY-MM-DD format to check for availability
    
    Returns a list of all available transit mixers on the specified date.
    """
    try:
        # Convert string date to datetime.date object
        parsed_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        # Get available TMs
        tms = await get_available_tms(parsed_date, str(current_user.id))
        
        # Convert to dict for safer serialization
        tm_list = [tm.model_dump() for tm in tms]
        
        # Convert any date/datetime objects in the result to strings
        safe_data = safe_serialize(tm_list)
        
        return StandardResponse(
            success=True,
            message="Available transit mixers retrieved successfully",
            data=safe_data
        )
    except Exception as e:
        # Log the error for debugging
        import logging
        logging.error(f"Error in read_available_tms: {str(e)}")
        
        # Return a more specific error message
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve available transit mixers: {str(e)}"
        )

@router.get("/{tm_id}", response_model=StandardResponse[TransitMixerModel])
async def read_tm(
    tm_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Retrieve a specific transit mixer by ID.
    
    Path parameter:
    - tm_id: The ID of the transit mixer to retrieve
    
    Returns the transit mixer details if found.
    """
    tm = await get_tm(tm_id, str(current_user.id))
    if not tm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transit mixer not found"
        )
    return StandardResponse(
        success=True,
        message="Transit mixer retrieved successfully",
        data=tm
    )

@router.put("/{tm_id}", response_model=StandardResponse[TransitMixerModel])
async def update_transit_mixer(
    tm_id: str,
    tm: TransitMixerUpdate,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Update a transit mixer's details.
    
    Path parameter:
    - tm_id: The ID of the transit mixer to update
    
    Request body:
    - identifier: Updated identifier (optional)
    - capacity: Updated capacity in cubic meters (optional)
    - plant_id: Updated plant association (optional)
    - notes: Updated notes (optional)
    
    Returns the updated transit mixer details.
    """
    updated_tm = await update_tm(tm_id, tm, str(current_user.id))
    if not updated_tm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transit mixer not found"
        )
    return StandardResponse(
        success=True,
        message="Transit mixer updated successfully",
        data=updated_tm
    )

@router.delete("/{tm_id}", response_model=StandardResponse, status_code=status.HTTP_200_OK)
async def delete_transit_mixer(
    tm_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Delete a transit mixer.
    
    Path parameter:
    - tm_id: The ID of the transit mixer to delete
    
    Returns a success message on successful deletion.
    """
    deleted = await delete_tm(tm_id, str(current_user.id))
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transit mixer not found"
        )
    return StandardResponse(
        success=True,
        message="Transit mixer deleted successfully",
        data=None
    )

@router.get("/{tm_id}/availability", response_model=StandardResponse[Dict[str, Any]])
async def read_tm_availability(
    tm_id: str,
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get availability information for a TM on a specific date in 30-minute intervals.
    
    Path parameter:
    - tm_id: The ID of the transit mixer
    
    Query parameter:
    - date: The date in YYYY-MM-DD format to check availability
    
    Returns the TM ID and an array of 30-minute slots with their booking status.
    Each slot includes start time, end time, and status (available or booked).
    """
    try:
        # Parse date string
        parsed_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        tm = await get_tm(tm_id, str(current_user.id))
        if not tm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transit mixer not found"
            )
        
        availability_data = await get_tm_availability_slots(tm_id, parsed_date, str(current_user.id))
        
        # Convert any date/datetime objects in the result to strings for safe serialization
        safe_data = safe_serialize(availability_data)
        
        return StandardResponse(
            success=True,
            message="Transit mixer availability retrieved successfully",
            data=safe_data
        )
    except Exception as e:
        # Log the error for debugging
        import logging
        logging.error(f"Error in read_tm_availability: {str(e)}")
        
        # Return a more specific error message
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve transit mixer availability: {str(e)}"
        ) 