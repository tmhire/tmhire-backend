from bson import ObjectId
from app.db.mongodb import users
from app.models.user import UserModel, UserCreate, UserUpdate
from datetime import datetime, timedelta
from typing import Optional
import os
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google.oauth2 import id_token
from google.auth.transport import requests
from passlib.context import CryptContext


# Use HTTPBearer instead of OAuth2PasswordBearer
security = HTTPBearer()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY", "placeholder_secret_key")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440
REFRESH_TOKEN_EXPIRE_DAYS = 30

async def get_user_by_email(email: str) -> Optional[UserModel]:
    """Get a user by email"""
    user = await users.find_one({"email": email})
    if user:
        return UserModel(**user)
    return None

async def get_user(id: str) -> Optional[UserModel]:
    """Get a user by email"""
    user = await users.find_one({"_id": ObjectId(id)})
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
        print("User already exists")
        if user_data["password"]:
            print("Throwing error because of signup process")
            raise HTTPException(status_code=400, detail="User already exists")
        return UserModel(**existing_user)
    
    if "password" in user_data and user_data["password"]:
        user_data["password"] = hash_password(user_data["password"])
    
    # Insert new user
    result = await users.insert_one(user_data)
    new_user = await users.find_one({"_id": result.inserted_id})
    return UserModel(**new_user)

async def update_user_data(user_id: str, user: UserUpdate):
    """Update a user"""
    user_data = {k: v for k, v in user.model_dump().items() if v is not None}
    
    if "password" in user_data and user_data["password"]:
        user_data["password"] = hash_password(user_data["password"])

    existing_user = (await get_user(user_id)).model_dump()
    isNewUser = True
    if all(
        key in existing_user and existing_user[key] is not None
        for key in ["contact", "company", "city"]
    ):
        isNewUser = False
    user_data["new_user"] = isNewUser

    updated_user = {**existing_user, **user_data}

    #Update user
    await users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": updated_user}
    )
    
    return await get_user(user_id)

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT refresh token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def refreshing_access_token(refresh_token):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type"
            )

        user_email = payload.get("sub")
        if user_email is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        # You could check a DB/cached list of valid refresh tokens here

        new_access_token = create_access_token(
            data={"sub": user_email},
            expires_delta=timedelta(minutes=1440)
        )
        
        new_refresh_token = create_refresh_token(
            data={"sub": user_email},
            expires_delta=timedelta(days=30)
        )

        return new_access_token, new_refresh_token

    except JWTError as e:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")


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
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Expected access token")
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

    except ValueError as e:
        print("ValueError in token verification:", e)
    except Exception as e:
        print("Unknown error in token verification:", e)