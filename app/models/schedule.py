from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Union
from app.db.mongodb import PyObjectId
from bson import ObjectId
from enum import Enum

from app.models.pump import PumpModel

class InputParams(BaseModel):
    quantity: float
    pumping_speed: float
    unloading_time: int = 0
    onward_time: int
    pump_onward_time: int = 0
    pump_fixing_time: Optional[int] = 0  # Time taken to fix the pump at the site
    pump_removal_time: Optional[int] = 0
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
    cycle_time: Optional[float] = None  # Duration of this trip in seconds
    trip_no_for_tm: Optional[int] = None  # Nth trip for this TM in the schedule
    cushion_time: Optional[int] = None
    plant_name: Optional[str] = None
    
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
                "completed_capacity": 8.0,
                "cycle_time": 4920.0,
                "trip_no_for_tm": 1,
                "cushion_time": 2,
                "plant_name": "Main Plant"
            }
        }
    )

class PumpType(str, Enum):
    LINE = "line"
    BOOM = "boom"

class ScheduleType(str, Enum):
    supply = "supply"
    pumping = "pumping"


class ScheduleModel(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    project_id: Optional[PyObjectId] = None  # Now always required
    client_id: PyObjectId   # Now always required
    client_name: str
    pump: Optional[PyObjectId | str] = None
    pump_type: Optional[PumpType] = None  # e.g., Boom Pump, Line Pump, etc.
    site_address: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    input_params: InputParams
    output_table: Optional[List[Trip]] = Field(default_factory=list)
    tm_count: Optional[int] = None
    concreteGrade: Optional[int] = None  # e.g., M20, M25, etc.
    pumping_job: Optional[str] = None
    floor_height: Optional[int] = None
    pump_site_reach_time: Optional[Union[datetime, str]] = None 
    pumping_speed: Optional[int] = None  # Concrete pumping speed in cubic meters per hour
    pumping_time: Optional[float] = None
    status: str = "draft"  # draft, generated, finalized, completed, cancelled
    type: Optional[ScheduleType] = "pumping"
    
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
                "project_id": "60d5ec9af682fcd81a060e78",
                "client_id": "60d5ec9af682fcd81a060e70",
                "client_name": "ABC Constructions",
                "pump": "60d5ec9af682fcd81a060e73",
                "pump_type": "boom",
                "site_address": "Chennai Main Road Site",
                "input_params": {
                    "quantity": 60,
                    "pumping_speed": 30,
                    "onward_time": 30,
                    "pump_onward_time": 50,
                    "pump_fixing_time": 10,
                    "pump_removal_time": 10,
                    "return_time": 25,
                    "buffer_time": 5,
                    "pump_start": "2023-06-25T08:00:00",
                    "schedule_date": "2023-06-25"
                },
                "tm_count": 6,
                "concreteGrade": 25,
                "pumping_job": "Road",
                "floor_height": 10,
                "pump_site_reach_time": "2023-06-25T07:30:00",
                "pumping_speed": 30,
                "pumping_time": 2.0,
                "status": "draft",
                "type": "supply"
            }
        }
    )

class AvailableTM(BaseModel):
    id: str
    identifier: str
    capacity: float
    plant_id: Optional[str]
    availability: bool

class AvailablePump(PumpModel):
    id: str
    availability: bool

class GetScheduleResponse(ScheduleModel):
    available_tms: Optional[List[AvailableTM]] = Field(default_factory=list)
    cycle_time: Optional[float] = None  # Total cycle time for the schedule in hours
    total_trips: Optional[int] = None  # Total number of trips calculated for this schedule
    trips_per_tm: Optional[int] = None  # Average number of trips per TM for this schedule
    available_pumps: Optional[List[AvailablePump]] = Field(default_factory=list)

class ScheduleCreate(BaseModel):
    project_id: str
    client_id: str  # Now required
    client_name: Optional[str] = None
    # pump: Optional[PyObjectId] = None
    pump_type: Optional[PumpType] = None  # e.g., Boom Pump, Line Pump, etc.
    site_address: Optional[str] = None
    concreteGrade: Optional[int] = None  # e.g., M20, M25, etc.
    pumping_job: Optional[str] = None
    floor_height: Optional[int] = None
    pump_site_reach_time: Union[datetime, str] = None
    pumping_speed: Optional[int] = None  # Concrete pumping speed in cubic meters per hour
    pumping_time: Optional[float] = None
    input_params: InputParams
    type: Optional[str] = "pumping"
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_id": "60d5ec9af682fcd81a060e78",
                "client_id": "60d5ec9af682fcd81a060e70",
                "client_name": "ABC Constructions",
                "pump_type": "boom",
                "site_address": "Chennai Main Road Site",
                "concreteGrade": 25,
                "pumping_job": "Road",
                "floor_height": 10,
                "pump_site_reach_time": "2023-06-25T07:30:00",
                "pumping_speed": 30,
                "pumping_time": 2.0,
                "input_params": {
                    "quantity": 60,
                    "pumping_speed": 30,
                    "onward_time": 30,
                    "pump_onward_time": 50,
                    "pump_fixing_time": 10,
                    "pump_removal_time": 10,
                    "return_time": 25,
                    "buffer_time": 5,
                    "pump_start": "2023-06-25T08:00:00",
                    "schedule_date": "2023-06-25"
                },
                "type": "supply"
            }
        }
    )

class CalculateTM(ScheduleCreate):
    tm_id: str

class ScheduleUpdate(BaseModel):
    project_id: Optional[str] = None
    client_id: Optional[str] = None  # Now required for update if project_id is updated
    client_name: Optional[str] = None
    site_address: Optional[str] = None
    input_params: Optional[InputParams] = None
    status: Optional[str] = None
    pump: Optional[PyObjectId] = None
    pump_type: Optional[PumpType] = None
    pumping_speed: Optional[int] = None  # Concrete pumping speed in cubic meters per hour
    concreteGrade: Optional[int] = None  # e.g., M20, M25, etc.
    pumping_job: Optional[str] = None
    floor_height: Optional[int] = None
    pump_site_reach_time: Union[datetime, str] = None
    type: Optional[str] = "pumping"
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_id": "60d5ec9af682fcd81a060e79",
                "client_id": "60d5ec9af682fcd81a060e70",
                "client_name": "XYZ Constructions",
                "site_address": "Updated Location",
                "input_params": {
                    "quantity": 70,
                    "pumping_speed": 35,
                    "onward_time": 30,
                    "pump_onward_time": 50,
                    "pump_fixing_time": 10,
                    "pump_removal_time": 10,
                    "return_time": 25,
                    "buffer_time": 5,
                    "pump_start": "2023-06-26T08:00:00",
                    "schedule_date": "2023-06-26"
                },
                "status": "draft",
                "pump": "60d5ec9af682fcd81a060e73",
                "pump_type": "boom",
                "pumping_speed": 35,
                "concreteGrade": 30,
                "pumping_job": "Road",
                "floor_height": 12,
                "pump_site_reach_time": "2023-06-26T07:30:00",
                "type": "supply"
            }
        }
    ) 