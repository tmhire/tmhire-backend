from typing import Literal, Union
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.company import CompanyCreate, CompanyModel
from app.models.user import CompanyUserModel, UserLogin, UserModel, UserCreate, UserUpdate
from app.models.otp import ForgotPasswordRequest, VerifyOTPRequest
from app.services.auth_service import create_refresh_token, create_user, create_access_token, get_current_user, get_user_by_email, onboard_user, refreshing_access_token, update_user_data, validate_google_token, verify_password, hash_password
from app.services.otp_service import (
    create_otp, get_latest_valid_otp, increment_otp_attempts, 
    mark_otp_as_used, invalidate_user_otps, verify_otp, MAX_OTP_ATTEMPTS
)
from app.services.email_service import send_otp_email
from app.db.mongodb import users
from bson import ObjectId
from datetime import datetime, timedelta
from pydantic import BaseModel
from app.schemas.response import StandardResponse
from app.services.company_service import get_company

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
    company: Union[str, None]
    city: Union[str, None]
    contact: Union[int, None]
    
    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyQGV4YW1wbGUuY29tIiwiZXhwIjoxNjI1MTcyODAwfQ.signature",
                "token_type": "bearer"
            }
        }

class User(CompanyUserModel):
    id: str
    name: str
    email: str
    new_user: bool
    contact: Union[int, None]
    company_id: Union[str, None] = None
    role: Union[Literal["super_admin", "company_admin", "user"], None] = None
    sub_role: Union[Literal["viewer", "editor"], None] = None
    account_status: Union[Literal["pending", "approved", "revoked"], None] = None
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
                "token_type": "bearer",
                "account_status": user.account_status or "pending",
                "created_at":  user.created_at or datetime.utcnow
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
        
        data = {"sub": user.email}
        company_data = {}
        if user.company_id:
            company = await get_company(str(user.company_id))
            if company:
                company_data = company.model_dump()
                data["company_code"] = company_data["company_code"]
                data["company_name"] = company_data["company_name"]
                for key in ["id", "_id"]:
                    if company_data.get(key, None):
                        del company_data[key]

        access_token = create_access_token(
            data=data,
            expires_delta=timedelta(minutes=1440)
        )
        
        refresh_token = create_refresh_token(
            data=data, 
            expires_delta=timedelta(days=30)
        )
        
        user_data = {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
                "new_user": user.new_user,
                "company_id": str(user.company_id),
                "contact": user.contact,
                "role": user.role,
                "sub_role": user.sub_role,
                "account_status": user.account_status,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                **company_data
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

        user = await get_user_by_email(user_data["email"])        
        if not user:
            # Create user if doesn't exist
            user = await create_user(UserCreate(
                email=user_data["email"],
                name=user_data["name"]
            ))

        company_data = {}
        data={"sub": user.email}
        if user.company_id:
            company = await get_company(str(user.company_id))
            if company:
                company_data = company.model_dump()
                data["company_code"] = company_data["company_code"]
                data["company_name"] = company_data["company_name"]
                for key in ["id", "_id"]:
                    if company_data.get(key, None):
                        del company_data[key]
        
        # Create access token
        access_token = create_access_token(
            data=data,
            expires_delta=timedelta(minutes=1440)
        )
        
        #Create refresh token
        refresh_token = create_refresh_token(
            data=data,
            expires_delta=timedelta(days=30)
        )

        token_data = {
            "new_user": user.new_user,
            "company_id": str(user.company_id) if user.company_id else None,
            "city": getattr(user, "city", None),
            "contact": user.contact,
            "preferred_format": getattr(user, "preferred_format", None),
            "custom_start_hour": getattr(user, "custom_start_hour", None),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            **company_data
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
    
@router.put("/update", response_model=StandardResponse[CompanyUserModel])
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

@router.get("/profile", response_model=StandardResponse[CompanyUserModel])
async def get_profile(current_user: UserModel = Depends(get_current_user)):
    """
    Get the profile information of the currently authenticated user.
    
    Returns:
    - User profile information including name, email, company, city, contact details
    """
    try:
        company_data = {}
        user = current_user.model_dump()
        if user["company_id"]:
            company = await get_company(str(user["company_id"]))
            if company:
                company_data = company.model_dump()
                for key in ["id", "_id"]:
                    if company_data.get(key, None):
                        del company_data[key]
        user["company_id"] = str(user["company_id"])
        return StandardResponse(
            success=True,
            message="Profile retrieved successfully",
            data={**user, **company_data}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e) or "Failed to retrieve profile",
        )

@router.put("/onboard", response_model=StandardResponse[CompanyUserModel])
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


@router.post("/forgot-password/request-otp")
async def request_password_reset_otp(request: ForgotPasswordRequest):
    """
    Request a password reset OTP.
    
    This endpoint:
    1. Checks if a user with the given email exists
    2. If user exists: generates OTP, stores it (hashed), and sends it via email
    3. If user does NOT exist: returns a clear error message
    
    IMPORTANT: This endpoint reveals whether an email is registered or not.
    """
    try:
        # Check if user exists
        user = await get_user_by_email(request.email)
        
        if not user:
            # Explicitly tell the user that the email is not registered
            return StandardResponse(
                success=False,
                message="No account found for this email.",
                data=None
            )
        
        # Invalidate any existing unused OTPs for this user
        await invalidate_user_otps(user.id, request.email)
        
        # Generate and store OTP
        raw_otp, otp_model = await create_otp(user.id, request.email)
        
        # Send OTP via email (this is synchronous but can be moved to background task)
        email_sent = send_otp_email(request.email, raw_otp)
        
        if not email_sent:
            # Log that email sending failed, but don't expose this to the user
            # In production, you might want to queue this for retry
            print(f"Warning: Failed to send OTP email to {request.email}, but OTP was generated: {raw_otp}")
        
        # Always return success message (security: don't reveal if email sending failed)
        return StandardResponse(
            success=True,
            message="OTP sent successfully to your email.",
            data=None
        )
        
    except Exception as e:
        print(f"Error in request_password_reset_otp: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process password reset request",
        )

@router.post("/forgot-password/verify-otp")
async def verify_password_reset_otp(request: VerifyOTPRequest):
    """
    Verify OTP and reset password.
    
    This endpoint:
    1. Validates the email exists
    2. Checks if a valid OTP exists for the user
    3. Verifies the OTP (with attempt limits)
    4. Updates the user's password if OTP is valid
    """
    try:
        # Find user by email
        user = await get_user_by_email(request.email)
        
        if not user:
            return StandardResponse(
                success=False,
                message="No account found for this email.",
                data=None
            )
        
        # Get the latest valid OTP
        otp_model = await get_latest_valid_otp(user.id, request.email)
        
        if not otp_model:
            return StandardResponse(
                success=False,
                message="Invalid or expired OTP.",
                data=None
            )
        
        # Check if attempts exceeded
        if otp_model.attempts_count >= MAX_OTP_ATTEMPTS:
            return StandardResponse(
                success=False,
                message="Too many attempts. Please request a new OTP.",
                data=None
            )
        
        # Verify OTP
        if not verify_otp(request.otp, otp_model.otp_hash):
            # Increment attempts
            await increment_otp_attempts(otp_model.id)
            
            return StandardResponse(
                success=False,
                message="Invalid OTP.",
                data=None
            )
        
        # OTP is valid - update password
        hashed_password = hash_password(request.new_password)
        
        # Update user password
        await users.update_one(
            {"_id": user.id},
            {"$set": {"password": hashed_password, "last_updated": datetime.utcnow()}}
        )
        
        # Mark OTP as used
        await mark_otp_as_used(otp_model.id)
        
        return StandardResponse(
            success=True,
            message="Password has been reset successfully.",
            data=None
        )
        
    except Exception as e:
        print(f"Error in verify_password_reset_otp: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify OTP and reset password",
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
