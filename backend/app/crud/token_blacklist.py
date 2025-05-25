from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError

from app.models import TokenBlacklist


class TokenBlacklistCRUD:
    """トークンブラックリストのCRUD操作"""
    
    async def create_blacklist_entry(
        self, 
        db: AsyncSession, 
        jti: str, 
        expires_at: datetime
    ) -> TokenBlacklist:
        """ブラックリストエントリを作成"""
        db_entry = TokenBlacklist(
            jti=jti,
            expires_at=expires_at
        )
        db.add(db_entry)
        try:
            await db.commit()
            await db.refresh(db_entry)
            return db_entry
        except IntegrityError:
            # 既に存在する場合は無視
            await db.rollback()
            return await self.get_by_jti(db, jti)
    
    async def get_by_jti(self, db: AsyncSession, jti: str) -> Optional[TokenBlacklist]:
        """JTIでブラックリストエントリを取得"""
        result = await db.execute(
            select(TokenBlacklist).where(TokenBlacklist.jti == jti)
        )
        return result.scalar_one_or_none()
    
    async def is_blacklisted(self, db: AsyncSession, jti: str) -> bool:
        """JTIがブラックリストに登録されているかチェック"""
        result = await db.execute(
            select(TokenBlacklist.id).where(TokenBlacklist.jti == jti)
        )
        return result.scalar_one_or_none() is not None
    
    async def delete_expired_entries(self, db: AsyncSession) -> int:
        """期限切れのブラックリストエントリを削除"""
        result = await db.execute(
            delete(TokenBlacklist).where(TokenBlacklist.expires_at < datetime.utcnow())
        )
        await db.commit()
        return result.rowcount


token_blacklist_crud = TokenBlacklistCRUD()