from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Optional, List
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
    start: str | datetime # Start time in IST format
    end: str | datetime # End time in IST format
    client: Optional[str] = None
    project: Optional[str] = None
    schedule_no: Optional[str] = None

class GanttMixer(BaseModel):
    """Represents a mixer in the Gantt chart"""
    id: str
    name: str
    plant: str
    tasks: List[GanttTask] = Field(default_factory=list)

class TMGanttResponse(BaseModel):
    """Response model for Gantt chart data"""
    mixers: List[GanttMixer]

class GanttPump(BaseModel):
    """Represents a mixer in the Gantt chart"""
    id: str
    name: str
    plant: str
    type: Literal["line", "boom"]
    tasks: List[GanttTask] = Field(default_factory=list)
    
class PumpGanttResponse(BaseModel):
    pumps: List[GanttPump]

class GanttResponse(BaseModel):
    mixers: List[GanttMixer]
    pumps: List[GanttPump]

class GanttRequest(BaseModel):
    """Body of the schedule_calendar/gantt endpoint"""
    query_date: datetime | str

class PlantTask(BaseModel):
    """Represents a task for a plant in the plant gantt chart"""
    id: str
    start: str | datetime
    end: str | datetime
    client: Optional[str] = None
    project: Optional[str] = None
    schedule_no: Optional[str] = None
    type: str  # buffer, load, onward, work, return, cushion, fixing, removal, pump
    tm_id: str  # The TM that's performing this task

class PlantHourlyUtilization(BaseModel):
    """Represents hourly TM utilization for a plant"""
    hour: int  # 0-23
    tm_count: int  # Number of TMs used in this hour
    tm_ids: List[str]  # List of TM IDs used in this hour
    utilization_percentage: float  # Percentage of plant capacity used

class PlantGanttRow(BaseModel):
    """Represents a plant row in the plant gantt chart"""
    id: str  # plant id
    name: str  # plant name
    location: Optional[str] = None
    capacity: Optional[float] = None
    tm_per_hour: float  # Theoretical TM capacity per hour
    tasks: List[PlantTask] = Field(default_factory=list)
    hourly_utilization: List[PlantHourlyUtilization] = Field(default_factory=list)

class PlantGanttResponse(BaseModel):
    """Response model for plant-based Gantt chart data"""
    plants: List[PlantGanttRow]
    query_date: str
    total_plants: int
    total_tms_used: int