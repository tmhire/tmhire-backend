from bson import ObjectId
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException
from app.models.company import ChangeStatus, CompanyCreate, CompanyModel, CompanyUpdate
from app.db.mongodb import companies, users
from pymongo import ASCENDING

from app.models.user import UserModel, CompanyUserModel

async def get_all_companies() -> List[CompanyModel]:
    """Get all companies"""
    company_list = []
    async for company in companies.find().sort("company_code", ASCENDING):
        # Find the company admin for this company
        company_admin = await users.find_one({
            "company_id": ObjectId(company["_id"]),
            "role": "company_admin"
        })
        
        # Add contact from company admin if found
        if company_admin and company_admin.get("contact"):
            company["contact"] = company_admin["contact"]
        
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


async def get_all_users_with_company_info() -> List[CompanyUserModel]:
    """Get all users across companies and include company_code/name/status"""
    company_users: List[CompanyUserModel] = []
    async for u in users.find().sort("name", ASCENDING):
        user = dict(u)
        cid = user.get("company_id")
        comp = None
        if cid:
            # company_id in user doc may be an ObjectId or a string
            try:
                if isinstance(cid, ObjectId):
                    comp = await companies.find_one({"_id": cid})
                else:
                    comp = await companies.find_one({"_id": ObjectId(cid)})
            except Exception:
                comp = None

        if comp:
            user["company_code"] = comp.get("company_code") or ""
            user["company_name"] = comp.get("company_name") or ""
            user["company_status"] = comp.get("company_status") or "pending"
        else:
            user["company_code"] = ""
            user["company_name"] = ""
            user["company_status"] = "pending"

        company_users.append(CompanyUserModel(**user))

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

async def update_company(company_id: str, company: CompanyUpdate):
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
