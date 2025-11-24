from bson import ObjectId
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException
from app.models.company import ChangeStatus, CompanyCreate, CompanyModel
from app.db.mongodb import companies, users
from pymongo import ASCENDING

from app.models.user import UserModel

async def get_all_companies() -> List[CompanyModel]:
    """Get all companies"""
    company_list = []
    async for company in companies.find().sort("company_code", ASCENDING):
        company_list.append(CompanyModel(**company))
    return company_list

async def get_company_by_code(company_code: str) -> Optional[CompanyModel]:
    """Get a company by code"""
    company = await companies.find_one({"company_code": company_code})
    if company:
        return CompanyModel(**company)
    return None

async def get_users_from_company(company_id: str) -> List[UserModel]:
    """Get all users from a company"""
    company_users = []
    async for user in users.find({"company_id": ObjectId(company_id)}).sort("name", ASCENDING):
        company_users.append(UserModel(**user))
    return company_users

async def get_company(id: str) -> Optional[CompanyModel]:
    """Get a company"""
    company = await companies.find_one({"_id": ObjectId(id)})
    if company:
        return CompanyModel(**company)
    return None

async def create_company(company_data: CompanyCreate) -> CompanyModel:
    """Create a new company"""
    company_data["created_at"] = datetime.utcnow()
    company_data["last_updated"] = datetime.utcnow()
    company_data["company_status"] = "pending"
    company_data["company_code"] = company_data["company_code"].upper()

    # Check if company already exists
    existing_company = await get_company_by_code(company_data["company_code"])
    if existing_company:
        print("Company already exists")
        raise HTTPException(status_code=400, detail="Company already exists")
    
    # Insert new company
    result = await companies.insert_one(company_data)
    new_company = await companies.find_one({"_id": result.inserted_id})
    return CompanyModel(**new_company)

async def update_company(company_id: str, company: CompanyCreate):
    """Update a company"""
    company_data = {k: v for k, v in company.model_dump().items() if v is not None}

    existing_company = (await get_company(company_id)).model_dump()
    if not existing_company:
        print("Company does not exist")
        raise HTTPException(status_code=400, detail="Company does not exist")

    updated_company = {**existing_company, **company_data}

    #Update company
    await companies.update_one(
        {"_id": ObjectId(company_id)},
        {"$set": updated_company}
    )
    
    return await get_company(company_id)

async def change_company_status(company: ChangeStatus):
    """Update a company"""
    company_data = {k: v for k, v in company.model_dump().items() if v is not None}

    company_id = company_data["company_id"]

    existing_company = (await get_company(company_id)).model_dump()
    if not existing_company:
        print("Company does not exist")
        raise HTTPException(status_code=400, detail="Company does not exist")

    updated_company = {**existing_company, "company_status": company_data["company_status"]}

    #Update company
    await companies.update_one(
        {"_id": ObjectId(company_id)},
        {"$set": updated_company}
    )
    
    return await get_company(company_id)
