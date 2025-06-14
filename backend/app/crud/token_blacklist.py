from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.exceptions import (
    TokenNotFoundError,
    TokenBlacklistNotFoundError,
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
    
    async def get(self, db: AsyncSession, entry_id: int) -> TokenBlacklist:
        """IDでブラックリストエントリを取得"""
        try:
            # パラメータ検証
            if entry_id is None:
                self.logger.error("Entry ID is required for blacklist entry retrieval")
                raise InvalidParameterError("entry_id", entry_id, "エントリIDが必要です")
            
            self.logger.info(f"Retrieving blacklist entry by id: {entry_id}")
            
            # データベース接続チェック
            if not db.is_active:
                self.logger.error("Database session is not active")
                raise DatabaseConnectionError("データベースセッションがアクティブではありません")
            
            result = await db.execute(
                select(TokenBlacklist).where(TokenBlacklist.id == entry_id)
            )
            entry = result.scalar_one_or_none()
            
            if entry:
                self.logger.info(f"Found blacklist entry with id: {entry_id}")
                return entry
            else:
                self.logger.info(f"Blacklist entry with id {entry_id} not found")
                raise TokenBlacklistNotFoundError(f"ブラックリストエントリ (ID: {entry_id})")
            
        except (InvalidParameterError, DatabaseConnectionError, TokenBlacklistNotFoundError):
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error retrieving blacklist entry: {str(e)}")
            raise DatabaseQueryError(f"ブラックリストエントリ取得中にデータベースエラーが発生しました: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving blacklist entry: {str(e)}")
            raise DatabaseQueryError(f"ブラックリストエントリ取得中に予期しないエラーが発生しました: {str(e)}") from e
    
    async def create(self, db: AsyncSession, obj_in) -> TokenBlacklist:
        """ブラックリストエントリを作成（スキーマ使用）"""
        return await self.create_blacklist_entry(db, obj_in.jti, obj_in.expires_at)
    
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
            
            now = datetime.now(expires_at.tzinfo) if expires_at.tzinfo else datetime.utcnow()
            if expires_at <= now:
                self.logger.error("Expiration time must be in the future")
                raise ValidationError("有効期限は未来の時刻である必要があります")
            
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
            
            return db_entry
            
        except IntegrityError:
            # 既に存在する場合はValidationErrorを発生させる
            self.logger.error(f"Blacklist entry for JTI {jti[:8]}... already exists")
            raise ValidationError(f"JTI {jti} は既にブラックリストに登録されています")
        except (InvalidParameterError, ValidationError, DatabaseConnectionError):
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error creating blacklist entry: {str(e)}")
            raise DatabaseQueryError(f"ブラックリストエントリ作成中にデータベースエラーが発生しました: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error creating blacklist entry: {str(e)}")
            raise DatabaseQueryError(f"ブラックリストエントリ作成中に予期しないエラーが発生しました: {str(e)}") from e
    
    async def get_by_jti(self, db: AsyncSession, jti: str) -> TokenBlacklist:
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
                return entry
            else:
                self.logger.info(f"No blacklist entry found for JTI: {jti[:8]}...")
                raise TokenBlacklistNotFoundError(f"ブラックリストエントリ (JTI: {jti})")
            
        except (InvalidParameterError, DatabaseConnectionError, TokenBlacklistNotFoundError):
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error retrieving blacklist entry: {str(e)}")
            raise DatabaseQueryError(f"ブラックリストエントリ取得中にデータベースエラーが発生しました: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving blacklist entry: {str(e)}")
            raise DatabaseQueryError(f"ブラックリストエントリ取得中に予期しないエラーが発生しました: {str(e)}") from e
    
    async def is_blacklisted(self, db: AsyncSession, jti: str) -> bool:
        """JTIがブラックリストに登録されているかチェック（期限切れは除外）"""
        try:
            # パラメータ検証
            if not jti or not jti.strip():
                self.logger.error("JTI is required for blacklist check")
                raise InvalidParameterError("jti", jti, "JTIが必要です")
            
            
            # データベース接続チェック
            if not db.is_active:
                self.logger.error("Database session is not active")
                raise DatabaseConnectionError("データベースセッションがアクティブではありません")
            
            current_time = datetime.utcnow()
            result = await db.execute(
                select(TokenBlacklist.id).where(
                    TokenBlacklist.jti == jti,
                    TokenBlacklist.expires_at > current_time
                )
            )
            is_blacklisted = result.scalar_one_or_none() is not None
            
            return is_blacklisted
            
        except (InvalidParameterError, DatabaseConnectionError):
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error checking blacklist status: {str(e)}")
            raise DatabaseQueryError(f"ブラックリスト確認中にデータベースエラーが発生しました: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error checking blacklist status: {str(e)}")
            raise DatabaseQueryError(f"ブラックリスト確認中に予期しないエラーが発生しました: {str(e)}") from e
    
    async def is_token_blacklisted(self, db: AsyncSession, jti: str) -> bool:
        """JTIがブラックリストに登録されているかチェック（エイリアス）"""
        return await self.is_blacklisted(db, jti)
    
    async def delete(self, db: AsyncSession, entry_id: int) -> bool:
        """IDでブラックリストエントリを削除"""
        try:
            # パラメータ検証
            if entry_id is None:
                self.logger.error("Entry ID is required for blacklist entry deletion")
                raise InvalidParameterError("entry_id", entry_id, "エントリIDが必要です")
            
            self.logger.info(f"Deleting blacklist entry with id: {entry_id}")
            
            # データベース接続チェック
            if not db.is_active:
                self.logger.error("Database session is not active")
                raise DatabaseConnectionError("データベースセッションがアクティブではありません")
            
            # 削除実行（存在チェックなしで直接削除）
            result = await db.execute(
                delete(TokenBlacklist).where(TokenBlacklist.id == entry_id)
            )
            await db.flush()
            
            deleted_count = result.rowcount
            if deleted_count > 0:
                self.logger.info(f"Successfully deleted blacklist entry with id: {entry_id}")
                return True
            else:
                self.logger.info(f"No blacklist entry found to delete for id: {entry_id}")
                return False
            
        except (InvalidParameterError, DatabaseConnectionError, TokenBlacklistNotFoundError):
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error deleting blacklist entry: {str(e)}")
            raise DatabaseQueryError(f"ブラックリストエントリ削除中にデータベースエラーが発生しました: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error deleting blacklist entry: {str(e)}")
            raise DatabaseQueryError(f"ブラックリストエントリ削除中に予期しないエラーが発生しました: {str(e)}") from e
    
    async def delete_by_jti(self, db: AsyncSession, jti: str) -> bool:
        """JTIでブラックリストエントリを削除"""
        try:
            # パラメータ検証
            if not jti or not jti.strip():
                self.logger.error("JTI is required for blacklist entry deletion")
                raise InvalidParameterError("jti", jti, "JTIが必要です")
            
            self.logger.info(f"Deleting blacklist entry for JTI: {jti[:8]}...")
            
            # データベース接続チェック
            if not db.is_active:
                self.logger.error("Database session is not active")
                raise DatabaseConnectionError("データベースセッションがアクティブではありません")
            
            # 削除実行（存在チェックなしで直接削除）
            result = await db.execute(
                delete(TokenBlacklist).where(TokenBlacklist.jti == jti)
            )
            await db.flush()
            
            deleted_count = result.rowcount
            if deleted_count > 0:
                self.logger.info(f"Successfully deleted blacklist entry for JTI: {jti[:8]}...")
                return True
            else:
                self.logger.info(f"No blacklist entry found to delete for JTI: {jti[:8]}...")
                return False
            
        except (InvalidParameterError, DatabaseConnectionError):
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error deleting blacklist entry: {str(e)}")
            raise DatabaseQueryError(f"ブラックリストエントリ削除中にデータベースエラーが発生しました: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error deleting blacklist entry: {str(e)}")
            raise DatabaseQueryError(f"ブラックリストエントリ削除中に予期しないエラーが発生しました: {str(e)}") from e
    
    async def get_all_active_entries(self, db: AsyncSession) -> list[TokenBlacklist]:
        """有効なブラックリストエントリ一覧を取得"""
        try:
            self.logger.info("Retrieving all active blacklist entries")
            
            # データベース接続チェック
            if not db.is_active:
                self.logger.error("Database session is not active")
                raise DatabaseConnectionError("データベースセッションがアクティブではありません")
            
            current_time = datetime.utcnow()
            result = await db.execute(
                select(TokenBlacklist).where(TokenBlacklist.expires_at > current_time)
            )
            entries = result.scalars().all()
            
            self.logger.info(f"Found {len(entries)} active blacklist entries")
            return list(entries)
            
        except DatabaseConnectionError:
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error retrieving active blacklist entries: {str(e)}")
            raise DatabaseQueryError(f"有効ブラックリストエントリ取得中にデータベースエラーが発生しました: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving active blacklist entries: {str(e)}")
            raise DatabaseQueryError(f"有効ブラックリストエントリ取得中に予期しないエラーが発生しました: {str(e)}") from e
    
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
