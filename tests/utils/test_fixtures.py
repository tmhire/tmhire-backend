import pytest
from datetime import datetime

def create_test_user():
    return {
        "id": "test_user_id",
        "email": "test@example.com",
        "password": "test_password",
        "full_name": "Test User",
        "role": "admin",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

def create_test_client():
    return {
        "id": "test_client_id",
        "name": "Test Client",
        "email": "client@example.com",
        "phone": "1234567890",
        "address": "Test Address",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

def create_test_project():
    return {
        "id": "test_project_id",
        "name": "Test Project",
        "client_id": "test_client_id",
        "status": "active",
        "start_date": datetime.utcnow(),
        "end_date": datetime.utcnow(),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

def create_test_team():
    return {
        "name": "Test Team",
        "designation": "pump-operator",
        "contact": 1234567890,  # Should be an integer
        "created_at": datetime.utcnow()
    }

def create_test_plant():
    return {
        "id": "test_plant_id",
        "name": "Test Plant",
        "location": "Test Location",
        "capacity": 100,
        "status": "active",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }