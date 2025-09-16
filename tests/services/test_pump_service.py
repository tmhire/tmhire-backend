import pytest
from datetime import datetime, date
from bson import ObjectId
from app.services.pump_service import (
    get_all_pumps,
    get_pump,
    create_pump,
    update_pump,
    delete_pump,
    get_pumps_by_plant,
    get_pump_gantt_data
)
from app.models.pump import PumpCreate, PumpUpdate
from tests.utils.test_fixtures import create_test_team
from tests.utils.pump_fixtures import create_test_pump
from unittest.mock import patch

@pytest.fixture(autouse=True)
def mock_team_service():
    with patch('app.services.pump_service.get_team_member') as mock:
        async def mock_team_member(*args, **kwargs):
            return {"_id": ObjectId(), "name": "Test Team Member"}
        mock.side_effect = mock_team_member
        yield mock

@pytest.mark.asyncio
async def test_get_all_pumps(mock_db):
    # Arrange
    user_id = str(ObjectId())
    plant_id = str(ObjectId())
    test_pump1 = create_test_pump(ObjectId(user_id), ObjectId(plant_id), "PUMP-001", 50.0, "line")
    test_pump2 = create_test_pump(ObjectId(user_id), ObjectId(plant_id), "PUMP-002", 60.0, "boom")
    await mock_db.pumps.insert_many([test_pump1, test_pump2])
    
    # Act
    result = await get_all_pumps(user_id)
    
    # Assert
    assert len(result) == 2
    sorted_identifiers = sorted([p.identifier for p in result])
    assert sorted_identifiers == ["PUMP-001", "PUMP-002"]

@pytest.mark.asyncio
async def test_get_pump(mock_db):
    # Arrange
    user_id = str(ObjectId())
    plant_id = str(ObjectId())
    test_pump = create_test_pump(ObjectId(user_id), ObjectId(plant_id), "PUMP-001", 50.0, "line")
    result = await mock_db.pumps.insert_one(test_pump)
    pump_id = str(result.inserted_id)
    
    # Act
    pump = await get_pump(pump_id, user_id)
    
    # Assert
    assert pump is not None
    assert pump.identifier == test_pump["identifier"]
    assert pump.type == test_pump["type"]
    assert str(pump.user_id) == user_id

@pytest.mark.asyncio
async def test_create_pump(mock_db):
    # Arrange
    user_id = str(ObjectId())
    plant_id = str(ObjectId())
    
    # Create required team members
    test_operator = {**create_test_team(), "user_id": ObjectId(user_id)}
    operator_result = await mock_db.teams.insert_one(test_operator)
    
    test_gang = {**create_test_team(), "user_id": ObjectId(user_id)}
    gang_result = await mock_db.teams.insert_one(test_gang)
    
    pump_data = PumpCreate(
        identifier="PUMP-001",
        type="line",
        plant_id=plant_id,
        capacity=50.0,
        make="Test Make",
        pump_operator_id=str(ObjectId()),
        pipeline_gang_id=str(ObjectId())
    )
    
    # Act
    result = await create_pump(pump_data, user_id)
    
    # Assert
    assert result is not None
    assert result.identifier == pump_data.identifier
    assert result.type == pump_data.type
    assert result.status == pump_data.status

@pytest.mark.asyncio
async def test_create_pump_missing_identifier(mock_db):
    # Arrange
    user_id = str(ObjectId())
    plant_id = str(ObjectId())
    pump_data = PumpCreate(
        identifier="",  # Empty identifier
        type="line",
        plant_id=plant_id,
        capacity=50.0,
        make="Test Make",
        pump_operator_id=str(ObjectId()),
        pipeline_gang_id=str(ObjectId())
    )
    
    # Act & Assert
    with pytest.raises(ValueError, match="Pump identifier is required"):
        await create_pump(pump_data, user_id)

@pytest.mark.asyncio
async def test_update_pump(mock_db):
    # Arrange
    user_id = str(ObjectId())
    plant_id = str(ObjectId())
    test_pump = create_test_pump(ObjectId(user_id), ObjectId(plant_id), "PUMP-001", 50.0, "line")
    result = await mock_db.pumps.insert_one(test_pump)
    pump_id = str(result.inserted_id)

    update_data = PumpUpdate(
        status="inactive",
        pump_operator_id=str(ObjectId()),
        pipeline_gang_id=str(ObjectId())
    )    # Act
    updated_pump = await update_pump(pump_id, update_data, user_id)
    
    # Assert
    assert updated_pump.status == update_data.status
    assert updated_pump.identifier == test_pump["identifier"]  # Unchanged field

@pytest.mark.asyncio
async def test_delete_pump(mock_db):
    # Arrange
    user_id = str(ObjectId())
    plant_id = str(ObjectId())
    test_pump = create_test_pump(ObjectId(user_id), ObjectId(plant_id), "PUMP-001", 50.0, "line")
    result = await mock_db.pumps.insert_one(test_pump)
    pump_id = str(result.inserted_id)
    
    # Act
    success = await delete_pump(pump_id, user_id)
    
    # Assert
    assert success is True
    assert await mock_db.pumps.find_one({"_id": ObjectId(pump_id)}) is None

@pytest.mark.asyncio
async def test_get_pumps_by_plant(mock_db):
    # Arrange
    user_id = str(ObjectId())
    plant_id = str(ObjectId())
    
    test_pump1 = create_test_pump(ObjectId(user_id), ObjectId(plant_id), "PUMP-001", 50.0, "line")
    test_pump2 = create_test_pump(ObjectId(user_id), ObjectId(plant_id), "PUMP-002", 60.0, "boom")
    await mock_db.pumps.insert_many([test_pump1, test_pump2])
    
    # Act
    result = await get_pumps_by_plant(str(plant_id), user_id)
    
    # Assert
    assert len(result) == 2
    assert any(pump.identifier == "PUMP-001" for pump in result)
    assert any(pump.identifier == "PUMP-002" for pump in result)

@pytest.mark.asyncio
async def test_get_pump_gantt_data(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_date = date(2025, 9, 16)
    
    # Create test pump
    plant_id = str(ObjectId())
    test_pump = create_test_pump(ObjectId(user_id), ObjectId(plant_id), "PUMP-001", 50.0, "line")
    pump_result = await mock_db.pumps.insert_one(test_pump)
    
    # Create test schedule for the pump
    test_schedule = {
        "user_id": ObjectId(user_id),
        "pump_id": pump_result.inserted_id,
        "status": "generated",
        "output_table": {
            "plant_start": datetime.combine(test_date, datetime.min.time()).isoformat()
        },
        "created_at": datetime.utcnow()
    }
    await mock_db.schedules.insert_one(test_schedule)
    
    # Act
    result = await get_pump_gantt_data(test_date, user_id)
    
    # Assert
    assert isinstance(result, list)
    # Note: The actual assertions would depend on your GanttPump implementation