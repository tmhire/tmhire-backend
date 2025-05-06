from fastapi import APIRouter, HTTPException, status
from app.models.user import UserModel, UserCreate
from app.services.auth_service import create_user, create_access_token, validate_google_token
from datetime import timedelta
from typing import Dict
from pydantic import BaseModel

router = APIRouter()

class GoogleToken(BaseModel):
    token: str

class Token(BaseModel):
    access_token: str
    token_type: str

@router.post("/google", response_model=Token)
async def login_google(token_data: GoogleToken):
    """
    Google SSO login endpoint.
    
    Expects a Google ID token in the request body.
    Returns a JWT token for API authentication.
    """
    print("token_data",token_data)
    try:
        # Validate the Google token
        user_data = await validate_google_token(token_data.token)
        
        # Create user if doesn't exist
        user = await create_user(UserCreate(
            email=user_data["email"],
            name=user_data["name"]
        ))
        
        # Create access token
        access_token = create_access_token(
            data={"sub": user.email},
            expires_delta=timedelta(minutes=30)
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e) or "Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) 