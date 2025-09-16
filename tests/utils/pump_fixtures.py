from datetime import datetime
from bson import ObjectId

def create_test_pump(user_id, plant_id, identifier="PUMP-001", capacity=50.0, pump_type="line"):
    """Create a test pump fixture."""
    return {
        "user_id": user_id,
        "plant_id": plant_id,
        "identifier": identifier,
        "capacity": capacity,
        "type": pump_type,
        "status": "active",
        "make": "Test Make",
        "driver_name": "Test Driver",
        "driver_contact": "+1234567890",
        "pump_operator_id": ObjectId(),
        "pipeline_gang_id": ObjectId(),
        "remarks": "Test pump",
        "created_at": datetime.utcnow()
    }