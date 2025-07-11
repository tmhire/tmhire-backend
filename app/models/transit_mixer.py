from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from app.db.mongodb import PyObjectId
from bson import ObjectId

class TransitMixerModel(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    plant_id: Optional[PyObjectId] = None
    identifier: str
    capacity: float
    driver_name: Optional[str] = None
    driver_contact: Optional[str] = None
    status: Literal["active", "inactive"] = Field(default="active")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "user_id": "60d5ec9af682fcd81a060e72",
                "plant_id": "60d5ec9af682fcd81a060e73",
                "identifier": "TM-A",
                "capacity": 8.0,
                "driver_name": "John Doe",
                "driver_contact": "+1234567890",
                "status": "active",
                "created_at": datetime.utcnow()
            }
        }
    )

class TransitMixerCreate(BaseModel):
    plant_id: str
    identifier: str
    capacity: float
    driver_name: Optional[str] = None
    driver_contact: Optional[str] = None
    status: Literal["active", "inactive"] = Field(default="active")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "plant_id": "60d5ec9af682fcd81a060e73",
                "identifier": "TM-A",
                "capacity": 8.0,
                "driver_name": "John Doe",
                "driver_contact": "+1234567890",
                "status": "active"
            }
        }
    )

class TransitMixerUpdate(BaseModel):
    plant_id: Optional[str] = None
    identifier: Optional[str] = None
    capacity: Optional[float] = None
    driver_name: Optional[str] = None
    driver_contact: Optional[str] = None
    status: Optional[Literal["active", "inactive"]] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "plant_id": "60d5ec9af682fcd81a060e74",
                "identifier": "TM-B",
                "capacity": 9.0,
                "driver_name": "Jane Smith",
                "driver_contact": "+1987654321",
                "status": "inactive"
            }
        }
    )

class TransitMixerStatusToggle(BaseModel):
    status: Literal["active", "inactive"]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "inactive"
            }
        }
    )

class AverageCapacity(BaseModel):
    average_capacity: float
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "average_capacity": 8.5
            }
        }
    ) 