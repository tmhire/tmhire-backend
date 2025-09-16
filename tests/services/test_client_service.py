import pytest
from datetime import datetime
from bson import ObjectId
from app.services.client_service import (
    get_all_clients,
    get_client,
    create_client,
    update_client,
    delete_client,
    get_client_schedules,
    get_client_stats
)
from app.models.client import ClientCreate, ClientUpdate
from tests.utils.test_fixtures import create_test_client

@pytest.mark.asyncio
async def test_get_all_clients(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_client1 = {**create_test_client(), "user_id": ObjectId(user_id)}
    test_client2 = {**create_test_client(), "user_id": ObjectId(user_id), "name": "Test Client 2"}
    await mock_db.clients.insert_many([test_client1, test_client2])
    
    # Act
    result = await get_all_clients(user_id)
    
    # Assert
    assert len(result) == 2
    assert result[0].name == "Test Client 2"  # Most recent first
    assert result[1].name == "Test Client"

@pytest.mark.asyncio
async def test_get_client(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_client = {**create_test_client(), "user_id": ObjectId(user_id)}
    result = await mock_db.clients.insert_one(test_client)
    client_id = str(result.inserted_id)
    
    # Act
    client = await get_client(client_id, user_id)
    
    # Assert
    assert client is not None
    assert client.name == test_client["name"]
    assert client.email == test_client["email"]
    assert str(client.user_id) == user_id

@pytest.mark.asyncio
async def test_get_client_not_found(mock_db):
    # Arrange
    user_id = str(ObjectId())
    client_id = str(ObjectId())
    
    # Act
    client = await get_client(client_id, user_id)
    
    # Assert
    assert client is None

@pytest.mark.asyncio
async def test_create_client(mock_db):
    # Arrange
    user_id = str(ObjectId())
    client_data = ClientCreate(
        name="New Client",
        email="newclient@example.com",
        phone="1234567890",
        address="New Address"
    )
    
    # Act
    result = await create_client(client_data, user_id)
    
    # Assert
    assert result is not None
    assert result.name == client_data.name
    assert result.email == client_data.email
    assert result.phone == client_data.phone
    assert str(result.user_id) == user_id

@pytest.mark.asyncio
async def test_update_client(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_client = {**create_test_client(), "user_id": ObjectId(user_id)}
    result = await mock_db.clients.insert_one(test_client)
    client_id = str(result.inserted_id)
    
    update_data = ClientUpdate(
        name="Updated Client",
        phone="9876543210"
    )
    
    # Act
    updated_client = await update_client(client_id, update_data, user_id)
    
    # Assert
    assert updated_client.name == update_data.name
    assert updated_client.phone == update_data.phone
    assert updated_client.email == test_client["email"]  # Unchanged field

@pytest.mark.asyncio
async def test_delete_client_with_no_schedules(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_client = {**create_test_client(), "user_id": ObjectId(user_id)}
    result = await mock_db.clients.insert_one(test_client)
    client_id = str(result.inserted_id)
    
    # Act
    result = await delete_client(client_id, user_id)
    
    # Assert
    assert result["success"] is True
    assert result["message"] == "Client deleted successfully"
    assert await mock_db.clients.find_one({"_id": ObjectId(client_id)}) is None

@pytest.mark.asyncio
async def test_delete_client_with_schedules(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_client = {**create_test_client(), "user_id": ObjectId(user_id)}
    client_result = await mock_db.clients.insert_one(test_client)
    client_id = str(client_result.inserted_id)
    
    # Create a schedule for this client
    await mock_db.schedules.insert_one({
        "user_id": ObjectId(user_id),
        "client_id": ObjectId(client_id),
        "date": datetime.utcnow()
    })
    
    # Act
    result = await delete_client(client_id, user_id)
    
    # Assert
    assert result["success"] is False
    assert result["message"] == "Cannot delete client with associated schedules"
    assert await mock_db.clients.find_one({"_id": ObjectId(client_id)}) is not None

@pytest.mark.asyncio
async def test_get_client_schedules(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_client = {**create_test_client(), "user_id": ObjectId(user_id)}
    client_result = await mock_db.clients.insert_one(test_client)
    client_id = str(client_result.inserted_id)
    
    # Create a project and schedule for this client
    project = {
        "user_id": ObjectId(user_id),
        "client_id": ObjectId(client_id),
        "name": "Test Project"
    }
    project_result = await mock_db.projects.insert_one(project)
    
    schedule = {
        "user_id": ObjectId(user_id),
        "project_id": project_result.inserted_id,
        "date": datetime.utcnow()
    }
    await mock_db.schedules.insert_one(schedule)
    
    # Act
    result = await get_client_schedules(client_id, user_id)
    
    # Assert
    assert result["client"] is not None
    assert result["client"]["name"] == test_client["name"]
    assert len(result["schedules"]) == 1
    assert str(result["schedules"][0]["user_id"]) == user_id

@pytest.mark.asyncio
async def test_get_client_stats(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_client = {**create_test_client(), "user_id": ObjectId(user_id)}
    client_result = await mock_db.clients.insert_one(test_client)
    client_id = str(client_result.inserted_id)
    
    # Act
    result = await get_client_stats(client_id, user_id)
    
    # Assert
    assert isinstance(result, dict)
    # Note: The actual stats calculation would depend on your implementation