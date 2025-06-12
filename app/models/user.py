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
    new_user: bool = Field(default=True, description="Indicates if the user is new")
    contact: Optional[int] = Field(default=None, description="Phone number of the user")
    company: Optional[str] = Field(default=None, description="Company that the user works for")
    city: Optional[str] = Field(default=None, description="Location of the user")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "name": "John Doe",
                "new_user": False,
                "contact": 1234567890,
                "company": "Main Concrete Firm",
                "city": "Coimbatore",
                "created_at": datetime.utcnow()
            }
        }
    )

class UserCreate(BaseModel):
    email: EmailStr
    password: Optional[str] = None
    name: str
    new_user: bool = Field(default=True, description="Indicates if the user is new")
    contact: Optional[int] = Field(default=None, description="Phone number of the user")
    company: Optional[str] = Field(default=None, description="Company that the user works for")
    city: Optional[str] = Field(default=None, description="Location of the user")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "name": "John Doe",
                "new_user": False,
                "contact": 1234567890,
                "company": "Main Concrete Firm",
                "city": "Coimbatore"
            }
        }
    ) 

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    password: Optional[str] = None
    contact: Optional[int] = None
    company: Optional[str] = None
    city: Optional[str] = None
    

