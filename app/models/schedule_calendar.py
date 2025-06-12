from datetime import datetime, date, time, timedelta
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from app.db.mongodb import PyObjectId
from bson import ObjectId

class TMAvailabilitySlot(BaseModel):
    """Represents a single TM's availability for a specific time slot"""
    tm_id: str
    tm_identifier: str
    plant_id: Optional[str] = None
    plant_name: Optional[str] = None
    status: str = "available"  # available, booked
    schedule_id: Optional[str] = None

class TimeSlot(BaseModel):
    """Represents a 30-minute time slot in the calendar"""
    start_time: datetime
    end_time: datetime
    tm_availability: List[TMAvailabilitySlot] = Field(default_factory=list)

class DailySchedule(BaseModel):
    """Represents the scheduling data for a specific date with 30-minute time slots from 8AM to 8PM"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    date: datetime
    time_slots: List[TimeSlot] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders = {
            ObjectId: str,
            PyObjectId: str,
            date: lambda d: d.isoformat(),
            datetime: lambda d: d.isoformat(),
        },
        json_schema_extra={
            "example": {
                "user_id": "60d5ec9af682fcd81a060e72",
                "date": "2023-06-30T00:00:00",
                "time_slots": [
                    {
                        "start_time": "2023-06-30T08:00:00",
                        "end_time": "2023-06-30T08:30:00",
                        "tm_availability": [
                            {
                                "tm_id": "60d5ec9af682fcd81a060e73",
                                "tm_identifier": "TM-A",
                                "plant_id": "60d5ec9af682fcd81a060e74",
                                "plant_name": "Main Plant",
                                "status": "available",
                                "schedule_id": None
                            },
                            {
                                "tm_id": "60d5ec9af682fcd81a060e75",
                                "tm_identifier": "TM-B",
                                "plant_id": "60d5ec9af682fcd81a060e74",
                                "plant_name": "Main Plant",
                                "status": "booked",
                                "schedule_id": "60d5ec9af682fcd81a060e76"
                            }
                        ]
                    },
                    {
                        "start_time": "2023-06-30T08:30:00",
                        "end_time": "2023-06-30T09:00:00",
                        "tm_availability": []
                    }
                ]
            }
        }
    )

class ScheduleCalendarQuery(BaseModel):
    """Query parameters for retrieving schedule calendar data"""
    start_date: date
    end_date: date
    plant_id: Optional[str] = None
    tm_id: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "start_date": "2023-07-01",
                "end_date": "2023-07-31",
                "plant_id": "60d5ec9af682fcd81a060e74",
                "tm_id": "60d5ec9af682fcd81a060e73"
            }
        }
    ) 