import pytest
import asyncio
import contextlib
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

    # Apply patches for all services that use MongoDB collections
    patches = [
        ('app.services.auth_service.users', database.users),
        ('app.services.pump_service.pumps', database.pumps),
        ('app.services.team_service.team', database.team),
        ('app.services.client_service.clients', database.clients),
        ('app.services.client_service.projects', database.projects),
        ('app.services.client_service.schedules', database.schedules),
        ('app.services.plant_service.plants', database.plants),
        ('app.services.project_service.projects', database.projects),
        ('app.services.schedule_calendar_service.schedule_calendar', database.schedule_calendar),
        ('app.services.schedule_service.schedules', database.schedules),
        ('app.services.tm_service.transit_mixers', database.transit_mixers),
        ('app.db.mongodb.users', database.users),
        ('app.db.mongodb.pumps', database.pumps),
        ('app.db.mongodb.team', database.team),
        ('app.db.mongodb.clients', database.clients),
        ('app.db.mongodb.plants', database.plants),
        ('app.db.mongodb.projects', database.projects),
        ('app.db.mongodb.schedule_calendar', database.schedule_calendar),
        ('app.db.mongodb.schedules', database.schedules),
        ('app.db.mongodb.transit_mixers', database.transit_mixers)
    ]
    
    # Create a context manager chain
    with contextlib.ExitStack() as stack:
        # Apply all patches
        for target, replacement in patches:
            stack.enter_context(patch(target, replacement))
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