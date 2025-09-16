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
async def test_get_all_schedules(mock_db):
    # Arrange
    user_id = str(ObjectId())
    
    # Create test plant
    test_plant = {**create_test_plant(), "user_id": ObjectId(user_id)}
    plant_result = await mock_db.plants.insert_one(test_plant)
    
    # Create test project
    test_project = {
        **create_test_project(),
        "user_id": ObjectId(user_id),
        "mother_plant_id": plant_result.inserted_id
    }
    project_result = await mock_db.projects.insert_one(test_project)
    
    # Create test schedules
    test_schedule1 = {
        "user_id": ObjectId(user_id),
        "project_id": project_result.inserted_id,
        "type": "pumping",
        "status": "generated",
        "output_table": [{
            "plant_start": datetime.now(),
            "pump_start": datetime.now(),
            "unloading_time": datetime.now(),
            "return": datetime.now()
        }],
        "created_at": datetime.utcnow()
    }
    
    test_schedule2 = {
        "user_id": ObjectId(user_id),
        "project_id": project_result.inserted_id,
        "type": "supply",
        "status": "generated",
        "output_table": [{
            "plant_start": datetime.now(),
            "pump_start": None,
            "unloading_time": datetime.now(),
            "return": datetime.now()
        }],
        "created_at": datetime.utcnow()
    }
    
    await mock_db.schedules.insert_many([test_schedule1, test_schedule2])
    
    # Act
    result = await get_all_schedules(user_id, ScheduleType.all)
    
    # Assert
    assert len(result) == 2
    assert result[0].type == "supply"  # Most recent first
    assert result[1].type == "pumping"
    for schedule in result:
        assert schedule.mother_plant_name == test_plant["name"]
        assert schedule.project_name == test_project["name"]

@pytest.mark.asyncio
async def test_get_all_schedules_filtered_by_type(mock_db):
    # Arrange
    user_id = str(ObjectId())
    
    # Create test plant and project
    test_plant = {**create_test_plant(), "user_id": ObjectId(user_id)}
    plant_result = await mock_db.plants.insert_one(test_plant)
    
    test_project = {
        **create_test_project(),
        "user_id": ObjectId(user_id),
        "mother_plant_id": plant_result.inserted_id
    }
    project_result = await mock_db.projects.insert_one(test_project)
    
    # Create test schedules with different types
    pumping_schedule = {
        "user_id": ObjectId(user_id),
        "project_id": project_result.inserted_id,
        "type": "pumping",
        "status": "generated",
        "output_table": [{
            "plant_start": datetime.now(),
            "pump_start": datetime.now(),
            "unloading_time": datetime.now(),
            "return": datetime.now()
        }],
        "created_at": datetime.utcnow()
    }
    
    supply_schedule = {
        "user_id": ObjectId(user_id),
        "project_id": project_result.inserted_id,
        "type": "supply",
        "status": "generated",
        "output_table": [{
            "plant_start": datetime.now(),
            "unloading_time": datetime.now(),
            "return": datetime.now()
        }],
        "created_at": datetime.utcnow()
    }
    
    await mock_db.schedules.insert_many([pumping_schedule, supply_schedule])
    
    # Act
    pumping_result = await get_all_schedules(user_id, ScheduleType.pumping)
    supply_result = await get_all_schedules(user_id, ScheduleType.supply)
    
    # Assert
    assert len(pumping_result) == 1
    assert pumping_result[0].type == "pumping"
    
    assert len(supply_result) == 1
    assert supply_result[0].type == "supply"

@pytest.mark.asyncio
async def test_get_schedule(mock_db):
    # Arrange
    user_id = str(ObjectId())
    
    # Create test plant and project
    test_plant = {**create_test_plant(), "user_id": ObjectId(user_id)}
    plant_result = await mock_db.plants.insert_one(test_plant)
    
    test_project = {
        **create_test_project(),
        "user_id": ObjectId(user_id),
        "mother_plant_id": plant_result.inserted_id
    }
    project_result = await mock_db.projects.insert_one(test_project)
    
    # Create test schedule
    test_schedule = {
        "user_id": ObjectId(user_id),
        "project_id": project_result.inserted_id,
        "type": "pumping",
        "status": "generated",
        "output_table": [{
            "plant_start": datetime.now(),
            "pump_start": datetime.now(),
            "unloading_time": datetime.now(),
            "return": datetime.now(),
            "tm_id": str(ObjectId())
        }],
        "created_at": datetime.utcnow()
    }
    
    schedule_result = await mock_db.schedules.insert_one(test_schedule)
    schedule_id = str(schedule_result.inserted_id)
    
    # Act
    result = await get_schedule(schedule_id, user_id)
    
    # Assert
    assert result is not None
    assert result.schedule.type == "pumping"
    assert str(result.schedule.project_id) == str(project_result.inserted_id)
    assert str(result.schedule.user_id) == user_id

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