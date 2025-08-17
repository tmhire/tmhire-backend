from fastapi import APIRouter, Depends, HTTPException, status
from app.models.team import TeamMemberModel, TeamMemberCreate, TeamMemberUpdate
from app.models.user import UserModel
from app.services.team_service import (
    get_all_teams, get_team_member, create_team_member, update_team_member, delete_team_member
)
from app.services.auth_service import get_current_user
from typing import List
from app.schemas.response import StandardResponse

router = APIRouter(tags=["Team Members"])

@router.get("/", response_model=StandardResponse[List[TeamMemberModel]])
async def read_teams(current_user: UserModel = Depends(get_current_user)):
    """Get all team members for the current user"""
    teams = await get_all_teams(str(current_user.id))
    return StandardResponse(
        success=True,
        message="Team members retrieved successfully",
        data=teams
    )

@router.post("/", response_model=StandardResponse[TeamMemberModel], status_code=status.HTTP_201_CREATED)
async def create_new_team_member(
    member: TeamMemberCreate,
    current_user: UserModel = Depends(get_current_user)
):
    """Create a new team member"""
    new_member = await create_team_member(member, str(current_user.id))
    return StandardResponse(
        success=True,
        message="Team member created successfully",
        data=new_member
    )

@router.get("/{member_id}", response_model=StandardResponse[TeamMemberModel])
async def read_team_member(
    member_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Get a specific team member by ID"""
    member = await get_team_member(member_id, str(current_user.id))
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found"
        )
    return StandardResponse(
        success=True,
        message="Team member retrieved successfully",
        data=member
    )

@router.put("/{member_id}", response_model=StandardResponse[TeamMemberModel])
async def update_team(
    member_id: str,
    member: TeamMemberUpdate,
    current_user: UserModel = Depends(get_current_user)
):
    """Update a team member"""
    updated_member = await update_team_member(member_id, member, str(current_user.id))
    if not updated_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found"
        )
    return StandardResponse(
        success=True,
        message="Team member updated successfully",
        data=updated_member
    )

@router.delete("/{member_id}", response_model=StandardResponse)
async def delete_team(
    member_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Delete a team member"""
    result = await delete_team_member(member_id, str(current_user.id))
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Cannot delete team member")
        )
    return StandardResponse(
        success=True,
        message=result.get("message", "Team member deleted successfully"),
        data=None
    )
