from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any, Union
from app.db.mongodb import PyObjectId
from bson import ObjectId

class InputParams(BaseModel):
    quantity: float
    pumping_speed: float
    onward_time: int
    return_time: int
    buffer_time: int
    pump_start: datetime = Field(default_factory=lambda: datetime.now().replace(hour=8, minute=0, second=0, microsecond=0))
    schedule_date: date = Field(default_factory=lambda: datetime.now().date())
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={
            date: lambda d: d.isoformat() if isinstance(d, date) else d,
            datetime: lambda dt: dt.isoformat() if isinstance(dt, datetime) else dt
        }
    )

class Trip(BaseModel):
    trip_no: int
    tm_no: str
    tm_id: str
    plant_start: Union[datetime, str]
    pump_start: Union[datetime, str]
    unloading_time: Union[datetime, str]
    return_: Union[datetime, str] = Field(..., alias="return")
    completed_capacity: float = 0
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            datetime: lambda dt: dt.isoformat() if isinstance(dt, datetime) else dt
        },
        json_schema_extra={
            "example": {
                "trip_no": 1,
                "tm_no": "A",
                "tm_id": "60d5ec9af682fcd81a060e73",
                "plant_start": "2023-06-25T08:30:00",
                "pump_start": "2023-06-25T09:00:00",
                "unloading_time": "2023-06-25T09:12:00",
                "return": "2023-06-25T09:52:00",
                "completed_capacity": 8.0
            }
        }
    )

class ScheduleModel(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    client_id: Optional[PyObjectId] = None
    client_name: str
    site_location: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    input_params: InputParams
    output_table: Optional[List[Trip]] = Field(default_factory=list)
    tm_count: Optional[int] = None
    pumping_time: Optional[float] = None
    status: str = "draft"  # draft, generated, finalized, completed, cancelled
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            ObjectId: str, 
            date: lambda d: d.isoformat() if isinstance(d, date) else d,
            datetime: lambda dt: dt.isoformat() if isinstance(dt, datetime) else dt
        },
        json_schema_extra={
            "example": {
                "user_id": "60d5ec9af682fcd81a060e72",
                "client_id": "60d5ec9af682fcd81a060e78",
                "client_name": "ABC Constructions",
                "site_location": "Chennai Main Road Site",
                "input_params": {
                    "quantity": 60,
                    "pumping_speed": 30,
                    "onward_time": 30,
                    "return_time": 25,
                    "buffer_time": 5,
                    "pump_start": "2023-06-25T08:00:00",
                    "schedule_date": "2023-06-25"
                },
                "tm_count": 6,
                "pumping_time": 2.0,
                "status": "draft"
            }
        }
    )

class ScheduleCreate(BaseModel):
    client_id: str
    client_name: Optional[str] = None
    site_location: Optional[str] = None
    input_params: InputParams
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "client_id": "60d5ec9af682fcd81a060e78",
                "client_name": "ABC Constructions",
                "site_location": "Chennai Main Road Site",
                "input_params": {
                    "quantity": 60,
                    "pumping_speed": 30,
                    "onward_time": 30,
                    "return_time": 25,
                    "buffer_time": 5,
                    "pump_start": "2023-06-25T08:00:00",
                    "schedule_date": "2023-06-25"
                }
            }
        }
    )

class ScheduleUpdate(BaseModel):
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    site_location: Optional[str] = None
    input_params: Optional[InputParams] = None
    status: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "client_id": "60d5ec9af682fcd81a060e79",
                "client_name": "XYZ Constructions",
                "site_location": "Updated Location",
                "input_params": {
                    "quantity": 70,
                    "pumping_speed": 35,
                    "onward_time": 30,
                    "return_time": 25,
                    "buffer_time": 5,
                    "pump_start": "2023-06-26T08:00:00",
                    "schedule_date": "2023-06-26"
                },
                "status": "draft"
            }
        }
    ) 