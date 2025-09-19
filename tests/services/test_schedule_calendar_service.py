import pytest
from datetime import datetime, date, time, timedelta
from bson import ObjectId
from app.services.schedule_calendar_service import (
    get_calendar_for_date_range,
    initialize_calendar_day,
    _get_valid_date
)
from app.models.schedule_calendar import ScheduleCalendarQuery, TimeSlot, TMAvailabilitySlot

@pytest.fixture
def valid_query():
    return ScheduleCalendarQuery(
        start_date=date(2025, 9, 16),
        end_date=date(2025, 9, 16),
        working_start_time=8.0,  # 8:00 AM
        working_end_time=20.0    # 8:00 PM
    )

def test_get_valid_date():
    # Test with date object
    test_date = date(2025, 9, 16)
    assert _get_valid_date(test_date) == test_date
    
    # Test with ISO format string
    assert _get_valid_date("2025-09-16") == date(2025, 9, 16)
    
    # Test with invalid string (should return current date)
    invalid_result = _get_valid_date("invalid")
    assert isinstance(invalid_result, date)