from fastapi import APIRouter, Depends
from app.models.company import CompanyModel
from app.models.user import UserModel
from app.services.auth_service import get_current_user
from typing import List
from app.schemas.response import StandardResponse
from app.services.company_service import get_all_companies

router = APIRouter(tags=["Company"])

@router.get("/", response_model=StandardResponse[List[CompanyModel]])
async def read_teams(current_user: UserModel = Depends(get_current_user)):
    """Get all team members for the current user"""
    teams = await get_all_companies()
    return StandardResponse(
        success=True,
        message="Team members retrieved successfully",
        data=teams
    )