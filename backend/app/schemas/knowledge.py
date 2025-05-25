from pydantic import BaseModel, field_validator
from datetime import datetime, date
from typing import List, Optional
from uuid import UUID
from app.models.knowledge import StatusEnum, ChangeTypeEnum
from app.schemas.user import User


class KnowledgeBase(BaseModel):
    title: str
    info_category: Optional[str] = None
    keywords: Optional[str] = None
    importance: bool = False
    target: Optional[str] = None
    open_publish_start: Optional[date] = None
    open_publish_end: Optional[date] = None
    question: Optional[str] = None
    answer: Optional[str] = None
    add_comments: Optional[str] = None
    remarks: Optional[str] = None

    @field_validator('open_publish_start', 'open_publish_end', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        if v == "":
            return None
        return v


class KnowledgeCreate(KnowledgeBase):
    article_number: str
    change_type: ChangeTypeEnum


class KnowledgeUpdate(BaseModel):
    title: Optional[str] = None
    info_category: Optional[str] = None
    keywords: Optional[str] = None
    importance: Optional[bool] = None
    target: Optional[str] = None
    open_publish_start: Optional[date] = None
    open_publish_end: Optional[date] = None
    question: Optional[str] = None
    answer: Optional[str] = None
    add_comments: Optional[str] = None
    remarks: Optional[str] = None

    @field_validator('open_publish_start', 'open_publish_end', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        if v == "":
            return None
        return v


class StatusUpdate(BaseModel):
    status: StatusEnum


class Knowledge(KnowledgeBase):
    id: UUID
    article_number: str
    change_type: ChangeTypeEnum
    status: StatusEnum
    created_by: UUID
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None  # 承認日時
    approved_by: Optional[UUID] = None  # 承認者ID
    created_at: datetime
    updated_at: datetime
    author: User
    approver: Optional[User] = None  # 承認者情報
    
    class Config:
        from_attributes = True


# レスポンス用のスキーマ
class UserWithKnowledge(User):
    knowledge_items: List[Knowledge] = []