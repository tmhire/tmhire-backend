from jose import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from app.services.auth_service import SECRET_KEY, ALGORITHM

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=15)):
    """Create a test JWT token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_test_auth_headers(user_id: str = "test_user_id"):
    """Get test authorization headers"""
    access_token = create_access_token({"sub": user_id})
    return {"Authorization": f"Bearer {access_token}"}

async def create_test_document(db, collection: str, document: dict):
    """Create a test document in the database"""
    result = await db[collection].insert_one(document)
    return str(result.inserted_id)

async def get_test_document(db, collection: str, document_id: str):
    """Get a test document from the database"""
    return await db[collection].find_one({"_id": document_id})

async def update_test_document(db, collection: str, document_id: str, update_data: dict):
    """Update a test document in the database"""
    await db[collection].update_one(
        {"_id": document_id},
        {"$set": update_data}
    )

async def delete_test_document(db, collection: str, document_id: str):
    """Delete a test document from the database"""
    await db[collection].delete_one({"_id": document_id})