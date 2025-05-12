from fastapi import APIRouter, HTTPException, status
from app.models.user import UserModel, UserCreate
from app.services.auth_service import create_user, create_access_token, validate_google_token
from datetime import timedelta
from typing import Dict
from pydantic import BaseModel
from app.schemas.response import StandardResponse

router = APIRouter(tags=["Authentication"])

class GoogleToken(BaseModel):
    token: str
    
    class Config:
        schema_extra = {
            "example": {
                "token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjFlOWdkazcyOGEwZjhjMDQxNWQzZGQ4ZjNkNGU2OWU1ZDU3YjE0YTEiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJhY2NvdW50cy5nb29nbGUuY29tIiwiYXpwIjoiMjE2Mjk2MDM1"
            }
        }

class Token(BaseModel):
    access_token: str
    token_type: str
    
    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyQGV4YW1wbGUuY29tIiwiZXhwIjoxNjI1MTcyODAwfQ.signature",
                "token_type": "bearer"
            }
        }

@router.post("/google", response_model=StandardResponse[Token])
async def login_google(token_data: GoogleToken):
    """
    Authenticate using Google Single Sign-On.
    
    Request body:
    - token: Google ID token obtained from Google Authentication
    
    This endpoint:
    1. Validates the Google token with Google's authentication service
    2. Creates a new user in the system if they don't already exist
    3. Issues a JWT access token for API authentication
    
    Returns:
    - access_token: JWT token to use for authenticated API requests
    - token_type: Token type (bearer)
    
    The access token should be included in the Authorization header for
    all protected API endpoints: `Authorization: Bearer {access_token}`
    """
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
            expires_delta=timedelta(minutes=1440)
        )
        
        token_data = {"access_token": access_token, "token_type": "bearer"}
        
        return StandardResponse(
            success=True,
            message="Authentication successful",
            data=token_data
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e) or "Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) 