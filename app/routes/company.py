from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from app.models.company import ChangeStatus, CompanyModel, CompanyUpdate
from app.models.user import UserModel, CompanyUserModel
from app.services.auth_service import get_current_user
from typing import List, Literal
from app.schemas.response import StandardResponse
from app.services.company_service import change_company_status, get_all_companies, get_company_by_code, get_users_from_company, update_company, get_company, get_all_users_with_company_info

router = APIRouter(tags=["Company"])

@router.get("/", response_model=StandardResponse[List[CompanyModel]])
async def get_companies():
    """Get all companies"""
    companies = await get_all_companies()
    return StandardResponse(
        success=True,
        message="Companies retrieved successfully",
        data=companies
    )

@router.get("/view/{company_primary_key}", response_model=StandardResponse[CompanyModel])
async def get_company_by_company_id(company_primary_key: str, type: Literal["company_id", "company_code"] = Query("company_id", description="Defines the type and default is company_id"), current_user: UserModel = Depends(get_current_user)):
    """Get company from company id"""
    if type == "company_id":
        company = await get_company(company_primary_key)
    elif type == "company_code":
        company = await get_company_by_code(company_primary_key)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail= "Invalid type of unique identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return StandardResponse(
        success=True,
        message="Company retrieved successfully",
        data=company
    )

@router.get("/all_users", response_model=StandardResponse[List[CompanyUserModel]])
async def get_users(current_user: UserModel = Depends(get_current_user)):
    """Get all users from company. Super admin receives all users across companies with company_code."""
    if current_user.role == "super_admin":
        users = await get_all_users_with_company_info()
    else:
        users = await get_users_from_company(current_user.company_id)

    return StandardResponse(
        success=True,
        message="Company users retrieved successfully",
        data=users
    )

@router.put("/update", response_model=StandardResponse[CompanyModel])
async def change_status(
    company_data: CompanyUpdate, 
    current_user: UserModel = Depends(get_current_user)
):
    """Change company status"""
    if current_user.role != "company_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail= "User not company admin",
            headers={"WWW-Authenticate": "Bearer"},
        )

    users = await update_company(company_data)
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

