from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError

from app.models import RefreshToken


class RefreshTokenCRUD:
    """リフレッシュトークンのCRUD操作"""
    
    async def create_refresh_token(
        self, 
        db: AsyncSession, 
        token: str, 
        user_id: UUID, 
        expires_at: datetime
    ) -> RefreshToken:
        """リフレッシュトークンを作成"""
        db_token = RefreshToken(
            token=token,
            user_id=user_id,
            expires_at=expires_at
        )
        db.add(db_token)
        await db.commit()
        await db.refresh(db_token)
        return db_token
    
    async def get_by_token(self, db: AsyncSession, token: str) -> Optional[RefreshToken]:
        """トークンでリフレッシュトークンを取得"""
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token == token)
        )
        return result.scalar_one_or_none()
    
    async def delete_refresh_token(self, db: AsyncSession, token: str) -> bool:
        """リフレッシュトークンを削除"""
        result = await db.execute(
            delete(RefreshToken).where(RefreshToken.token == token)
        )
        await db.commit()
        return result.rowcount > 0
    
    async def delete_expired_tokens(self, db: AsyncSession) -> int:
        """期限切れのリフレッシュトークンを削除"""
        result = await db.execute(
            delete(RefreshToken).where(RefreshToken.expires_at < datetime.utcnow())
        )
        await db.commit()
        return result.rowcount
    
    async def delete_user_tokens(self, db: AsyncSession, user_id: UUID) -> int:
        """特定ユーザーのすべてのリフレッシュトークンを削除"""
        result = await db.execute(
            delete(RefreshToken).where(RefreshToken.user_id == user_id)
        )
        await db.commit()
        return result.rowcount


refresh_token_crud = RefreshTokenCRUD()