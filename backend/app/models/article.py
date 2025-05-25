from sqlalchemy import String, Text, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from sqlalchemy.sql import func
from typing import Optional


class Base(DeclarativeBase):
    pass


class Article(Base):
    __tablename__ = "articles"
    
    article_uuid: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)  # URL生成用UUID
    article_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # KBA-01234-AB567
    title: Mapped[str] = mapped_column(String(200))  # 既存記事タイトル
    content: Mapped[Optional[str]] = mapped_column(Text)  # 既存記事内容（参考用）
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # 有効フラグ
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())