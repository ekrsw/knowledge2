from pydantic import BaseModel, field_validator
from datetime import datetime, date
from typing import List, Optional
from uuid import UUID
from app.models import StatusEnum, ChangeTypeEnum


# User関連のスキーマ
class UserBase(BaseModel):
    username: str
    full_name: str

class UserCreate(UserBase):
    password: str
    is_admin: Optional[bool] = False

class UserRegister(UserBase):
    """ユーザー登録用のスキーマ（管理者権限は含まない）"""
    password: str
    # is_adminフィールドは意図的に除外してセキュリティを確保

class UserUpdate(BaseModel):
    username: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_admin: Optional[bool] = None

class PasswordUpdate(BaseModel):
    old_password: str
    new_password: str

class User(UserBase):
    id: UUID
    is_admin: bool
    
    class Config:
        from_attributes = True
