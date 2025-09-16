import pytest
from datetime import datetime, date, time
from bson import ObjectId
from app.services.tm_service import (
    get_all_tms,
    get_tm,
    create_tm,
    update_tm,
    delete_tm,
    get_average_capacity,
    get_tms_by_plant,
    get_available_tms
)
from app.models.transit_mixer import TransitMixerCreate, TransitMixerUpdate

@pytest.mark.asyncio
async def test_get_all_tms(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_tm1 = {
        "user_id": ObjectId(user_id),
        "identifier": "TM-001",
        "capacity": 6,
        "status": "active",
        "created_at": datetime.utcnow()
    }
    test_tm2 = {
        "user_id": ObjectId(user_id),
        "identifier": "TM-002",
        "capacity": 8,
        "status": "active",
        "created_at": datetime.utcnow()
    }
    await mock_db.transit_mixers.insert_many([test_tm1, test_tm2])
    
    # Act
    result = await get_all_tms(user_id)
    
    # Assert
    assert len(result) == 2
    assert result[0].identifier == "TM-002"  # Most recent first
    assert result[1].identifier == "TM-001"

@pytest.mark.asyncio
async def test_get_tm(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_tm = {
        "user_id": ObjectId(user_id),
        "identifier": "TM-001",
        "capacity": 6,
        "status": "active",
        "created_at": datetime.utcnow()
    }
    result = await mock_db.transit_mixers.insert_one(test_tm)
    tm_id = str(result.inserted_id)
    
    # Act
    tm = await get_tm(tm_id, user_id)
    
    # Assert
    assert tm is not None
    assert tm.identifier == test_tm["identifier"]
    assert tm.capacity == test_tm["capacity"]
    assert str(tm.user_id) == user_id

@pytest.mark.asyncio
async def test_create_tm(mock_db):
    # Arrange
    user_id = str(ObjectId())
    tm_data = TransitMixerCreate(
        identifier="TM-001",
        capacity=6,
        status="active",
        plant_id=str(ObjectId())  # Optional plant ID
    )
    
    # Act
    result = await create_tm(tm_data, user_id)
    
    # Assert
    assert result is not None
    assert result.identifier == tm_data.identifier
    assert result.capacity == tm_data.capacity
    assert result.status == tm_data.status
    assert str(result.user_id) == user_id
    if tm_data.plant_id:
        assert str(result.plant_id) == tm_data.plant_id

@pytest.mark.asyncio
async def test_update_tm(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_tm = {
        "user_id": ObjectId(user_id),
        "identifier": "TM-001",
        "capacity": 6,
        "status": "active",
        "created_at": datetime.utcnow()
    }
    result = await mock_db.transit_mixers.insert_one(test_tm)
    tm_id = str(result.inserted_id)
    
    update_data = TransitMixerUpdate(
        capacity=8,
        status="inactive"
    )
    
    # Act
    updated_tm = await update_tm(tm_id, update_data, user_id)
    
    # Assert
    assert updated_tm.capacity == update_data.capacity
    assert updated_tm.status == update_data.status
    assert updated_tm.identifier == test_tm["identifier"]  # Unchanged field

@pytest.mark.asyncio
async def test_delete_tm(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_tm = {
        "user_id": ObjectId(user_id),
        "identifier": "TM-001",
        "capacity": 6,
        "status": "active",
        "created_at": datetime.utcnow()
    }
    result = await mock_db.transit_mixers.insert_one(test_tm)
    tm_id = str(result.inserted_id)
    
    # Act
    success = await delete_tm(tm_id, user_id)
    
    # Assert
    assert success is True
    assert await mock_db.transit_mixers.find_one({"_id": ObjectId(tm_id)}) is None

@pytest.mark.asyncio
async def test_get_average_capacity(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_tm1 = {
        "user_id": ObjectId(user_id),
        "identifier": "TM-001",
        "capacity": 6,
        "status": "active"
    }
    test_tm2 = {
        "user_id": ObjectId(user_id),
        "identifier": "TM-002",
        "capacity": 8,
        "status": "active"
    }
    await mock_db.transit_mixers.insert_many([test_tm1, test_tm2])
    
    # Act
    result = await get_average_capacity(user_id)
    
    # Assert
    assert result == 7.0  # (6 + 8) / 2

@pytest.mark.asyncio
async def test_get_tms_by_plant(mock_db):
    # Arrange
    user_id = str(ObjectId())
    plant_id = ObjectId()
    
    test_tm1 = {
        "user_id": ObjectId(user_id),
        "plant_id": plant_id,
        "identifier": "TM-001",
        "capacity": 6,
        "status": "active",
        "created_at": datetime.utcnow()
    }
    test_tm2 = {
        "user_id": ObjectId(user_id),
        "plant_id": plant_id,
        "identifier": "TM-002",
        "capacity": 8,
        "status": "active",
        "created_at": datetime.utcnow()
    }
    await mock_db.transit_mixers.insert_many([test_tm1, test_tm2])
    
    # Act
    result = await get_tms_by_plant(str(plant_id), user_id)
    
    # Assert
    assert len(result) == 2
    assert any(tm.identifier == "TM-001" for tm in result)
    assert any(tm.identifier == "TM-002" for tm in result)

@pytest.mark.asyncio
async def test_get_available_tms_with_date_string(mock_db):
    # Arrange
    user_id = str(ObjectId())
    date_str = "2025-09-16"
    test_tm = {
        "user_id": ObjectId(user_id),
        "identifier": "TM-001",
        "capacity": 6,
        "status": "active",
        "created_at": datetime.utcnow()
    }
    await mock_db.transit_mixers.insert_one(test_tm)
    
    # Act
    result = await get_available_tms(date_str, user_id)
    
    # Assert
    assert isinstance(result, list)

@pytest.mark.asyncio
async def test_get_available_tms_with_date_object(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_date = date(2025, 9, 16)
    test_tm = {
        "user_id": ObjectId(user_id),
        "identifier": "TM-001",
        "capacity": 6,
        "status": "active",
        "created_at": datetime.utcnow()
    }
    await mock_db.transit_mixers.insert_one(test_tm)
    
    # Act
    result = await get_available_tms(test_date, user_id)
    
    # Assert
    assert isinstance(result, list)

@pytest.mark.asyncio
async def test_get_available_tms_with_invalid_date(mock_db):
    # Arrange
    user_id = str(ObjectId())
    invalid_date = "invalid-date"
    test_tm = {
        "user_id": ObjectId(user_id),
        "identifier": "TM-001",
        "capacity": 6,
        "status": "active",
        "created_at": datetime.utcnow()
    }
    await mock_db.transit_mixers.insert_one(test_tm)
    
    # Act
    result = await get_available_tms(invalid_date, user_id)
    
    # Assert
    assert isinstance(result, list)  # Should fallback to today's date