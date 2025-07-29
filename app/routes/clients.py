from fastapi import APIRouter, Depends, HTTPException, status
from app.models.client import ClientModel, ClientCreate, ClientUpdate
from app.models.user import UserModel
from app.services.client_service import (
    get_all_clients, get_client, create_client, update_client, delete_client, get_client_schedules, get_client_stats
)
from app.services.auth_service import get_current_user
from typing import List, Dict, Any
from app.schemas.response import StandardResponse

router = APIRouter(tags=["Clients"])

@router.get("/", response_model=StandardResponse[List[ClientModel]])
async def read_clients(current_user: UserModel = Depends(get_current_user)):
    """
    Retrieve all clients for the current user.
    
    Returns a list of all clients belonging to the authenticated user.
    """
    clients = await get_all_clients(str(current_user.id))
    return StandardResponse(
        success=True,
        message="Clients retrieved successfully",
        data=clients
    )

@router.post("/", response_model=StandardResponse[ClientModel], status_code=status.HTTP_201_CREATED)
async def create_new_client(
    client: ClientCreate,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Create a new client.
    
    Requires client details in the request body.
    Returns the newly created client with its ID.
    """
    new_client = await create_client(client, str(current_user.id))
    return StandardResponse(
        success=True,
        message="Client created successfully",
        data=new_client
    )

@router.get("/{client_id}", response_model=StandardResponse[ClientModel])
async def read_client(
    client_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Retrieve a specific client by ID.
    
    Path parameter:
    - client_id: The ID of the client to retrieve
    
    Returns the client details if found.
    """
    client = await get_client(client_id, str(current_user.id))
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    return StandardResponse(
        success=True,
        message="Client retrieved successfully",
        data=client
    )

@router.put("/{client_id}", response_model=StandardResponse[ClientModel])
async def update_client_details(
    client_id: str,
    client: ClientUpdate,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Update a client's details.
    
    Path parameter:
    - client_id: The ID of the client to update
    
    Request body:
    - Updated client fields (only fields to be updated need to be included)
    
    Returns the updated client details.
    """
    updated_client = await update_client(client_id, client, str(current_user.id))
    if not updated_client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    return StandardResponse(
        success=True,
        message="Client updated successfully",
        data=updated_client
    )

@router.delete("/{client_id}", response_model=StandardResponse)
async def delete_client_record(
    client_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Delete a client.
    
    Path parameter:
    - client_id: The ID of the client to delete
    
    Returns a success status and message. Will not delete clients that have associated schedules.
    """
    result = await delete_client(client_id, str(current_user.id))
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    return StandardResponse(
        success=True,
        message=result["message"],
        data=None
    )

@router.get("/{client_id}/schedules", response_model=StandardResponse[Dict])
async def read_client_schedules(
    client_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Retrieve all schedules for a specific client.
    
    Path parameter:
    - client_id: The ID of the client
    
    Returns the client details along with all their associated schedules.
    """
    result = await get_client_schedules(client_id, str(current_user.id))
    if not result["client"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    return StandardResponse(
        success=True,
        message="Client schedules retrieved successfully",
        data=result
    )

@router.get("/{client_id}/stats", response_model=StandardResponse[Dict[str, Any]])
async def read_client_stats(
    client_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Retrieve statistics for a specific client.
    
    Path parameter:
    - client_id: The ID of the client
    
    Returns statistics including:
    - Total scheduled volume
    - Total delivered volume
    - Pending delivery volume
    - Recent trip summaries
    """    
    stats = await get_client_stats(client_id, str(current_user.id))
    return StandardResponse(
        success=True,
        message="Client statistics retrieved successfully",
        data=stats
    ) 