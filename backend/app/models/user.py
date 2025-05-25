from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(100))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # リレーションシップ
    knowledge_items: Mapped[List["Knowledge"]] = relationship(
        "Knowledge", 
        back_populates="author", 
        foreign_keys="Knowledge.created_by"
    )
    approved_knowledge_items: Mapped[List["Knowledge"]] = relationship(
        "Knowledge", 
        back_populates="approver", 
        foreign_keys="Knowledge.approved_by"
    )