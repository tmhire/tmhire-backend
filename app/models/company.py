from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Optional
from app.db.mongodb import PyObjectId
from bson import ObjectId

class CompanyModel(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    company_code: str
    company_name: Optional[str] = Field(default=None, description="Company that the user works for")
    company_status: Literal["pending", "approved", "revoked"]
    city: Optional[str] = Field(default=None, description="Location of the user")
    preferred_format: Optional[Literal["12h", "24h"]] = "24h"
    custom_start_hour: Optional[float] = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "id": "60d5ec9af682fcd81a060e72",
                "company_code": "MCF",
                "company_name": "Main Concrete Firm",
                "company_status": False,
                "city": "Coimbatore",
                "preferred_format": "24h",
                "custom_start_hour": 0.0,
                "created_at": datetime.utcnow()
            }
        }
    )

class CompanyCreate(BaseModel):
    role: Literal["company_admin", "user"]
    id: str | None = None
    company_code: str | None = None
    company_name: str | None = None
    company_status: Literal["pending", "approved", "revoked"] | None = None
    city: str | None = None
    contact: str | None = None
    preferred_format: Literal["12h", "24h"] = "24h"
    custom_start_hour: float = 0.0

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "role": "company_admin",
                "company_code": "MCF",
                "contact": "1234567890",
                "company_name": "Main Concrete Firm",
                "company_status": False,
                "city": "Coimbatore",
                "preferred_format": "24h",
                "custom_start_hour": 0.0,
            }
        }
    )

class CompanyUpdate(BaseModel):
    company_code: str | None = None
    company_name: str | None = None
    company_status: Literal["pending", "approved", "revoked"] | None = None
    city: str | None = None
    preferred_format: Literal["12h", "24h"] = "24h"
    custom_start_hour: float = 0.0

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "company_code": "MCF",
                "company_name": "Main Concrete Firm",
                "company_status": False,
                "city": "Coimbatore",
                "preferred_format": "24h",
                "custom_start_hour": 0.0,
            }
        }
    )


class ChangeStatus(BaseModel):
    company_id: str
    company_status: Literal["approved", "revoked"]