import pytest
from datetime import datetime, date, time
from bson import ObjectId
from app.services.schedule_service import (
    get_all_schedules,
    get_schedule,
    _convert_to_datetime,
    UNLOADING_TIME_LOOKUP
)
from app.models.schedule import ScheduleType, Trip
from tests.utils.test_fixtures import create_test_project, create_test_plant







@pytest.mark.asyncio
async def test_get_schedule_not_found(mock_db):
    # Arrange
    user_id = str(ObjectId())
    schedule_id = str(ObjectId())
    
    # Act
    result = await get_schedule(schedule_id, user_id)
    
    # Assert
    assert result is None

def test_convert_to_datetime():
    # Test with datetime object
    now = datetime.now()
    assert _convert_to_datetime(now) == now
    
    # Test with ISO format string
    date_str = "2025-09-16T12:00:00"
    expected = datetime(2025, 9, 16, 12, 0)
    assert _convert_to_datetime(date_str) == expected
    
    # Test with invalid string
    assert _convert_to_datetime("invalid") is None

def test_unloading_time_lookup():
    # Test that all values in the lookup table are valid
    for key, value in UNLOADING_TIME_LOOKUP.items():
        assert isinstance(key, int)  # Capacity should be integer
        assert isinstance(value, int)  # Time should be integer
        assert value > 0  # Time should be positive