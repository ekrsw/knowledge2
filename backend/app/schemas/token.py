from pydantic import BaseModel, field_validator
from datetime import datetime, date
from typing import List, Optional
from uuid import UUID
from app.models import StatusEnum, ChangeTypeEnum


class Token(BaseModel):
    access_token: str
    token_type: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class RefreshTokenRequest(BaseModel):
    access_token: str
    refresh_token: str

class LogoutRequest(BaseModel):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None

class RefreshTokenCreate(BaseModel):
    token: str
    user_id: UUID
    expires_at: datetime

class TokenBlacklistCreate(BaseModel):
    jti: str
    expires_at: datetime
