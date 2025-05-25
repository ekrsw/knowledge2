from datetime import datetime, timedelta, UTC
import json
import secrets
from typing import Dict, Any, Optional
import uuid

from passlib.context import CryptContext
from jose import jwt, JWTError

from app.core.config import settings
from app.core.logging import app_logger


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)