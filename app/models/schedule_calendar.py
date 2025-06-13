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

class GanttTask(BaseModel):
    """Represents a task in the Gantt chart"""
    id: str
    start: int  # Hour of the day (0-23)
    duration: int  # Duration in hours
    color: str = "bg-orange-500"  # Default color
    client: Optional[str] = None
    type: str = "production"  # production, cleaning, setup, quality, maintenance

class GanttMixer(BaseModel):
    """Represents a mixer in the Gantt chart"""
    id: str
    name: str
    plant: str
    client: Optional[str] = None
    tasks: List[GanttTask] = Field(default_factory=list)

class GanttResponse(BaseModel):
    """Response model for Gantt chart data"""
    mixers: List[GanttMixer] 