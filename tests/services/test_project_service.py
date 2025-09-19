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
async def test_get_project_not_found(mock_db):
    # Arrange
    user_id = str(ObjectId())
    project_id = str(ObjectId())
    
    # Act
    project = await get_project(project_id, user_id)
    
    # Assert
    assert project is None



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

