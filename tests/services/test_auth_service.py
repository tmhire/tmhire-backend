import pytest
from datetime import datetime, timedelta
from bson import ObjectId
from app.services.auth_service import (
    get_user_by_email,
    get_user,
    create_user,
    update_user_data,
    hash_password,
    verify_password,
    create_access_token
)
from app.models.user import UserCreate, UserUpdate
from fastapi import HTTPException
from tests.utils.test_fixtures import create_test_user

@pytest.mark.asyncio
async def test_get_user_by_email(mock_db):
    # Arrange
    test_user = create_test_user()
    await mock_db.users.insert_one(test_user)
    
    # Act
    result = await get_user_by_email(test_user["email"])
    
    # Assert
    assert result is not None
    assert result.email == test_user["email"]
    assert result.full_name == test_user["full_name"]

@pytest.mark.asyncio
async def test_get_user_by_email_not_found(mock_db):
    # Act
    result = await get_user_by_email("nonexistent@example.com")
    
    # Assert
    assert result is None

@pytest.mark.asyncio
async def test_get_user(mock_db):
    # Arrange
    test_user = create_test_user()
    result = await mock_db.users.insert_one(test_user)
    user_id = str(result.inserted_id)
    
    # Act
    user = await get_user(user_id)
    
    # Assert
    assert user is not None
    assert user.email == test_user["email"]
    assert user.full_name == test_user["full_name"]

@pytest.mark.asyncio
async def test_get_user_not_found(mock_db):
    # Act & Assert
    user = await get_user(str(ObjectId()))
    assert user is None

@pytest.mark.asyncio
async def test_create_user(mock_db):
    # Arrange
    user_data = UserCreate(
        email="new@example.com",
        password="testpassword",
        full_name="New User",
        role="user"
    )
    
    # Act
    result = await create_user(user_data)
    
    # Assert
    assert result is not None
    assert result.email == user_data.email
    assert result.full_name == user_data.full_name
    assert result.role == user_data.role
    
    # Verify password is hashed
    db_user = await mock_db.users.find_one({"email": user_data.email})
    assert verify_password("testpassword", db_user["password"])

@pytest.mark.asyncio
async def test_create_user_already_exists(mock_db):
    # Arrange
    test_user = create_test_user()
    await mock_db.users.insert_one(test_user)
    user_data = UserCreate(
        email=test_user["email"],
        password="newpassword",
        full_name="New Name",
        role="user"
    )
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await create_user(user_data)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "User already exists"

@pytest.mark.asyncio
async def test_update_user_data(mock_db):
    # Arrange
    test_user = create_test_user()
    result = await mock_db.users.insert_one(test_user)
    user_id = str(result.inserted_id)
    
    update_data = UserUpdate(
        full_name="Updated Name",
        contact="9876543210",
        company="New Company",
        city="New City"
    )
    
    # Act
    updated_user = await update_user_data(user_id, update_data)
    
    # Assert
    assert updated_user.full_name == update_data.full_name
    assert updated_user.contact == update_data.contact
    assert updated_user.company == update_data.company
    assert updated_user.city == update_data.city
    assert updated_user.new_user is False

def test_hash_password():
    # Arrange
    password = "testpassword"
    
    # Act
    hashed = hash_password(password)
    
    # Assert
    assert hashed != password
    assert verify_password(password, hashed)

def test_verify_password():
    # Arrange
    password = "testpassword"
    hashed = hash_password(password)
    
    # Act & Assert
    assert verify_password(password, hashed)
    assert not verify_password("wrongpassword", hashed)

def test_create_access_token():
    # Arrange
    data = {"sub": "test@example.com"}
    expires = timedelta(minutes=15)
    
    # Act
    token = create_access_token(data, expires)
    
    # Assert
    assert token is not None
    assert isinstance(token, str)