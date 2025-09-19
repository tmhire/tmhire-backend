import pytest
from datetime import datetime
from bson import ObjectId
from app.services.plant_service import (
    get_all_plants,
    get_plant,
    create_plant,
    update_plant,
    delete_plant,
    get_plant_tms
)
from app.models.plant import PlantCreate, PlantUpdate
from tests.utils.test_fixtures import create_test_plant



@pytest.mark.asyncio
async def test_get_plant(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_plant = {**create_test_plant(), "user_id": ObjectId(user_id)}
    result = await mock_db.plants.insert_one(test_plant)
    plant_id = str(result.inserted_id)
    
    # Act
    plant = await get_plant(plant_id, user_id)
    
    # Assert
    assert plant is not None
    assert plant.name == test_plant["name"]
    assert plant.location == test_plant["location"]
    assert str(plant.user_id) == user_id

@pytest.mark.asyncio
async def test_get_plant_not_found(mock_db):
    # Arrange
    user_id = str(ObjectId())
    plant_id = str(ObjectId())
    
    # Act
    plant = await get_plant(plant_id, user_id)
    
    # Assert
    assert plant is None

@pytest.mark.asyncio
async def test_create_plant(mock_db):
    # Arrange
    user_id = str(ObjectId())
    plant_data = PlantCreate(
        name="New Plant",
        location="New Location",
        capacity=150,
        status="active"
    )
    
    # Act
    result = await create_plant(plant_data, user_id)
    
    # Assert
    assert result is not None
    assert result.name == plant_data.name
    assert result.location == plant_data.location
    assert result.capacity == plant_data.capacity
    assert result.status == plant_data.status
    assert str(result.user_id) == user_id

@pytest.mark.asyncio
async def test_update_plant(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_plant = {**create_test_plant(), "user_id": ObjectId(user_id)}
    result = await mock_db.plants.insert_one(test_plant)
    plant_id = str(result.inserted_id)
    
    update_data = PlantUpdate(
        name="Updated Plant",
        capacity=200
    )
    
    # Act
    updated_plant = await update_plant(plant_id, update_data, user_id)
    
    # Assert
    assert updated_plant.name == update_data.name
    assert updated_plant.capacity == update_data.capacity
    assert updated_plant.location == test_plant["location"]  # Unchanged field





@pytest.mark.asyncio
async def test_get_plant_tms_not_found(mock_db):
    # Arrange
    user_id = str(ObjectId())
    plant_id = str(ObjectId())
    
    # Act
    result = await get_plant_tms(plant_id, user_id)
    
    # Assert
    assert result["plant"] is None
    assert len(result["transit_mixers"]) == 0