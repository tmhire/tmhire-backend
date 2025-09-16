import pytest
from datetime import datetime, date, time, timedelta
from bson import ObjectId
from app.services.schedule_calendar_service import (
    get_calendar_for_date_range,
    initialize_calendar_day,
    _get_valid_date
)
from app.models.schedule_calendar import ScheduleCalendarQuery, TimeSlot, TMAvailabilitySlot

@pytest.mark.asyncio
async def test_get_calendar_for_date_range_empty(mock_db):
    # Arrange
    user_id = str(ObjectId())
    start_date = date(2025, 9, 16)
    end_date = date(2025, 9, 17)
    
    query = ScheduleCalendarQuery(
        start_date=start_date,
        end_date=end_date
    )
    
    # Act
    result = await get_calendar_for_date_range(query, user_id)
    
    # Assert
    assert isinstance(result, list)
    assert len(result) == 2  # Two days should be initialized
    assert result[0].date.date() == start_date
    assert result[1].date.date() == end_date

@pytest.mark.asyncio
async def test_get_calendar_for_date_range_with_existing_data(mock_db):
    # Arrange
    user_id = str(ObjectId())
    start_date = date(2025, 9, 16)
    end_date = date(2025, 9, 17)
    
    # Create test calendar entry
    test_entry = {
        "user_id": ObjectId(user_id),
        "date": datetime.combine(start_date, time.min),
        "time_slots": [
            {
                "start_time": "08:00:00",  # Store time as string
                "end_time": "08:30:00",    # Store time as string
                "tm_availability": []
            }
        ]
    }
    await mock_db.schedule_calendar.insert_one(test_entry)
    
    query = ScheduleCalendarQuery(
        start_date=start_date,
        end_date=end_date
    )
    
    # Act
    result = await get_calendar_for_date_range(query, user_id)
    
    # Assert
    assert len(result) == 2  # One existing + one initialized
    assert any(cal.date.date() == start_date for cal in result)
    assert any(cal.date.date() == end_date for cal in result)

@pytest.mark.asyncio
async def test_get_calendar_for_date_range_with_plant_filter(mock_db):
    # Arrange
    user_id = str(ObjectId())
    plant_id = str(ObjectId())
    start_date = date(2025, 9, 16)
    end_date = date(2025, 9, 16)
    
    # Create test calendar entry with plant
    test_entry = {
        "user_id": ObjectId(user_id),
        "date": datetime.combine(start_date, time.min),
        "time_slots": [
            {
                "start_time": "08:00:00",
                "end_time": "08:30:00",
                "tm_availability": [
                    {
                        "plant_id": plant_id,
                        "tm_id": str(ObjectId()),
                        "available": True
                    }
                ]
            }
        ]
    }
    await mock_db.schedule_calendar.insert_one(test_entry)
    
    query = ScheduleCalendarQuery(
        start_date=start_date,
        end_date=end_date,
        plant_id=plant_id
    )
    
    # Act
    result = await get_calendar_for_date_range(query, user_id)
    
    # Assert
    assert len(result) == 1
    assert result[0].date.date() == start_date
    assert len(result[0].time_slots) > 0
    assert len(result[0].time_slots[0].tm_availability) > 0
    assert result[0].time_slots[0].tm_availability[0].plant_id == plant_id

@pytest.mark.asyncio
async def test_get_calendar_for_date_range_with_tm_filter(mock_db):
    # Arrange
    user_id = str(ObjectId())
    tm_id = str(ObjectId())
    start_date = date(2025, 9, 16)
    end_date = date(2025, 9, 16)
    
    # Create test calendar entry with transit mixer
    test_entry = {
        "user_id": ObjectId(user_id),
        "date": datetime.combine(start_date, time.min),
        "time_slots": [
            {
                "start_time": "08:00:00",
                "end_time": "08:30:00",
                "tm_availability": [
                    {
                        "plant_id": str(ObjectId()),
                        "tm_id": tm_id,
                        "available": True
                    }
                ]
            }
        ]
    }
    await mock_db.schedule_calendar.insert_one(test_entry)
    
    query = ScheduleCalendarQuery(
        start_date=start_date,
        end_date=end_date,
        tm_id=tm_id
    )
    
    # Act
    result = await get_calendar_for_date_range(query, user_id)
    
    # Assert
    assert len(result) == 1
    assert result[0].date.date() == start_date
    assert len(result[0].time_slots) > 0
    assert len(result[0].time_slots[0].tm_availability) > 0
    assert result[0].time_slots[0].tm_availability[0].tm_id == tm_id

@pytest.mark.asyncio
async def test_initialize_calendar_day(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_date = date(2025, 9, 16)
    
    # Create test plant and transit mixer
    plant = {
        "user_id": ObjectId(user_id),
        "name": "Test Plant",
        "status": "active",
        "created_at": datetime.utcnow()
    }
    plant_result = await mock_db.plants.insert_one(plant)
    
    tm = {
        "user_id": ObjectId(user_id),
        "plant_id": plant_result.inserted_id,
        "name": "Test TM",
        "status": "active",
        "created_at": datetime.utcnow()
    }
    await mock_db.transit_mixers.insert_one(tm)
    
    # Act
    result = await initialize_calendar_day(test_date, user_id)
    
    # Assert
    assert result is not None
    assert result.date.date() == test_date
    assert len(result.time_slots) > 0  # Should have time slots from 8AM to 8PM
    # Verify first and last time slots
    assert result.time_slots[0].start_time == "08:00:00"  # Time as string
    assert result.time_slots[-1].end_time == "20:00:00"  # Time as string

def test_get_valid_date():
    # Test with date object
    test_date = date(2025, 9, 16)
    assert _get_valid_date(test_date) == test_date
    
    # Test with ISO format string
    assert _get_valid_date("2025-09-16") == date(2025, 9, 16)
    
    # Test with invalid string (should return current date)
    invalid_result = _get_valid_date("invalid")
    assert isinstance(invalid_result, date)