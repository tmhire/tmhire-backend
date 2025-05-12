from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional, List
from app.db.mongodb import PyObjectId
from bson import ObjectId

class ClientModel(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    name: str
    address: str
    city: str
    state: Optional[str] = None
    postal_code: Optional[str] = None
    contact_person: str
    contact_email: Optional[EmailStr] = None
    contact_phone: str
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "name": "ABC Constructions",
                "address": "123 Main Street",
                "city": "Chennai",
                "state": "Tamil Nadu",
                "postal_code": "600001",
                "contact_person": "John Doe",
                "contact_email": "john@abcconstructions.com",
                "contact_phone": "9876543210",
                "notes": "Premium client with multiple projects"
            }
        }
    )

class ClientCreate(BaseModel):
    name: str
    address: str
    city: str
    state: Optional[str] = None
    postal_code: Optional[str] = None
    contact_person: str
    contact_email: Optional[EmailStr] = None
    contact_phone: str
    notes: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "ABC Constructions",
                "address": "123 Main Street",
                "city": "Chennai",
                "state": "Tamil Nadu",
                "postal_code": "600001",
                "contact_person": "John Doe",
                "contact_email": "john@abcconstructions.com",
                "contact_phone": "9876543210",
                "notes": "Premium client with multiple projects"
            }
        }
    )

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    notes: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "ABC Constructions Updated",
                "address": "456 New Street",
                "contact_person": "Jane Smith",
                "contact_phone": "9876543211"
            }
        }
    ) 