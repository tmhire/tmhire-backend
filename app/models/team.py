from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Optional
from app.db.mongodb import PyObjectId
from bson import ObjectId

class TeamMemberModel(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId  # Keep for backward compatibility
    company_id: Optional[PyObjectId] = None  # Company that owns this team member
    created_by: Optional[PyObjectId] = None  # User who created this team member
    name: str
    designation: Literal["sales-engineer", "pump-operator", "pipeline-gang", "site-supervisor", "field-technician"]
    contact: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "user_id": "507f1f77bcf86cd799439012",
                "name": "John Doe",
                "designation": "sales-engineer",
                "contact": 9876543210,
                "created_at": "2023-10-01T12:00:00Z"
            }
        }
    )

class TeamMemberCreate(BaseModel):
    name: str
    designation: Literal["sales-engineer", "pump-operator", "pipeline-gang", "site-supervisor", "field-technician"]
    contact: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "John Doe",
                "designation": "sales-engineer",
                "contact": 9876543210,
            }
        }
    )

class TeamMemberUpdate(BaseModel):
    name: Optional[str] = None
    designation: Optional[Literal["sales-engineer", "pump-operator", "pipeline-gang", "site-supervisor"]] = None
    contact: Optional[int] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Updated Team Member Name",
                "designation": "sales-engineer",
                "contact": 9876543210,
            }
        }
    )