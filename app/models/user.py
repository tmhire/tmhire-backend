from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Literal, Optional
from app.db.mongodb import PyObjectId
from bson import ObjectId

from app.models.company import CompanyModel

class CompanyAdminInfo(BaseModel):
    mail: str = ""
    phone: str = ""

class UserModel(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    email: EmailStr
    password: Optional[str] = None
    name: str
    new_user: bool = Field(default=True, description="Indicates if the user is new")
    contact: Optional[int] = Field(default=None, description="Phone number of the user")
    company_id: Optional[PyObjectId | str] = Field(default=None, description="Company that the user works for")
    role: Literal["super_admin", "company_admin", "user"] | None = None
    sub_role: Literal["viewer", "editor"] | None = None
    account_status: Literal["pending", "approved", "revoked"] | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "name": "John Doe",
                "new_user": False,
                "contact": 1234567890,
                "company_id": "{company_id}",
                "role": "user",
                "sub_role": "editor",
                "account_status": "approved",
                "created_at": datetime.utcnow()
            }
        }
    )

class UserCreate(BaseModel):
    email: EmailStr
    password: Optional[str] = None
    name: str
    new_user: bool = Field(default=True, description="Indicates if the user is new")
    contact: Optional[int] = Field(default=None, description="Phone number of the user")
    company_id: Optional[PyObjectId | str] = Field(default=None, description="Company that the user works for")
    role: Literal["super_admin", "company_admin", "user"] | None = None
    sub_role: Literal["viewer", "editor"] | None = "viewer"
    account_status: Literal["pending", "approved", "revoked"] | None = "pending"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "securepassword123",
                "name": "John Doe",
                "new_user": False,
                "contact": 1234567890,
                "company_id": "{company_id}",
                "role": "user",
                "sub_role": "editor",
                "account_status": "approved",
            }
        }
    ) 

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    password: Optional[str] = None
    contact: Optional[int] = None
    company_id: Optional[PyObjectId | str] = Field(default=None, description="Company that the user works for")
    role: Literal["super_admin", "company_admin", "user"] | None = None
    sub_role: Literal["viewer", "editor"] | None = None
    account_status: Literal["pending", "approved", "revoked"] | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "John Doe",
                "password": "newpassword123",
                "contact": 1234567890,
                "company_id": "{company_id}",
                "role": "user",
                "sub_role": "editor",
                "account_status": "approved",
            }
        }
    ) 

class CompanyUserModel(UserModel):
    company_id: Optional[PyObjectId | str] | None = None
    company_code: str = ""
    company_name: Optional[str] = Field(default="", description="Company that the user works for")
    company_status: Literal["pending", "approved", "revoked"] = "pending"
    city: Optional[str] = Field(default="", description="Location of the user")
    preferred_format: Optional[Literal["12h", "24h"]] = "24h"
    custom_start_hour: Optional[float] = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    parent_admin: Optional[CompanyAdminInfo] = None
