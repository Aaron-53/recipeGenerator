from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema"""

    username: str = Field(..., min_length=3, max_length=50)


class UserCreate(UserBase):
    """Schema for user registration"""

    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    """Schema for user login"""

    username: str
    password: str


class UserResponse(UserBase):
    """Schema for user response"""

    user_id: str
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class UserInDB(UserBase):
    """Schema for user in database"""

    user_id: str
    hashed_password: str
    is_active: bool = True
    created_at: datetime


class Token(BaseModel):
    """Schema for authentication token"""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for token data"""

    username: Optional[str] = None
    user_id: Optional[str] = None


class GoogleAuth(BaseModel):
    """Schema for Google authentication"""

    token: str


class GoogleUserInfo(BaseModel):
    """Schema for Google user information"""

    email: str
    name: str
    picture: Optional[str] = None
    google_id: str
