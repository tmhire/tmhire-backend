from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.company import CompanyCreate, CompanyModel
from app.models.user import UserLogin, UserModel, UserCreate, UserUpdate
from app.services.auth_service import create_refresh_token, create_user, create_access_token, get_current_user, get_user_by_email, onboard_user, refreshing_access_token, update_user_data, validate_google_token, verify_password
from datetime import timedelta
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
    refresh_token: str
    token_type: str
    
    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyQGV4YW1wbGUuY29tIiwiZXhwIjoxNjI1MTcyODAwfQ.signature",
                "token_type": "bearer"
            }
        }

class TokenWithNewUser(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    new_user: bool
    company: str | None
    city: str | None
    contact: int | None
    
    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyQGV4YW1wbGUuY29tIiwiZXhwIjoxNjI1MTcyODAwfQ.signature",
                "token_type": "bearer"
            }
        }

class User(BaseModel):
    id: str
    name: str
    email: str
    new_user: bool
    contact: int | None
    company_id: str | None = None
    role: Literal["super_admin", "company_admin", "user"] | None = None
    sub_role: Literal["viewer", "editor"] | None = None
    status: Literal["pending", "approved", "revoked"] | None = None
    access_token: str
    refresh_token: str
    token_type: str
    
    class Config:
        schema_extra = {
            "example": {
                "id": "Mongoid",
                "name": "Akilan",
                "email": "email@gmail.com",
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyQGV4YW1wbGUuY29tIiwiZXhwIjoxNjI1MTcyODAwfQ.signature",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyQGV4YW1wbGUuY29tIiwiZXhwIjoxNjI1MTcyODAwfQ.signature",
                "token_type": "bearer"
            }
        }

class RefreshTokenRequest(BaseModel):
    refresh_token: str

@router.post("/signup", response_model=StandardResponse[User])
async def signup(user_data: UserCreate):
    try:
        user = await create_user(user_data)

        access_token = create_access_token(
            data={"sub": user.email}, 
            expires_delta=timedelta(minutes=1440)
        )
        
        refresh_token = create_refresh_token(
            data={"sub": user.email}, 
            expires_delta=timedelta(days=30)
        )

        user_data = {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
                "new_user": user.new_user,
                "company_id": str(user.company_id) if user.company_id else None,
                "city": getattr(user, "city", None),
                "contact": user.contact,
                "preferred_format": getattr(user, "preferred_format", None),
                "custom_start_hour": getattr(user, "custom_start_hour", None),
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer"
            }
        
        return StandardResponse(
            success=True,
            message="Authentication successful",
            data=user_data
        )

    except Exception as e:
        print(e)
        raise e


@router.post("/signin", response_model=StandardResponse[User])
async def login_user(user_data: UserLogin):
    try:
        user = await get_user_by_email(user_data.email)
        if not user or not verify_password(user_data.password, user.password):
            print("Incorrect password")
            print(user_data.password, user.password)
            raise HTTPException(status_code=401, detail="Invalid credentials")

        access_token = create_access_token(
            data={"sub": user.email},
            expires_delta=timedelta(minutes=1440)
        )
        
        refresh_token = create_refresh_token(
            data={"sub": user.email}, 
            expires_delta=timedelta(days=30)
        )
        
        user_data = {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
                "new_user": user.new_user,
                "company_id": user.company_id,
                "contact": user.contact,
                "role": user.role,
                "sub_role": user.sub_role,
                "status": user.status,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer"
            }
                
        return StandardResponse(
            success=True,
            message="Authentication successful",
            data=user_data
        )
    
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e) or "Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/google", response_model=StandardResponse[TokenWithNewUser])
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
        
        #Create refresh token
        refresh_token = create_refresh_token(
            data={"sub": user.email},
            expires_delta=timedelta(days=30)
        )

        token_data = {
            "new_user": user.new_user,
            "company": str(user.company_id) if user.company_id else None,
            "city": getattr(user, "city", None),
            "contact": user.contact,
            "preferred_format": getattr(user, "preferred_format", None),
            "custom_start_hour": getattr(user, "custom_start_hour", None),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

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

@router.post("/refresh", response_model=StandardResponse[Token])
async def refresh_access_token(request: RefreshTokenRequest):
    try:
        refresh_token = request.refresh_token
        new_access_token, new_refresh_token = refreshing_access_token(refresh_token)

        return StandardResponse(
            success=True,
            message="Access token refreshed",
            data={
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer"
            }
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e) or "Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
@router.put("/update", response_model=StandardResponse[UserModel])
async def update_user(user_data: UserUpdate, current_user: UserModel = Depends(get_current_user)):
    try:
        user = await update_user_data(current_user.id, user_data, current_user=current_user)
        return StandardResponse(
            success=True,
            message="User updated successfully",
            data=user
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e) or "Failed to update user",
        )

@router.get("/profile", response_model=StandardResponse[UserModel])
async def get_profile(current_user: UserModel = Depends(get_current_user)):
    """
    Get the profile information of the currently authenticated user.
    
    Returns:
    - User profile information including name, email, company, city, contact details
    """
    try:
        return StandardResponse(
            success=True,
            message="Profile retrieved successfully",
            data=current_user
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e) or "Failed to retrieve profile",
        )

@router.put("/onboard", response_model=StandardResponse[UserModel])
async def onboard(company_data: CompanyCreate, current_user: UserModel = Depends(get_current_user)):
    try:
        user = await onboard_user(company=company_data, current_user=current_user)
        return StandardResponse(
            success=True,
            message="User onboarded successfully",
            data=user
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e) or "Failed to update user",
        )


@router.put("/{user_id}", response_model=StandardResponse[UserModel])
async def update_user(user_id: str, user_data: UserUpdate, current_user: UserModel = Depends(get_current_user)):
    try:
        user = await update_user_data(user_id, user_data, current_user)
        return StandardResponse(
            success=True,
            message="User updated successfully",
            data=user
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e) or "Failed to update user",
        )
