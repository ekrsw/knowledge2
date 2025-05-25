from pydantic import BaseModel, field_validator
from datetime import datetime, date
from typing import List, Optional
from uuid import UUID
from app.models import StatusEnum, ChangeTypeEnum


# Article関連のスキーマ
class ArticleBase(BaseModel):
    article_number: str
    title: str
    content: Optional[str] = None

class ArticleCreate(ArticleBase):
    article_uuid: str

class ArticleImport(BaseModel):
    article_uuid: str
    article_number: str
    title: str
    content: Optional[str] = None

class Article(ArticleBase):
    article_uuid: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ArticleSearch(BaseModel):
    article_uuid: str
    article_number: str
    title: str
    is_active: bool

class ArticleURL(BaseModel):
    url: str