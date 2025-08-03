from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from app.db.mongodb import PyObjectId
from bson import ObjectId

class ProjectModel(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    client_id: PyObjectId
    name: str
    address: Optional[str] = None
    coordinates: Optional[str] = None
    contact_name: Optional[str] = None
    contact_number: Optional[str] = None
    remarks: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "client_id": "688872706e3053d0211f0015",
                "name": "John Doe Construction Project",
                "address": "123 Main Street, City",
                "coordinates": "https://maps.google.com/?q=12.9715987,77.594566",
                "contact_name": "John Doe",
                "contact_number": "9876543210",
                "remarks": "Initial project setup",
            }
        }
    )

class ProjectCreate(BaseModel):
    client_id: PyObjectId
    name: str
    address: Optional[str] = None
    coordinates: Optional[str] = None
    contact_name: Optional[str] = None
    contact_number: Optional[str] = None
    remarks: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "client_id": "688872706e3053d0211f0015",
                "name": "John Doe Construction Project",
                "address": "123 Main Street, City",
                "coordinates": "https://maps.google.com/?q=12.9715987,77.594566",
                "contact_name": "John Doe",
                "contact_number": "9876543210",
                "remarks": "Initial project setup",
            }
        }
    )

class ProjectUpdate(BaseModel):
    client_id: PyObjectId
    name: str
    address: Optional[str] = None
    coordinates: Optional[str] = None
    contact_name: Optional[str] = None
    contact_number: Optional[str] = None
    remarks: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "client_id": "688872706e3053d0211f0015",
                "name": "John Doe Construction Project",
                "address": "123 Main Street, City",
                "coordinates": "https://maps.google.com/?q=12.9715987,77.594566",
                "contact_name": "John Doe",
                "contact_number": "9876543210",
                "remarks": "Initial project setup",
            }
        }
    ) 