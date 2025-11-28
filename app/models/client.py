from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional
from app.db.mongodb import PyObjectId
from bson import ObjectId

class ClientModel(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId  # Keep for backward compatibility
    company_id: Optional[PyObjectId] = None  # Company that owns this client
    created_by: Optional[PyObjectId] = None  # User who created this client
    name: str
    legal_entity: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "name": "ABC Constructions",
                "legal_entity": "Premium client with multiple projects"
            }
        }
    )

class ClientCreate(BaseModel):
    name: str
    legal_entity: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "ABC Constructions",
                "legal_entity": "Premium client with multiple projects"
            }
        }
    )

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    legal_entity: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "ABC Constructions Updated",
                "legal_entity": "Premium client with multiple projects - Updated"
            }
        }
    ) 