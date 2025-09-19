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
    
    # Check counts
    assert "counts" in result
    assert all(count == 0 for count in result["counts"].values())
    assert "active_plants_count" in result["counts"]
    assert "inactive_plants_count" in result["counts"]
    assert "active_tms_count" in result["counts"]
    assert "inactive_tms_count" in result["counts"]
    assert "active_line_pumps_count" in result["counts"]
    assert "inactive_line_pumps_count" in result["counts"]
    assert "active_boom_pumps_count" in result["counts"]
    assert "inactive_boom_pumps_count" in result["counts"]
    
    # Check plants_table
    assert "plants_table" in result
    assert len(result["plants_table"]) == 0
    
    # Check monthly series data
    assert "series" in result
    assert len(result["series"]) == 2
    assert result["series"][0]["name"] == "Pumping quantity"
    assert result["series"][1]["name"] == "TMs used"
    assert len(result["series"][0]["data"]) == 12  # Last 12 months
    assert len(result["series"][1]["data"]) == 12  # Last 12 months
    assert all(count == 0 for count in result["series"][0]["data"])
    assert all(count == 0 for count in result["series"][1]["data"])
    
    # Check recent orders
    assert "recent_orders" in result
    assert len(result["recent_orders"]) == 0

@pytest.mark.asyncio
async def test_get_dashboard_stats_date_validation(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_date = date(2025, 9, 16)
    day_start = datetime.combine(test_date, datetime.min.time())
    
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
        "plant_id": active_plant["_id"],
        "status": "active",
        "created_at": datetime.utcnow()
    }
    inactive_tm = {
        "user_id": ObjectId(user_id),
        "name": "Inactive TM",
        "plant_id": inactive_plant["_id"],
        "status": "inactive",
        "created_at": datetime.utcnow()
    }
    await mock_db.transit_mixers.insert_many([active_tm, inactive_tm])
    
    # Create test pumps
    active_line_pump = {
        "user_id": ObjectId(user_id),
        "name": "Active Line Pump",
        "plant_id": active_plant["_id"],
        "type": "line",
        "status": "active",
        "created_at": datetime.utcnow()
    }
    active_boom_pump = {
        "user_id": ObjectId(user_id),
        "name": "Active Boom Pump",
        "plant_id": active_plant["_id"],
        "type": "boom",
        "status": "active",
        "created_at": datetime.utcnow()
    }
    inactive_line_pump = {
        "user_id": ObjectId(user_id),
        "name": "Inactive Line Pump",
        "plant_id": inactive_plant["_id"],
        "type": "line",
        "status": "inactive",
        "created_at": datetime.utcnow()
    }
    inactive_boom_pump = {
        "user_id": ObjectId(user_id),
        "name": "Inactive Boom Pump",
        "plant_id": inactive_plant["_id"],
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
    
    # Create test schedules
    pumping_schedule = {
        "user_id": ObjectId(user_id),
        "type": "pumping",
        "schedule_no": "PMP001",
        "status": "generated",
        "input_params": {
            "pump_onward_time": 30,
            "pump_fixing_time": 30,
            "pump_removal_time": 30,
            "quantity": 100
        },
        "output_table": [{
            "plant_start": day_start.isoformat(),
            "plant_buffer": day_start.isoformat(),
            "return": (day_start.replace(hour=2)).isoformat(),
            "pump_start": day_start.isoformat(),
            "unloading_time": day_start.isoformat(),
            "tm_id": str(active_tm["_id"]),
            "completed_capacity": 100
        }],
        "client_name": "Test Client",
        "pump": str(active_line_pump["_id"]),
        "plant_id": str(active_plant["_id"]),
        "created_at": datetime.utcnow()
    }
    await mock_db.schedules.insert_one(pumping_schedule)
    
    # Act
    result = await get_dashboard_stats(test_date, user_id)
    
    # Assert
    assert isinstance(result, dict)
    
    # Check counts
    assert result["counts"]["active_plants_count"] == 1
    assert result["counts"]["inactive_plants_count"] == 1
    assert result["counts"]["active_tms_count"] == 1
    assert result["counts"]["inactive_tms_count"] == 1
    assert result["counts"]["active_line_pumps_count"] == 1
    assert result["counts"]["active_boom_pumps_count"] == 1
    assert result["counts"]["inactive_line_pumps_count"] == 1
    assert result["counts"]["inactive_boom_pumps_count"] == 1
    
    # Check plants_table
    active_plant_id = str(active_plant["_id"])
    plant_stats = result["plants_table"][active_plant_id]
    assert len(plant_stats["pump_jobs"]) == 1
    assert plant_stats["tm_used_total_hours"] == 2.0  # 2 hours difference
    assert plant_stats["line_pump_used_total_hours"] == 2.0
    assert plant_stats["boom_pump_used_total_hours"] == 0
    assert plant_stats["tm_active_but_not_used"] == 0
    assert plant_stats["line_pump_active_but_not_used"] == 0
    assert plant_stats["boom_pump_active_but_not_used"] == 1
    
    # Check monthly series
    assert "series" in result
    assert len(result["series"]) == 2
    assert result["series"][0]["name"] == "Pumping quantity"
    assert result["series"][1]["name"] == "TMs used"
    # Current month should have data
    current_month_idx = -1
    assert result["series"][0]["data"][current_month_idx] == 100  # from input_params
    assert result["series"][1]["data"][current_month_idx] == 1    # one TM used
    
    # Check recent orders
    assert "recent_orders" in result
    assert len(result["recent_orders"]) == 1
    recent_order = result["recent_orders"][0]
    assert recent_order["client"] == "Test Client"
    assert recent_order["quantity"] == "100 m³"
    assert recent_order["status"] == "generated"
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
    
    # Create test TM and pump
    tm = {
        "user_id": ObjectId(user_id),
        "name": "Test TM",
        "status": "active",
        "plant_id": plant_result.inserted_id,
        "created_at": datetime.utcnow()
    }
    tm_result = await mock_db.transit_mixers.insert_one(tm)
    
    pump = {
        "user_id": ObjectId(user_id),
        "name": "Test Pump",
        "type": "line",
        "status": "active",
        "plant_id": plant_result.inserted_id,
        "created_at": datetime.utcnow()
    }
    pump_result = await mock_db.pumps.insert_one(pump)
    
    # Create test schedules
    pumping_schedule = {
        "user_id": ObjectId(user_id),
        "status": "generated",
        "type": "pumping",
        "schedule_no": "PMP001",
        "client_name": "Test Client 1",
        "input_params": {
            "pump_onward_time": 30,
            "pump_fixing_time": 30,
            "pump_removal_time": 30,
            "quantity": 100
        },
        "output_table": [{
            "plant_start": day_start.isoformat(),
            "plant_buffer": day_start.isoformat(),
            "return": (day_start.replace(hour=2)).isoformat(),
            "pump_start": day_start.isoformat(),
            "unloading_time": day_start.isoformat(),
            "tm_id": str(tm_result.inserted_id),
            "completed_capacity": 100
        }],
        "pump": str(pump_result.inserted_id),
        "plant_id": str(plant_result.inserted_id),
        "created_at": datetime.utcnow()
    }
    
    supply_schedule = {
        "user_id": ObjectId(user_id),
        "status": "generated",
        "type": "supply",
        "schedule_no": "SUP001",
        "client_name": "Test Client 2",
        "input_params": {
            "quantity": 150
        },
        "output_table": [{
            "plant_start": day_start.isoformat(),
            "plant_buffer": (day_start.replace(hour=3)).isoformat(),
            "return": (day_start.replace(hour=4)).isoformat(),
            "unloading_time": day_start.isoformat(),
            "tm_id": str(tm_result.inserted_id),
            "completed_capacity": 150
        }],
        "plant_id": str(plant_result.inserted_id),
        "created_at": datetime.utcnow()
    }
    
    await mock_db.schedules.insert_many([pumping_schedule, supply_schedule])
    
    # Act
    result = await get_dashboard_stats(test_date, user_id)
    
    # Assert
    assert isinstance(result, dict)
    assert result["counts"]["active_plants_count"] == 1
    assert result["counts"]["active_tms_count"] == 1
    assert result["counts"]["active_line_pumps_count"] == 1
    
    # Verify plant_table stats
    plant_id = str(plant_result.inserted_id)
    plant_stats = result["plants_table"][plant_id]
    assert len(plant_stats["pump_jobs"]) == 1  # One pumping schedule
    assert len(plant_stats["supply_jobs"]) == 1  # One supply schedule
    assert plant_stats["tm_used_total_hours"] == 3.0  # 2 hours for pumping + 1 hour for supply
    assert plant_stats["line_pump_used_total_hours"] == 2.0  # 2 hours from pumping schedule
    assert plant_stats["boom_pump_used_total_hours"] == 0
    assert plant_stats["tm_active_but_not_used"] == 0
    assert plant_stats["line_pump_active_but_not_used"] == 0
    
    # Check monthly series
    assert "series" in result
    assert len(result["series"]) == 2
    assert result["series"][0]["name"] == "Pumping quantity"
    assert result["series"][1]["name"] == "TMs used"
    # Current month should have data
    current_month_idx = -1
    assert result["series"][0]["data"][current_month_idx] == 250  # 100 + 150
    assert result["series"][1]["data"][current_month_idx] == 1    # one TM used
    
    # Check recent orders
    assert "recent_orders" in result
    assert len(result["recent_orders"]) == 2
    # Orders should be sorted by creation date descending
    assert result["recent_orders"][0]["client"] in ["Test Client 1", "Test Client 2"]
    assert result["recent_orders"][0]["quantity"] in ["100 m³", "150 m³"]
    assert result["recent_orders"][0]["status"] == "generated"
    assert result["recent_orders"][1]["client"] in ["Test Client 1", "Test Client 2"]
    assert result["recent_orders"][1]["quantity"] in ["100 m³", "150 m³"]
    assert result["recent_orders"][1]["status"] == "generated"

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
    assert "counts" in result
    assert all(count == 0 for count in result["counts"].values())
    
    # Verify standard response structure
    assert "plants_table" in result
    assert len(result["plants_table"]) == 0
    
    assert "series" in result
    assert len(result["series"]) == 2
    assert result["series"][0]["name"] == "Pumping quantity"
    assert result["series"][1]["name"] == "TMs used"
    assert len(result["series"][0]["data"]) == 12
    assert len(result["series"][1]["data"]) == 12
    
    assert "recent_orders" in result
    assert len(result["recent_orders"]) == 0