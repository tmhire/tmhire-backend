from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional
from app.db.mongodb import PyObjectId
from bson import ObjectId

class UserModel(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    email: EmailStr
    password: Optional[str] = None
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "name": "John Doe",
                "created_at": datetime.utcnow()
            }
        }
    )

class UserCreate(BaseModel):
    email: EmailStr
    password: Optional[str] = None
    name: str
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "name": "John Doe"
            }
        }
    ) 

class UserLogin(BaseModel):
    email: EmailStr
    password: str