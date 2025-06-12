from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from app.db.mongodb import PyObjectId
from bson import ObjectId

class PumpModel(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    plant_id: Optional[PyObjectId] = None
    identifier: str
    capacity: float
    type: Literal["line", "boom"]
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
                "identifier": "PUMP-1",
                "capacity": 50.0,
                "type": "boom",
                "status": "active",
                "created_at": datetime.utcnow()
            }
        }
    )

class PumpCreate(BaseModel):
    plant_id: str
    identifier: str
    capacity: float
    type: Literal["line", "boom"]
    status: Literal["active", "inactive"] = Field(default="active")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "plant_id": "60d5ec9af682fcd81a060e73",
                "identifier": "PUMP-1",
                "capacity": 50.0,
                "type": "line",
                "status": "active"
            }
        }
    )

class PumpUpdate(BaseModel):
    plant_id: Optional[str] = None
    identifier: Optional[str] = None
    capacity: Optional[float] = None
    type: Optional[Literal["line", "boom"]] = None
    status: Optional[Literal["active", "inactive"]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "plant_id": "60d5ec9af682fcd81a060e74",
                "identifier": "PUMP-2",
                "capacity": 60.0,
                "type": "boom",
                "status": "inactive"
            }
        }
    )

class PumpStatusToggle(BaseModel):
    status: Literal["active", "inactive"]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "inactive"
            }
        }
    )

class AveragePumpCapacity(BaseModel):
    average_capacity: float

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "average_capacity": 55.0
            }
        }
    )
