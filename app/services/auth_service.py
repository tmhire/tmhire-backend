from app.db.mongodb import users
from app.models.user import UserModel, UserCreate
from datetime import datetime, timedelta
from typing import Optional
import os
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google.oauth2 import id_token
from google.auth.transport import requests

# Use HTTPBearer instead of OAuth2PasswordBearer
security = HTTPBearer()

# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY", "placeholder_secret_key")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

async def get_user_by_email(email: str) -> Optional[UserModel]:
    """Get a user by email"""
    user = await users.find_one({"email": email})
    if user:
        return UserModel(**user)
    return None

async def create_user(user: UserCreate) -> UserModel:
    """Create a new user"""
    user_data = user.model_dump()
    user_data["created_at"] = datetime.utcnow()
    
    # Check if user already exists
    existing_user = await users.find_one({"email": user_data["email"]})
    if existing_user:
        return UserModel(**existing_user)
    
    # Insert new user
    result = await users.insert_one(user_data)
    new_user = await users.find_one({"_id": result.inserted_id})
    return UserModel(**new_user)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserModel:
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await get_user_by_email(email)
    if user is None:
        raise credentials_exception
    return user

async def validate_google_token(token: str) -> dict:
    """
    Validate Google ID token using Google's OAuth2 API and extract user info.

    Args:
        token (str): Google ID token from client.

    Returns:
        dict: Dictionary containing user's email and name.

    Raises:
        HTTPException: If token is invalid or verification fails.
    """
    print("token",token)
    try:
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)
        print("idinfo",idinfo)

        # Check if the token is issued to your app
        if idinfo['aud'] != GOOGLE_CLIENT_ID:
            raise HTTPException(status_code=401, detail="Invalid audience")

        return {
            "email": idinfo.get("email"),
            "name": idinfo.get("name")
        }

    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google token")