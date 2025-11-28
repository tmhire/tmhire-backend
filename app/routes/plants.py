from fastapi import APIRouter, Depends, HTTPException, status
from app.models.plant import PlantModel, PlantCreate, PlantUpdate
from app.models.user import UserModel
from app.services.plant_service import (
    get_all_plants, get_plant, create_plant, update_plant, delete_plant, get_plant_tms
)
from app.services.auth_service import get_current_user
from typing import List, Dict
from app.schemas.response import StandardResponse

router = APIRouter(tags=["Plants"])

@router.get("/", response_model=StandardResponse[List[PlantModel]])
async def read_plants(current_user: UserModel = Depends(get_current_user)):
    """Get all plants for the current user"""
    plants = await get_all_plants(current_user)
    return StandardResponse(
        success=True,
        message="Plants retrieved successfully",
        data=plants
    )

@router.post("/", response_model=StandardResponse[PlantModel], status_code=status.HTTP_201_CREATED)
async def create_new_plant(
    plant: PlantCreate,
    current_user: UserModel = Depends(get_current_user)
):
    """Create a new plant"""
    new_plant = await create_plant(plant, current_user)
    return StandardResponse(
        success=True,
        message="Plant created successfully",
        data=new_plant
    )

@router.get("/{plant_id}", response_model=StandardResponse[PlantModel])
async def read_plant(
    plant_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Get a specific plant by ID"""
    plant = await get_plant(plant_id, current_user)
    if not plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plant not found"
        )
    return StandardResponse(
        success=True,
        message="Plant retrieved successfully",
        data=plant
    )

@router.put("/{plant_id}", response_model=StandardResponse[PlantModel])
async def update_plant_details(
    plant_id: str,
    plant: PlantUpdate,
    current_user: UserModel = Depends(get_current_user)
):
    """Update a plant"""
    updated_plant = await update_plant(plant_id, plant, current_user)
    if not updated_plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plant not found"
        )
    return StandardResponse(
        success=True,
        message="Plant updated successfully",
        data=updated_plant
    )

@router.delete("/{plant_id}", response_model=StandardResponse)
async def delete_plant_record(
    plant_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Delete a plant"""
    result = await delete_plant(plant_id, current_user)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Cannot delete plant")
        )
    return StandardResponse(
        success=True,
        message=result.get("message", "Plant deleted successfully"),
        data=None
    )

@router.get("/{plant_id}/tms", response_model=StandardResponse[Dict])
async def read_plant_transit_mixers(
    plant_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Get all transit mixers for a specific plant"""
    result = await get_plant_tms(plant_id, current_user)
    if not result["plant"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plant not found"
        )
    return StandardResponse(
        success=True,
        message="Plant transit mixers retrieved successfully",
        data=result
    )

@router.put("/{plant_id}/status", response_model=StandardResponse[PlantModel])
async def update_plant_status(
    plant_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Update the status of a plant.
    
    Path parameter:
    - plant_id: The ID of the plant to update

    Returns the updated plant details.
    """
    plant = await get_plant(plant_id, current_user)
    if not plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plant not found"
        )
    current_status = plant.status
    if current_status == "active":
        new_status = "inactive"
    else:
        new_status = "active"
    plant.status = new_status
    updated_plant = await update_plant(plant_id, plant, current_user)
    return StandardResponse(
        success=True,
        message="Transit mixer status updated successfully",
        data=updated_plant
    )