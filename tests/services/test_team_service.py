import pytest
from datetime import datetime
from bson import ObjectId
from app.services.team_service import (
    get_all_teams,
    get_team_member,
    get_team_group,
    create_team_member,
    update_team_member,
    delete_team_member,
    groupSet
)
from app.models.team import TeamMemberCreate, TeamMemberUpdate
from tests.utils.test_fixtures import create_test_team

@pytest.mark.asyncio
async def test_get_all_teams(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_member1 = {**create_test_team(), "user_id": ObjectId(user_id)}
    test_member2 = {**create_test_team(), "user_id": ObjectId(user_id), "name": "Team Member 2"}
    await mock_db.team.insert_many([test_member1, test_member2])
    
    # Act
    result = await get_all_teams(user_id)
    
    # Assert
    assert len(result) == 2
    assert result[0].name == "Team Member 2"  # Most recent first
    assert result[1].name == "Test Team"

@pytest.mark.asyncio
async def test_get_team_member(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_member = {**create_test_team(), "user_id": ObjectId(user_id)}
    result = await mock_db.team.insert_one(test_member)
    member_id = str(result.inserted_id)
    
    # Act
    member = await get_team_member(member_id, user_id)
    
    # Assert
    assert member is not None
    assert member.name == test_member["name"]
    assert member.role == test_member["role"]
    assert str(member.user_id) == user_id

@pytest.mark.asyncio
async def test_get_team_member_not_found(mock_db):
    # Arrange
    user_id = str(ObjectId())
    member_id = str(ObjectId())
    
    # Act
    member = await get_team_member(member_id, user_id)
    
    # Assert
    assert member is None

@pytest.mark.asyncio
async def test_get_team_member_null_id(mock_db):
    # Arrange
    user_id = str(ObjectId())
    
    # Act
    member = await get_team_member(None, user_id)
    
    # Assert
    assert member is None

@pytest.mark.asyncio
async def test_get_team_group_client(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_member = {
        **create_test_team(),
        "user_id": ObjectId(user_id),
        "designation": "sales-engineer"
    }
    await mock_db.team.insert_one(test_member)
    
    # Act
    result = await get_team_group("client", user_id)
    
    # Assert
    assert len(result) == 1
    assert result[0].designation == "sales-engineer"

@pytest.mark.asyncio
async def test_get_team_group_pump(mock_db):
    # Arrange
    user_id = str(ObjectId())
    pump_operator = {
        **create_test_team(),
        "user_id": ObjectId(user_id),
        "designation": "pump-operator"
    }
    pipeline_gang = {
        **create_test_team(),
        "user_id": ObjectId(user_id),
        "designation": "pipeline-gang"
    }
    await mock_db.team.insert_many([pump_operator, pipeline_gang])
    
    # Act
    result = await get_team_group("pump", user_id)
    
    # Assert
    assert len(result) == 2
    assert set(m.designation for m in result) == {"pump-operator", "pipeline-gang"}

@pytest.mark.asyncio
async def test_create_team_member(mock_db):
    # Arrange
    user_id = str(ObjectId())
    member_data = TeamMemberCreate(
        name="New Team Member",
        designation="pump-operator",
        contact=9876543210  # Should be integer
    )
    
    # Act
    result = await create_team_member(member_data, user_id)
    
    # Assert
    assert result is not None
    assert result.name == member_data.name
    assert result.designation == member_data.designation
    assert result.contact == member_data.contact
    assert str(result.user_id) == user_id

@pytest.mark.asyncio
async def test_update_team_member(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_member = {**create_test_team(), "user_id": ObjectId(user_id)}
    result = await mock_db.team.insert_one(test_member)
    member_id = str(result.inserted_id)
    
    update_data = TeamMemberUpdate(
        name="Updated Name",
        contact=9876543210  # Should be integer
    )
    
    # Act
    updated_member = await update_team_member(member_id, update_data, user_id)
    
    # Assert
    assert updated_member.name == update_data.name
    assert updated_member.contact == update_data.contact
    assert updated_member.role == test_member["role"]  # Unchanged field

@pytest.mark.asyncio
async def test_delete_team_member(mock_db):
    # Arrange
    user_id = str(ObjectId())
    test_member = {**create_test_team(), "user_id": ObjectId(user_id)}
    result = await mock_db.team.insert_one(test_member)
    member_id = str(result.inserted_id)
    
    # Act
    success = await delete_team_member(member_id, user_id)
    
    # Assert
    assert success["success"] is True
    assert await mock_db.team.find_one({"_id": ObjectId(member_id)}) is None

@pytest.mark.asyncio
async def test_delete_team_member_not_found(mock_db):
    # Arrange
    user_id = str(ObjectId())
    member_id = str(ObjectId())
    
    # Act
    result = await delete_team_member(member_id, user_id)
    
    # Assert
    assert result["success"] is False

def test_group_set_structure():
    # Test that the group set has the correct structure
    assert "client" in groupSet
    assert "pump" in groupSet
    assert "schedule" in groupSet
    
    assert "sales-engineer" in groupSet["client"]
    assert set(groupSet["pump"]) == {"pump-operator", "pipeline-gang"}
    assert "site-supervisor" in groupSet["schedule"]