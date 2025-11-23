from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.models.company import ChangeStatus, CompanyModel
from app.models.user import UserModel
from app.services.auth_service import get_current_user
from typing import List, Literal
from app.schemas.response import StandardResponse
from app.services.company_service import change_company_status, get_all_companies, get_users_from_company, update_company

router = APIRouter(tags=["Company"])

@router.get("/", response_model=StandardResponse[List[CompanyModel]])
async def get_companies(current_user: UserModel = Depends(get_current_user)):
    """Get all companies"""
    companies = await get_all_companies()
    return StandardResponse(
        success=True,
        message="Companies retrieved successfully",
        data=companies
    )

@router.get("/all_users", response_model=StandardResponse[List[UserModel]])
async def get_users(current_user: UserModel = Depends(get_current_user)):
    """Get all users from company"""
    users = await get_users_from_company(current_user.company_id)
    return StandardResponse(
        success=True,
        message="Company users retrieved successfully",
        data=users
    )

@router.put("/change_status", response_model=StandardResponse[CompanyModel])
async def change_status(company_data: ChangeStatus, current_user: UserModel = Depends(get_current_user)):
    """Change company status"""
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail= "User not super admin",
            headers={"WWW-Authenticate": "Bearer"},
        )

    users = await change_company_status(company_data)
    return StandardResponse(
        success=True,
        message="Company users retrieved successfully",
        data=users
    )

