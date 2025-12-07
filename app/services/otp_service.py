from bson import ObjectId
from app.db.mongodb import password_reset_otps
from app.models.otp import PasswordResetOTPModel
from datetime import datetime, timedelta
from typing import Optional
import secrets
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Maximum number of OTP verification attempts
MAX_OTP_ATTEMPTS = 5
# OTP expiration time in minutes
OTP_EXPIRY_MINUTES = 10

def generate_otp() -> str:
    """Generate a 6-digit numeric OTP"""
    return f"{secrets.randbelow(10**6):06d}"

def hash_otp(otp: str) -> str:
    """Hash an OTP using bcrypt"""
    return pwd_context.hash(otp)

def verify_otp(plain_otp: str, hashed_otp: str) -> bool:
    """Verify an OTP against its hash"""
    return pwd_context.verify(plain_otp, hashed_otp)

async def create_otp(user_id: ObjectId, email: str) -> tuple[str, PasswordResetOTPModel]:
    """
    Create a new OTP for password reset.
    Returns: (raw_otp, otp_model)
    """
    # Generate OTP
    raw_otp = generate_otp()
    otp_hash = hash_otp(raw_otp)
    
    # Set expiration time
    expires_at = datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)
    
    # Create OTP document
    otp_data = {
        "user_id": user_id,
        "email": email,
        "otp_hash": otp_hash,
        "expires_at": expires_at,
        "used": False,
        "attempts_count": 0,
        "created_at": datetime.utcnow()
    }
    
    # Insert into database
    result = await password_reset_otps.insert_one(otp_data)
    otp_doc = await password_reset_otps.find_one({"_id": result.inserted_id})
    
    return raw_otp, PasswordResetOTPModel(**otp_doc)

async def get_latest_valid_otp(user_id: ObjectId, email: str) -> Optional[PasswordResetOTPModel]:
    """
    Get the latest valid (unused, not expired) OTP for a user.
    Returns None if no valid OTP exists.
    """
    now = datetime.utcnow()
    
    # Find the latest OTP that is not used and not expired
    otp_doc = await password_reset_otps.find_one(
        {
            "user_id": user_id,
            "email": email,
            "used": False,
            "expires_at": {"$gt": now}
        },
        sort=[("created_at", -1)]  # Get the most recent one
    )
    
    if otp_doc:
        return PasswordResetOTPModel(**otp_doc)
    return None

async def increment_otp_attempts(otp_id: ObjectId) -> None:
    """Increment the attempts_count for an OTP"""
    await password_reset_otps.update_one(
        {"_id": otp_id},
        {"$inc": {"attempts_count": 1}}
    )

async def mark_otp_as_used(otp_id: ObjectId) -> None:
    """Mark an OTP as used"""
    await password_reset_otps.update_one(
        {"_id": otp_id},
        {"$set": {"used": True}}
    )

async def invalidate_user_otps(user_id: ObjectId, email: str) -> None:
    """
    Invalidate all unused OTPs for a user when a new one is created.
    This prevents multiple valid OTPs from existing at the same time.
    """
    await password_reset_otps.update_many(
        {
            "user_id": user_id,
            "email": email,
            "used": False
        },
        {"$set": {"used": True}}
    )

