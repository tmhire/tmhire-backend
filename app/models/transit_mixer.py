from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from app.db.mongodb import PyObjectId
from bson import ObjectId

class TransitMixerModel(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    plant_id: Optional[PyObjectId] = None
    identifier: str
    capacity: float
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
                "created_at": datetime.utcnow()
            }
        }
    )

class TransitMixerCreate(BaseModel):
    plant_id: str
    identifier: str
    capacity: float
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "plant_id": "60d5ec9af682fcd81a060e73",
                "identifier": "TM-A",
                "capacity": 8.0
            }
        }
    )

class TransitMixerUpdate(BaseModel):
    plant_id: Optional[str] = None
    identifier: Optional[str] = None
    capacity: Optional[float] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "plant_id": "60d5ec9af682fcd81a060e74",
                "identifier": "TM-B",
                "capacity": 9.0
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