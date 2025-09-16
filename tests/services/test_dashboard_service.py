import pytest
from datetime import datetime, date
from bson import ObjectId
from app.services.dashboard_service import get_dashboard_stats
from tests.utils.test_fixtures import create_test_plant, create_test_team

@pytest.mark.asyncio
async def test_get_dashboard_stats_empty(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_date = date(2025, 9, 16)
    
    # Act
    result = await get_dashboard_stats(test_date, user_id)
    
    # Assert
    assert isinstance(result, dict)
    # Verify the structure of the response
    assert "plant_stats" in result
    assert "equipment_stats" in result
    assert "volume_stats" in result
    assert "schedule_stats" in result

@pytest.mark.asyncio
async def test_get_dashboard_stats_with_data(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_date = date(2025, 9, 16)
    
    # Create test plants
    active_plant = {
        "user_id": ObjectId(user_id),
        "name": "Active Plant",
        "status": "active",
        "created_at": datetime.utcnow()
    }
    inactive_plant = {
        "user_id": ObjectId(user_id),
        "name": "Inactive Plant",
        "status": "inactive",
        "created_at": datetime.utcnow()
    }
    await mock_db.plants.insert_many([active_plant, inactive_plant])
    
    # Create test transit mixers
    active_tm = {
        "user_id": ObjectId(user_id),
        "name": "Active TM",
        "status": "active",
        "created_at": datetime.utcnow()
    }
    inactive_tm = {
        "user_id": ObjectId(user_id),
        "name": "Inactive TM",
        "status": "inactive",
        "created_at": datetime.utcnow()
    }
    await mock_db.transit_mixers.insert_many([active_tm, inactive_tm])
    
    # Create test pumps
    active_line_pump = {
        "user_id": ObjectId(user_id),
        "name": "Active Line Pump",
        "type": "line",
        "status": "active",
        "created_at": datetime.utcnow()
    }
    active_boom_pump = {
        "user_id": ObjectId(user_id),
        "name": "Active Boom Pump",
        "type": "boom",
        "status": "active",
        "created_at": datetime.utcnow()
    }
    inactive_line_pump = {
        "user_id": ObjectId(user_id),
        "name": "Inactive Line Pump",
        "type": "line",
        "status": "inactive",
        "created_at": datetime.utcnow()
    }
    inactive_boom_pump = {
        "user_id": ObjectId(user_id),
        "name": "Inactive Boom Pump",
        "type": "boom",
        "status": "inactive",
        "created_at": datetime.utcnow()
    }
    await mock_db.pumps.insert_many([
        active_line_pump,
        active_boom_pump,
        inactive_line_pump,
        inactive_boom_pump
    ])
    
    # Create test schedule
    day_start = datetime.combine(test_date, datetime.min.time())
    schedule = {
        "user_id": ObjectId(user_id),
        "status": "generated",
        "type": "pumping",
        "output_table": {
            "plant_start": day_start.isoformat(),
            "return": day_start.isoformat()
        },
        "created_at": datetime.utcnow()
    }
    await mock_db.schedules.insert_one(schedule)
    
    # Act
    result = await get_dashboard_stats(test_date, user_id)
    
    # Assert
    assert isinstance(result, dict)
    
    # Check plant stats
    assert result["plant_stats"]["active_count"] == 1
    assert result["plant_stats"]["inactive_count"] == 1
    
    # Check equipment stats
    assert result["equipment_stats"]["active_tms_count"] == 1
    assert result["equipment_stats"]["inactive_tms_count"] == 1
    assert result["equipment_stats"]["active_line_pumps_count"] == 1
    assert result["equipment_stats"]["inactive_line_pumps_count"] == 1
    assert result["equipment_stats"]["active_boom_pumps_count"] == 1
    assert result["equipment_stats"]["inactive_boom_pumps_count"] == 1

@pytest.mark.asyncio
async def test_get_dashboard_stats_with_schedules(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_date = date(2025, 9, 16)
    day_start = datetime.combine(test_date, datetime.min.time())
    
    # Create test plant
    plant = {
        "user_id": ObjectId(user_id),
        "name": "Test Plant",
        "status": "active",
        "created_at": datetime.utcnow()
    }
    plant_result = await mock_db.plants.insert_one(plant)
    
    # Create test schedules
    pumping_schedule = {
        "user_id": ObjectId(user_id),
        "status": "generated",
        "type": "pumping",
        "plant_id": plant_result.inserted_id,
        "output_table": {
            "plant_start": day_start.isoformat(),
            "return": day_start.isoformat(),
            "volume": 100
        },
        "created_at": datetime.utcnow()
    }
    
    supply_schedule = {
        "user_id": ObjectId(user_id),
        "status": "generated",
        "type": "supply",
        "plant_id": plant_result.inserted_id,
        "output_table": {
            "plant_start": day_start.isoformat(),
            "return": day_start.isoformat(),
            "volume": 150
        },
        "created_at": datetime.utcnow()
    }
    
    await mock_db.schedules.insert_many([pumping_schedule, supply_schedule])
    
    # Act
    result = await get_dashboard_stats(test_date, user_id)
    
    # Assert
    assert isinstance(result, dict)
    assert "volume_stats" in result
    assert "schedule_stats" in result
    
    # Verify the schedule counts and volumes are correct
    plant_id = str(plant_result.inserted_id)
    assert result["plant_stats"]["plants"][plant_id]["pump_volume"] > 0
    assert result["plant_stats"]["plants"][plant_id]["supply_volume"] > 0
    assert len(result["plant_stats"]["plants"][plant_id]["pump_jobs"]) > 0
    assert len(result["plant_stats"]["plants"][plant_id]["supply_jobs"]) > 0

@pytest.mark.asyncio
async def test_get_dashboard_stats_date_validation(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_date_str = "2025-09-16"
    
    # Act
    result = await get_dashboard_stats(test_date_str, user_id)
    
    # Assert
    assert isinstance(result, dict)
    # Verify that the function handles string dates correctly
    assert "plant_stats" in result
    assert "equipment_stats" in result
    assert "volume_stats" in result
    assert "schedule_stats" in result