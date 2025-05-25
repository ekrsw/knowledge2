from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.exceptions import (
    TokenNotFoundError,
    ExpiredTokenError,
    DatabaseQueryError,
    DatabaseConnectionError,
    DatabaseIntegrityError,
    InvalidParameterError,
    ValidationError
)
from app.core.logging import get_logger
from app.models import RefreshToken


class RefreshTokenCRUD:
    """リフレッシュトークンのCRUD操作"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    async def create_refresh_token(
        self, 
        db: AsyncSession, 
        token: str, 
        user_id: UUID, 
        expires_at: datetime
    ) -> RefreshToken:
        """リフレッシュトークンを作成"""
        try:
            # パラメータ検証
            if not token or not token.strip():
                self.logger.error("Token is required for refresh token creation")
                raise InvalidParameterError("token", "[HIDDEN]", "トークンが必要です")
            
            if not user_id:
                self.logger.error("User ID is required for refresh token creation")
                raise InvalidParameterError("user_id", user_id, "ユーザーIDが必要です")
            
            if not expires_at:
                self.logger.error("Expiration time is required for refresh token creation")
                raise InvalidParameterError("expires_at", expires_at, "有効期限が必要です")
            
            if expires_at <= datetime.utcnow():
                self.logger.error("Expiration time must be in the future")
                raise ValidationError("有効期限は未来の時刻である必要があります")
            
            self.logger.info(f"Creating refresh token for user: {user_id}")
            
            # データベース接続チェック
            if not db.is_active:
                self.logger.error("Database session is not active")
                raise DatabaseConnectionError("データベースセッションがアクティブではありません")
            
            db_token = RefreshToken(
                token=token,
                user_id=user_id,
                expires_at=expires_at
            )
            
            db.add(db_token)
            await db.flush()
            await db.refresh(db_token)
            
            self.logger.info(f"Successfully created refresh token with id: {db_token.id}")
            return db_token
            
        except (InvalidParameterError, ValidationError, DatabaseConnectionError):
            raise
        except IntegrityError as e:
            self.logger.error(f"Database integrity error creating refresh token: {str(e)}")
            raise DatabaseIntegrityError(f"リフレッシュトークン作成中にデータベース整合性エラーが発生しました: {str(e)}")
        except SQLAlchemyError as e:
            self.logger.error(f"Database error creating refresh token: {str(e)}")
            raise DatabaseQueryError(f"リフレッシュトークン作成中にデータベースエラーが発生しました: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error creating refresh token: {str(e)}")
            raise DatabaseQueryError(f"リフレッシュトークン作成中に予期しないエラーが発生しました: {str(e)}") from e
    
    async def get_by_token(self, db: AsyncSession, token: str) -> Optional[RefreshToken]:
        """トークンでリフレッシュトークンを取得"""
        try:
            # パラメータ検証
            if not token or not token.strip():
                self.logger.error("Token is required for refresh token retrieval")
                raise InvalidParameterError("token", "[HIDDEN]", "トークンが必要です")
            
            self.logger.info("Retrieving refresh token")
            
            # データベース接続チェック
            if not db.is_active:
                self.logger.error("Database session is not active")
                raise DatabaseConnectionError("データベースセッションがアクティブではありません")
            
            result = await db.execute(
                select(RefreshToken).where(RefreshToken.token == token)
            )
            refresh_token = result.scalar_one_or_none()
            
            if refresh_token:
                # 有効期限チェック
                if refresh_token.expires_at <= datetime.utcnow():
                    self.logger.warning("Refresh token has expired")
                    raise ExpiredTokenError("リフレッシュトークン")
                
                self.logger.info("Found valid refresh token")
            else:
                self.logger.info("Refresh token not found")
            
            return refresh_token
            
        except (InvalidParameterError, DatabaseConnectionError, ExpiredTokenError):
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error retrieving refresh token: {str(e)}")
            raise DatabaseQueryError(f"リフレッシュトークン取得中にデータベースエラーが発生しました: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving refresh token: {str(e)}")
            raise DatabaseQueryError(f"リフレッシュトークン取得中に予期しないエラーが発生しました: {str(e)}") from e
    
    async def delete_refresh_token(self, db: AsyncSession, token: str) -> bool:
        """リフレッシュトークンを削除"""
        try:
            # パラメータ検証
            if not token or not token.strip():
                self.logger.error("Token is required for refresh token deletion")
                raise InvalidParameterError("token", "[HIDDEN]", "トークンが必要です")
            
            self.logger.info("Deleting refresh token")
            
            # データベース接続チェック
            if not db.is_active:
                self.logger.error("Database session is not active")
                raise DatabaseConnectionError("データベースセッションがアクティブではありません")
            
            result = await db.execute(
                delete(RefreshToken).where(RefreshToken.token == token)
            )
            await db.flush()
            
            deleted_count = result.rowcount
            if deleted_count > 0:
                self.logger.info(f"Successfully deleted {deleted_count} refresh token(s)")
            else:
                self.logger.info("No refresh token found to delete")
            
            return deleted_count > 0
            
        except (InvalidParameterError, DatabaseConnectionError):
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error deleting refresh token: {str(e)}")
            raise DatabaseQueryError(f"リフレッシュトークン削除中にデータベースエラーが発生しました: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error deleting refresh token: {str(e)}")
            raise DatabaseQueryError(f"リフレッシュトークン削除中に予期しないエラーが発生しました: {str(e)}") from e
    
    async def delete_expired_tokens(self, db: AsyncSession) -> int:
        """期限切れのリフレッシュトークンを削除"""
        try:
            self.logger.info("Deleting expired refresh tokens")
            
            # データベース接続チェック
            if not db.is_active:
                self.logger.error("Database session is not active")
                raise DatabaseConnectionError("データベースセッションがアクティブではありません")
            
            current_time = datetime.utcnow()
            result = await db.execute(
                delete(RefreshToken).where(RefreshToken.expires_at < current_time)
            )
            await db.flush()
            
            deleted_count = result.rowcount
            self.logger.info(f"Successfully deleted {deleted_count} expired refresh token(s)")
            
            return deleted_count
            
        except DatabaseConnectionError:
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error deleting expired refresh tokens: {str(e)}")
            raise DatabaseQueryError(f"期限切れリフレッシュトークン削除中にデータベースエラーが発生しました: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error deleting expired refresh tokens: {str(e)}")
            raise DatabaseQueryError(f"期限切れリフレッシュトークン削除中に予期しないエラーが発生しました: {str(e)}") from e
    
    async def delete_user_tokens(self, db: AsyncSession, user_id: UUID) -> int:
        """特定ユーザーのすべてのリフレッシュトークンを削除"""
        try:
            # パラメータ検証
            if not user_id:
                self.logger.error("User ID is required for user token deletion")
                raise InvalidParameterError("user_id", user_id, "ユーザーIDが必要です")
            
            self.logger.info(f"Deleting all refresh tokens for user: {user_id}")
            
            # データベース接続チェック
            if not db.is_active:
                self.logger.error("Database session is not active")
                raise DatabaseConnectionError("データベースセッションがアクティブではありません")
            
            result = await db.execute(
                delete(RefreshToken).where(RefreshToken.user_id == user_id)
            )
            await db.flush()
            
            deleted_count = result.rowcount
            self.logger.info(f"Successfully deleted {deleted_count} refresh token(s) for user {user_id}")
            
            return deleted_count
            
        except (InvalidParameterError, DatabaseConnectionError):
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error deleting user refresh tokens: {str(e)}")
            raise DatabaseQueryError(f"ユーザーリフレッシュトークン削除中にデータベースエラーが発生しました: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error deleting user refresh tokens: {str(e)}")
            raise DatabaseQueryError(f"ユーザーリフレッシュトークン削除中に予期しないエラーが発生しました: {str(e)}") from e


refresh_token_crud = RefreshTokenCRUD()
