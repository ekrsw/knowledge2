from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.exceptions import (
    TokenNotFoundError,
    DatabaseQueryError,
    DatabaseConnectionError,
    DatabaseIntegrityError,
    InvalidParameterError,
    ValidationError
)
from app.core.logging import get_logger
from app.models import TokenBlacklist


class TokenBlacklistCRUD:
    """トークンブラックリストのCRUD操作"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    async def create_blacklist_entry(
        self, 
        db: AsyncSession, 
        jti: str, 
        expires_at: datetime
    ) -> TokenBlacklist:
        """ブラックリストエントリを作成"""
        try:
            # パラメータ検証
            if not jti or not jti.strip():
                self.logger.error("JTI is required for blacklist entry creation")
                raise InvalidParameterError("jti", jti, "JTIが必要です")
            
            if not expires_at:
                self.logger.error("Expiration time is required for blacklist entry creation")
                raise InvalidParameterError("expires_at", expires_at, "有効期限が必要です")
            
            if expires_at <= datetime.utcnow():
                self.logger.error("Expiration time must be in the future")
                raise ValidationError("有効期限は未来の時刻である必要があります")
            
            self.logger.info(f"Creating blacklist entry for JTI: {jti[:8]}...")
            
            # データベース接続チェック
            if not db.is_active:
                self.logger.error("Database session is not active")
                raise DatabaseConnectionError("データベースセッションがアクティブではありません")
            
            db_entry = TokenBlacklist(
                jti=jti,
                expires_at=expires_at
            )
            
            db.add(db_entry)
            await db.flush()
            await db.refresh(db_entry)
            
            self.logger.info(f"Successfully created blacklist entry with id: {db_entry.id}")
            return db_entry
            
        except IntegrityError:
            # 既に存在する場合は既存のエントリを返す
            self.logger.info(f"Blacklist entry for JTI {jti[:8]}... already exists, returning existing entry")
            existing_entry = await self.get_by_jti(db, jti)
            if existing_entry:
                return existing_entry
            else:
                self.logger.error("Failed to retrieve existing blacklist entry after integrity error")
                raise DatabaseIntegrityError("ブラックリストエントリの作成中に整合性エラーが発生しました")
        except (InvalidParameterError, ValidationError, DatabaseConnectionError):
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error creating blacklist entry: {str(e)}")
            raise DatabaseQueryError(f"ブラックリストエントリ作成中にデータベースエラーが発生しました: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error creating blacklist entry: {str(e)}")
            raise DatabaseQueryError(f"ブラックリストエントリ作成中に予期しないエラーが発生しました: {str(e)}") from e
    
    async def get_by_jti(self, db: AsyncSession, jti: str) -> Optional[TokenBlacklist]:
        """JTIでブラックリストエントリを取得"""
        try:
            # パラメータ検証
            if not jti or not jti.strip():
                self.logger.error("JTI is required for blacklist entry retrieval")
                raise InvalidParameterError("jti", jti, "JTIが必要です")
            
            self.logger.info(f"Retrieving blacklist entry for JTI: {jti[:8]}...")
            
            # データベース接続チェック
            if not db.is_active:
                self.logger.error("Database session is not active")
                raise DatabaseConnectionError("データベースセッションがアクティブではありません")
            
            result = await db.execute(
                select(TokenBlacklist).where(TokenBlacklist.jti == jti)
            )
            entry = result.scalar_one_or_none()
            
            if entry:
                self.logger.info(f"Found blacklist entry for JTI: {jti[:8]}...")
            else:
                self.logger.info(f"No blacklist entry found for JTI: {jti[:8]}...")
            
            return entry
            
        except (InvalidParameterError, DatabaseConnectionError):
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error retrieving blacklist entry: {str(e)}")
            raise DatabaseQueryError(f"ブラックリストエントリ取得中にデータベースエラーが発生しました: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving blacklist entry: {str(e)}")
            raise DatabaseQueryError(f"ブラックリストエントリ取得中に予期しないエラーが発生しました: {str(e)}") from e
    
    async def is_blacklisted(self, db: AsyncSession, jti: str) -> bool:
        """JTIがブラックリストに登録されているかチェック"""
        try:
            # パラメータ検証
            if not jti or not jti.strip():
                self.logger.error("JTI is required for blacklist check")
                raise InvalidParameterError("jti", jti, "JTIが必要です")
            
            self.logger.info(f"Checking if JTI is blacklisted: {jti[:8]}...")
            
            # データベース接続チェック
            if not db.is_active:
                self.logger.error("Database session is not active")
                raise DatabaseConnectionError("データベースセッションがアクティブではありません")
            
            result = await db.execute(
                select(TokenBlacklist.id).where(TokenBlacklist.jti == jti)
            )
            is_blacklisted = result.scalar_one_or_none() is not None
            
            if is_blacklisted:
                self.logger.warning(f"JTI {jti[:8]}... is blacklisted")
            else:
                self.logger.info(f"JTI {jti[:8]}... is not blacklisted")
            
            return is_blacklisted
            
        except (InvalidParameterError, DatabaseConnectionError):
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error checking blacklist status: {str(e)}")
            raise DatabaseQueryError(f"ブラックリスト確認中にデータベースエラーが発生しました: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error checking blacklist status: {str(e)}")
            raise DatabaseQueryError(f"ブラックリスト確認中に予期しないエラーが発生しました: {str(e)}") from e
    
    async def delete_expired_entries(self, db: AsyncSession) -> int:
        """期限切れのブラックリストエントリを削除"""
        try:
            self.logger.info("Deleting expired blacklist entries")
            
            # データベース接続チェック
            if not db.is_active:
                self.logger.error("Database session is not active")
                raise DatabaseConnectionError("データベースセッションがアクティブではありません")
            
            current_time = datetime.utcnow()
            result = await db.execute(
                delete(TokenBlacklist).where(TokenBlacklist.expires_at < current_time)
            )
            await db.flush()
            
            deleted_count = result.rowcount
            self.logger.info(f"Successfully deleted {deleted_count} expired blacklist entries")
            
            return deleted_count
            
        except DatabaseConnectionError:
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error deleting expired blacklist entries: {str(e)}")
            raise DatabaseQueryError(f"期限切れブラックリストエントリ削除中にデータベースエラーが発生しました: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error deleting expired blacklist entries: {str(e)}")
            raise DatabaseQueryError(f"期限切れブラックリストエントリ削除中に予期しないエラーが発生しました: {str(e)}") from e


token_blacklist_crud = TokenBlacklistCRUD()
