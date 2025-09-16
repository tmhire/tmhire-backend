import pytest
import asyncio
from mongomock_motor import AsyncMongoMockClient
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.testclient import TestClient
from app.main import app
import app.db.mongodb as mongodb
from unittest.mock import patch, MagicMock

@pytest.fixture(scope="session")
def event_loop():
    """Create a new event loop for each test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
def mock_client():
    """Create a mock MongoDB client."""
    client = AsyncMongoMockClient()
    return client

@pytest.fixture(scope="function")
def mock_db(mock_client):
    """Set up database with mock collections."""
    database = mock_client["test_db"]

    # Apply patches
    with patch('app.services.pump_service.pumps', database.pumps), \
         patch('app.services.team_service.team', database.team), \
         patch('app.db.mongodb.pumps', database.pumps), \
         patch('app.db.mongodb.team', database.team):
        yield database

@pytest.fixture
def test_app():
    """Get a FastAPI test client."""
    client = TestClient(app)
    return client

@pytest.fixture
def mock_current_user():
    """Mock an authenticated user for testing."""
    return {
        "id": "test_user_id",
        "email": "test@example.com",
        "full_name": "Test User",
        "disabled": False,
        "role": "admin"
    }