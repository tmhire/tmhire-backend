from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional
from app.db.mongodb import PyObjectId
from bson import ObjectId

class PasswordResetOTPModel(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId = Field(description="Reference to the user")
    email: EmailStr = Field(description="User email")
    otp_hash: str = Field(description="Hashed OTP")
    expires_at: datetime = Field(description="OTP expiration time")
    used: bool = Field(default=False, description="Whether the OTP has been used")
    attempts_count: int = Field(default=0, description="Number of verification attempts")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "user_id": "507f1f77bcf86cd799439011",
                "email": "user@example.com",
                "otp_hash": "$2b$12$...",
                "expires_at": datetime.utcnow(),
                "used": False,
                "attempts_count": 0,
                "created_at": datetime.utcnow()
            }
        }
    )

class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com"
            }
        }
    )

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(description="6-digit OTP")
    new_password: str = Field(description="New password")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "otp": "123456",
                "new_password": "NewStrongPassword!23"
            }
        }
    )

