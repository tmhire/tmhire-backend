from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.models.pump import PumpModel, PumpCreate, PumpUpdate, AveragePumpCapacity
from app.models.user import UserModel
from app.services.pump_service import (
    get_all_pumps, get_pump, create_pump, update_pump, delete_pump, get_pumps_by_plant, get_pump_gantt_data
)
from app.services.auth_service import get_current_user
from app.schemas.response import StandardResponse
from app.models.schedule_calendar import GanttRequest, PumpGanttResponse

router = APIRouter(tags=["Pumps"])

@router.get("/", response_model=StandardResponse[List[PumpModel]])
async def read_pumps(current_user: UserModel = Depends(get_current_user)):
    """
    Retrieve all pumps for the current user.
    """
    pumps = await get_all_pumps(str(current_user.id))
    return StandardResponse(
        success=True,
        message="Pumps retrieved successfully",
        data=pumps
    )

@router.get("/{pump_id}", response_model=StandardResponse[PumpModel])
async def read_pump(
    pump_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Retrieve a specific pump by ID.
    """
    pump = await get_pump(pump_id, str(current_user.id))
    if not pump:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pump not found"
        )
    return StandardResponse(
        success=True,
        message="Pump retrieved successfully",
        data=pump
    )

@router.post("/", response_model=StandardResponse[PumpModel], status_code=status.HTTP_201_CREATED)
async def create_new_pump(
    pump: PumpCreate,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Create a new pump.
    """
    new_pump = await create_pump(pump, str(current_user.id))
    return StandardResponse(
        success=True,
        message="Pump created successfully",
        data=new_pump
    )

@router.put("/{pump_id}", response_model=StandardResponse[PumpModel])
async def update_existing_pump(
    pump_id: str,
    pump: PumpUpdate,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Update an existing pump.
    """
    updated_pump = await update_pump(pump_id, pump, str(current_user.id))
    if not updated_pump:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pump not found"
        )
    return StandardResponse(
        success=True,
        message="Pump updated successfully",
        data=updated_pump
    )

@router.delete("/{pump_id}", response_model=StandardResponse[None])
async def delete_existing_pump(
    pump_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Delete a pump.
    """
    deleted = await delete_pump(pump_id, str(current_user.id))
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pump not found"
        )
    return StandardResponse(
        success=True,
        message="Pump deleted successfully",
        data=None
    )

@router.get("/by-plant/{plant_id}", response_model=StandardResponse[List[PumpModel]])
async def get_pumps_for_plant(
    plant_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get all pumps for a specific plant.
    """
    pumps = await get_pumps_by_plant(plant_id, str(current_user.id))
    return StandardResponse(
        success=True,
        message="Pumps for plant retrieved successfully",
        data=pumps
    )

# @router.post("/gantt", response_model=StandardResponse[PumpGanttResponse])
# async def get_pump_gantt_calendar(
#     query: GanttRequest,
#     current_user: UserModel = Depends(get_current_user)
# ):
#     """
#     Get Gantt chart data for all pumps for a given date.
#     """
#     gantt_data = await get_pump_gantt_data(query.query_date, str(current_user.id))
#     return StandardResponse(
#         success=True,
#         message="Pump Gantt calendar data retrieved successfully",
#         data=PumpGanttResponse(pumps=gantt_data)
#     )
