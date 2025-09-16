import pytest
from datetime import datetime
from bson import ObjectId
from app.services.project_service import (
    get_all_projects,
    get_project,
    create_project,
    update_project,
    delete_project
)
from app.models.project import ProjectCreate, ProjectUpdate
from tests.utils.test_fixtures import create_test_project, create_test_client, create_test_plant, create_test_team

@pytest.mark.asyncio
async def test_get_all_projects(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_project1 = {**create_test_project(), "user_id": ObjectId(user_id)}
    test_project2 = {**create_test_project(), "user_id": ObjectId(user_id), "name": "Test Project 2"}
    await mock_db.projects.insert_many([test_project1, test_project2])
    
    # Act
    result = await get_all_projects(user_id)
    
    # Assert
    assert len(result) == 2
    assert result[0].name == "Test Project 2"  # Most recent first
    assert result[1].name == "Test Project"

@pytest.mark.asyncio
async def test_get_project(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_project = {**create_test_project(), "user_id": ObjectId(user_id)}
    result = await mock_db.projects.insert_one(test_project)
    project_id = str(result.inserted_id)
    
    # Act
    project = await get_project(project_id, user_id)
    
    # Assert
    assert project is not None
    assert project.name == test_project["name"]
    assert str(project.user_id) == user_id

@pytest.mark.asyncio
async def test_get_project_not_found(mock_db):
    # Arrange
    user_id = str(ObjectId())
    project_id = str(ObjectId())
    
    # Act
    project = await get_project(project_id, user_id)
    
    # Assert
    assert project is None

@pytest.mark.asyncio
async def test_create_project(mock_db):
    # Arrange
    user_id = str(ObjectId())
    
    # Create required related entities
    test_client = {**create_test_client(), "user_id": ObjectId(user_id)}
    client_result = await mock_db.clients.insert_one(test_client)
    
    test_plant = {**create_test_plant(), "user_id": ObjectId(user_id)}
    plant_result = await mock_db.plants.insert_one(test_plant)
    
    test_team = {**create_test_team(), "user_id": ObjectId(user_id)}
    team_result = await mock_db.teams.insert_one(test_team)
    
    project_data = ProjectCreate(
        name="New Project",
        client_id=str(client_result.inserted_id),
        mother_plant_id=str(plant_result.inserted_id),
        sales_engineer_id=str(team_result.inserted_id),
        status="active",
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow()
    )
    
    # Act
    result = await create_project(project_data, user_id)
    
    # Assert
    assert result is not None
    assert result.name == project_data.name
    assert str(result.client_id) == str(project_data.client_id)
    assert str(result.mother_plant_id) == str(project_data.mother_plant_id)
    assert str(result.sales_engineer_id) == str(project_data.sales_engineer_id)
    assert result.status == project_data.status

@pytest.mark.asyncio
async def test_create_project_invalid_client(mock_db):
    # Arrange
    user_id = str(ObjectId())
    
    test_plant = {**create_test_plant(), "user_id": ObjectId(user_id)}
    plant_result = await mock_db.plants.insert_one(test_plant)
    
    test_team = {**create_test_team(), "user_id": ObjectId(user_id)}
    team_result = await mock_db.teams.insert_one(test_team)
    
    project_data = ProjectCreate(
        name="New Project",
        client_id=str(ObjectId()),  # Invalid client ID
        mother_plant_id=str(plant_result.inserted_id),
        sales_engineer_id=str(team_result.inserted_id),
        status="active",
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow()
    )
    
    # Act & Assert
    with pytest.raises(ValueError, match="Client ID does not exist"):
        await create_project(project_data, user_id)

@pytest.mark.asyncio
async def test_update_project(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_project = {**create_test_project(), "user_id": ObjectId(user_id)}
    result = await mock_db.projects.insert_one(test_project)
    project_id = str(result.inserted_id)
    
    # Create new client for update
    test_client = {**create_test_client(), "user_id": ObjectId(user_id)}
    client_result = await mock_db.clients.insert_one(test_client)
    
    # Create new team member for update
    test_team = {**create_test_team(), "user_id": ObjectId(user_id)}
    team_result = await mock_db.teams.insert_one(test_team)
    
    update_data = ProjectUpdate(
        name="Updated Project",
        client_id=str(client_result.inserted_id),
        sales_engineer_id=str(team_result.inserted_id),
        status="completed"
    )
    
    # Act
    updated_project = await update_project(project_id, update_data, user_id)
    
    # Assert
    assert updated_project.name == update_data.name
    assert str(updated_project.client_id) == str(update_data.client_id)
    assert updated_project.status == update_data.status

@pytest.mark.asyncio
async def test_delete_project_with_no_schedules(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_project = {**create_test_project(), "user_id": ObjectId(user_id)}
    result = await mock_db.projects.insert_one(test_project)
    project_id = str(result.inserted_id)
    
    # Act
    result = await delete_project(project_id, user_id)
    
    # Assert
    assert result["success"] is True
    assert result["message"] == "Project deleted successfully"
    assert await mock_db.projects.find_one({"_id": ObjectId(project_id)}) is None

@pytest.mark.asyncio
async def test_delete_project_with_schedules(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_project = {**create_test_project(), "user_id": ObjectId(user_id)}
    project_result = await mock_db.projects.insert_one(test_project)
    project_id = str(project_result.inserted_id)
    
    # Create a schedule for this project
    await mock_db.schedules.insert_one({
        "user_id": ObjectId(user_id),
        "project_id": ObjectId(project_id),
        "date": datetime.utcnow()
    })
    
    # Act
    result = await delete_project(project_id, user_id)
    
    # Assert
    assert result["success"] is False
    assert result["message"] == "Cannot delete project with associated schedules"
    assert await mock_db.projects.find_one({"_id": ObjectId(project_id)}) is not None