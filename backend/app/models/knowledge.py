from sqlalchemy import String, Text, DateTime, ForeignKey, Boolean, Date, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from typing import Optional
from datetime import datetime, date
import enum

from app.db.base import Base


class StatusEnum(enum.Enum):
    draft = "draft"
    submitted = "submitted"
    approved = "approved"
    published = "published"


class ChangeTypeEnum(enum.Enum):
    modify = "modify"
    delete = "delete"


class Knowledge(Base):
    __tablename__ = "knowledge"

    article_number: Mapped[str] = mapped_column(String(20), index=True)  # 対象記事番号
    change_type: Mapped[ChangeTypeEnum] = mapped_column(Enum(ChangeTypeEnum))  # 修正案 or 削除案
    title: Mapped[str] = mapped_column(String(200))
    info_category: Mapped[Optional[str]] = mapped_column(String(100))
    keywords: Mapped[Optional[str]] = mapped_column(String(500))
    importance: Mapped[bool] = mapped_column(Boolean, default=False)
    target: Mapped[Optional[str]] = mapped_column(String(200))
    open_publish_start: Mapped[Optional[date]] = mapped_column(Date)
    open_publish_end: Mapped[Optional[date]] = mapped_column(Date)
    question: Mapped[Optional[str]] = mapped_column(Text)
    answer: Mapped[Optional[str]] = mapped_column(Text)
    add_comments: Mapped[Optional[str]] = mapped_column(Text)
    remarks: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[StatusEnum] = mapped_column(Enum(StatusEnum), default=StatusEnum.draft)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))  # 承認日時
    approved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))  # 承認者ID
    
    # リレーションシップ
    author: Mapped["User"] = relationship(
        "User", 
        back_populates="knowledge_items", 
        foreign_keys=[created_by]
    )
    approver: Mapped[Optional["User"]] = relationship(
        "User", 
        back_populates="approved_knowledge_items", 
        foreign_keys=[approved_by]
    )