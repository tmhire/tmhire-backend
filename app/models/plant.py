from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from app.db.mongodb import PyObjectId
from bson import ObjectId

class PlantModel(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    name: str
    location: str
    address: Optional[str] = None
    coordinates: Optional[str] = None
    contact_name1: Optional[str] = None
    contact_number1: Optional[str] = None
    contact_name2: Optional[str] = None
    contact_number2: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "name": "Main Concrete Plant",
                "location": "Chennai",
                "address": "123 Industrial Area, Chennai",
                "coordinates": "https://maps.google.com/?q=12.9715987,77.594566",
                "contact_name1": "John Doe",
                "contact_number1":"9876543210",
                "contact_name2":"Jane Smith",
                "contact_number2": "1234567890",
            }
        }
    )

class PlantCreate(BaseModel):
    name: str
    location: str
    address: Optional[str] = None
    coordinates: Optional[str] = None
    contact_name1: Optional[str] = None
    contact_number1: Optional[str] = None
    contact_name2: Optional[str] = None
    contact_number2: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Main Concrete Plant",
                "location": "Chennai",
                "address": "123 Industrial Area, Chennai",
                "coordinates": "https://maps.google.com/?q=12.9715987,77.594566",
                "contact_name1": "John Doe",
                "contact_number1":"9876543210",
                "contact_name2":"Jane Smith",
                "contact_number2": "1234567890",
            }
        }
    )

class PlantUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    coordinates: Optional[str] = None
    contact_name1: Optional[str] = None
    contact_number1: Optional[str] = None
    contact_name2: Optional[str] = None
    contact_number2: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Updated Plant Name",
                "location": "Updated Location",
                "address": "Updated Address",
                "coordinates": "https://maps.google.com/?q=12.9715987,77.594566",
                "contact_name1": "John Doe",
                "contact_number1":"9876543210",
                "contact_name2":"Jane Smith",
                "contact_number2": "1234567890",
            }
        }
    ) 