from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import List, Optional
from uuid import UUID

from app.core.exceptions import (
    UserNotFoundError, 
    DuplicateUsernameError, 
    DatabaseQueryError,
    DatabaseConnectionError,
    DatabaseIntegrityError,
    InvalidParameterError,
    ValidationError,
    InvalidCredentialsError
)
from app.core.logging import get_logger
from app.models import User
from app.schemas import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password


class UserCRUD:
    """ユーザー関連のCRUD操作"""
    logger = get_logger(__name__)
    
    async def get(self, db: AsyncSession, id: UUID) -> Optional[User]:
        """IDでユーザーを取得"""
        try:
            # パラメータ検証
            if not id:
                self.logger.error("User ID is required")
                raise InvalidParameterError("id", id, "IDが必要です")
            
            self.logger.info(f"Retrieving user by id: {id}")
            
            # データベース接続チェック
            if not db.is_active:
                self.logger.error("Database session is not active")
                raise DatabaseConnectionError("データベースセッションがアクティブではありません")
            
            result = await db.execute(select(User).filter(User.id == id))
            user = result.scalar_one_or_none()
            
            if user:
                self.logger.info(f"Found user with id: {id}")
                return user
            else:
                self.logger.info(f"User with id {id} not found")
                raise UserNotFoundError(user_id=str(id))
                
        except UserNotFoundError:
            raise
        except InvalidParameterError:
            raise
        except DatabaseConnectionError:
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error retrieving user {id}: {str(e)}")
            raise DatabaseQueryError(f"ユーザー取得中にデータベースエラーが発生しました: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving user {id}: {str(e)}")
            raise DatabaseQueryError(f"ユーザー取得中に予期しないエラーが発生しました: {str(e)}") from e
    
    async def get_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        """ユーザー名でユーザーを取得"""
        try:
            # パラメータ検証
            if not username or not username.strip():
                self.logger.error("Username is required and cannot be empty")
                raise InvalidParameterError("username", username, "ユーザー名が必要です")
            
            self.logger.info(f"Retrieving user by username: {username}")
            
            # データベース接続チェック
            if not db.is_active:
                self.logger.error("Database session is not active")
                raise DatabaseConnectionError("データベースセッションがアクティブではありません")
            
            result = await db.execute(select(User).filter(User.username == username))
            user = result.scalar_one_or_none()
            
            if user:
                self.logger.info(f"Found user with username: {username}")
                return user
            else:
                self.logger.warning(f"User with username {username} not found")
                raise UserNotFoundError(username=username)
                
        except UserNotFoundError:
            raise
        except InvalidParameterError:
            raise
        except DatabaseConnectionError:
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error retrieving user by username {username}: {str(e)}")
            raise DatabaseQueryError(f"ユーザー名によるユーザー取得中にデータベースエラーが発生しました: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving user by username {username}: {str(e)}")
            raise DatabaseQueryError(f"ユーザー名によるユーザー取得中に予期しないエラーが発生しました: {str(e)}") from e
    
    async def get_by_username_optional(self, db: AsyncSession, username: str) -> Optional[User]:
        """ユーザー名でユーザーを取得（例外を投げない）"""
        try:
            # パラメータ検証
            if not username or not username.strip():
                self.logger.error("Username is required and cannot be empty")
                return None
            
            self.logger.info(f"Retrieving user by username: {username}")
            
            # データベース接続チェック
            if not db.is_active:
                self.logger.error("Database session is not active")
                return None
            
            result = await db.execute(select(User).filter(User.username == username))
            user = result.scalar_one_or_none()
            
            if user:
                self.logger.info(f"Found user with username: {username}")
            else:
                self.logger.info(f"User with username {username} not found")
            
            return user
            
        except SQLAlchemyError as e:
            self.logger.error(f"Database error retrieving user by username {username}: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving user by username {username}: {str(e)}")
            return None
    
    async def get_multi(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
        """ユーザー一覧を取得"""
        try:
            # パラメータ検証
            if skip < 0:
                self.logger.error(f"Invalid skip parameter: {skip}")
                raise InvalidParameterError("skip", skip, "skipは0以上である必要があります")
            
            if limit <= 0 or limit > 1000:
                self.logger.error(f"Invalid limit parameter: {limit}")
                raise InvalidParameterError("limit", limit, "limitは1以上1000以下である必要があります")
            
            self.logger.info(f"Retrieving users (skip={skip}, limit={limit})")
            
            # データベース接続チェック
            if not db.is_active:
                self.logger.error("Database session is not active")
                raise DatabaseConnectionError("データベースセッションがアクティブではありません")
            
            result = await db.execute(select(User).offset(skip).limit(limit))
            users = result.scalars().all()
            
            self.logger.info(f"Retrieved {len(users)} users")
            return users
            
        except InvalidParameterError:
            raise
        except DatabaseConnectionError:
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error retrieving users: {str(e)}")
            raise DatabaseQueryError(f"ユーザー一覧取得中にデータベースエラーが発生しました: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving users: {str(e)}")
            raise DatabaseQueryError(f"ユーザー一覧取得中に予期しないエラーが発生しました: {str(e)}") from e
    
    async def create(self, db: AsyncSession, obj_in: UserCreate) -> User:
        """新しいユーザーを作成"""
        try:
            # 入力データ検証
            if not obj_in.username or not obj_in.username.strip():
                self.logger.error("Username is required for user creation")
                raise ValidationError("ユーザー名は必須です")
            
            if not obj_in.password or len(obj_in.password) < 8:
                self.logger.error("Password must be at least 8 characters long")
                raise ValidationError("パスワードは8文字以上である必要があります")
            
            self.logger.info(f"Creating new user with username: {obj_in.username}")
            
            # データベース接続チェック
            if not db.is_active:
                self.logger.error("Database session is not active")
                raise DatabaseConnectionError("データベースセッションがアクティブではありません")
            
            # ユーザー名の重複チェック
            existing_user = await self.get_by_username_optional(db, obj_in.username)
            if existing_user:
                self.logger.warning(f"Username {obj_in.username} already exists")
                raise DuplicateUsernameError(obj_in.username)
            
            # パスワードハッシュ化
            try:
                hashed_password = get_password_hash(obj_in.password)
            except Exception as e:
                self.logger.error(f"Error hashing password: {str(e)}")
                raise ValidationError(f"パスワードの処理中にエラーが発生しました: {str(e)}")
            
            # ユーザーオブジェクト作成
            db_obj = User(
                username=obj_in.username,
                hashed_password=hashed_password,
                full_name=obj_in.full_name,
                is_admin=obj_in.is_admin
            )
            
            db.add(db_obj)
            await db.flush()
            
            self.logger.info(f"Successfully created user with id: {db_obj.id}")
            return db_obj
            
        except (ValidationError, DuplicateUsernameError, DatabaseConnectionError):
            raise
        except IntegrityError as e:
            self.logger.error(f"Database integrity error creating user: {str(e)}")
            raise DatabaseIntegrityError(f"ユーザー作成中にデータベース整合性エラーが発生しました: {str(e)}")
        except SQLAlchemyError as e:
            self.logger.error(f"Database error creating user: {str(e)}")
            raise DatabaseQueryError(f"ユーザー作成中にデータベースエラーが発生しました: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error creating user: {str(e)}")
            raise DatabaseQueryError(f"ユーザー作成中に予期しないエラーが発生しました: {str(e)}") from e
    
    async def update(self, db: AsyncSession, db_obj: User, obj_in: UserUpdate) -> User:
        """ユーザー情報を更新"""
        try:
            # パラメータ検証
            if not db_obj:
                self.logger.error("User object is required for update")
                raise InvalidParameterError("db_obj", db_obj, "更新対象のユーザーオブジェクトが必要です")
            
            self.logger.info(f"Updating user: {db_obj.id}")
            
            # データベース接続チェック
            if not db.is_active:
                self.logger.error("Database session is not active")
                raise DatabaseConnectionError("データベースセッションがアクティブではありません")
            
            update_data = obj_in.dict(exclude_unset=True)
            
            if not update_data:
                self.logger.info(f"No update data provided for user {db_obj.id}")
                return db_obj
            
            # パスワード検証とハッシュ化
            if "password" in update_data:
                password = update_data.pop("password")
                if not password or len(password) < 8:
                    self.logger.error("Password must be at least 8 characters long")
                    raise ValidationError("パスワードは8文字以上である必要があります")
                
                try:
                    update_data["hashed_password"] = get_password_hash(password)
                except Exception as e:
                    self.logger.error(f"Error hashing password: {str(e)}")
                    raise ValidationError(f"パスワードの処理中にエラーが発生しました: {str(e)}")
            
            # ユーザー名の重複チェック（ユーザー名が変更される場合）
            if "username" in update_data and update_data["username"] != db_obj.username:
                existing_user = await self.get_by_username_optional(db, update_data["username"])
                if existing_user:
                    self.logger.warning(f"Username {update_data['username']} already exists")
                    raise DuplicateUsernameError(update_data["username"])
            
            # フィールド更新
            for field, value in update_data.items():
                setattr(db_obj, field, value)
            
            await db.flush()
            
            self.logger.info(f"Successfully updated user {db_obj.id}")
            return db_obj
            
        except (ValidationError, DuplicateUsernameError, InvalidParameterError, DatabaseConnectionError):
            raise
        except IntegrityError as e:
            self.logger.error(f"Database integrity error updating user: {str(e)}")
            raise DatabaseIntegrityError(f"ユーザー更新中にデータベース整合性エラーが発生しました: {str(e)}")
        except SQLAlchemyError as e:
            self.logger.error(f"Database error updating user: {str(e)}")
            raise DatabaseQueryError(f"ユーザー更新中にデータベースエラーが発生しました: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error updating user: {str(e)}")
            raise DatabaseQueryError(f"ユーザー更新中に予期しないエラーが発生しました: {str(e)}") from e
    
    async def delete(self, db: AsyncSession, id: UUID) -> bool:
        """ユーザーを削除"""
        try:
            # パラメータ検証
            if not id:
                self.logger.error("User ID is required for deletion")
                raise InvalidParameterError("id", id, "削除対象のユーザーIDが必要です")
            
            self.logger.info(f"Deleting user with id: {id}")
            
            # データベース接続チェック
            if not db.is_active:
                self.logger.error("Database session is not active")
                raise DatabaseConnectionError("データベースセッションがアクティブではありません")
            
            # ユーザー取得（存在チェック）
            db_obj = await self.get(db, id)
            if not db_obj:
                self.logger.warning(f"User {id} not found for deletion")
                return False
            
            await db.delete(db_obj)
            await db.flush()
            
            self.logger.info(f"Successfully deleted user {id}")
            return True
            
        except UserNotFoundError:
            self.logger.warning(f"User {id} not found for deletion")
            return False
        except (InvalidParameterError, DatabaseConnectionError):
            raise
        except IntegrityError as e:
            self.logger.error(f"Database integrity error deleting user {id}: {str(e)}")
            raise DatabaseIntegrityError(f"ユーザー削除中にデータベース整合性エラーが発生しました: {str(e)}")
        except SQLAlchemyError as e:
            self.logger.error(f"Database error deleting user {id}: {str(e)}")
            raise DatabaseQueryError(f"ユーザー削除中にデータベースエラーが発生しました: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error deleting user {id}: {str(e)}")
            raise DatabaseQueryError(f"ユーザー削除中に予期しないエラーが発生しました: {str(e)}") from e
    
    async def authenticate(self, db: AsyncSession, username: str, password: str) -> Optional[User]:
        """ユーザー認証"""
        try:
            # パラメータ検証
            if not username or not username.strip():
                self.logger.error("Username is required for authentication")
                raise InvalidParameterError("username", username, "認証にはユーザー名が必要です")
            
            if not password:
                self.logger.error("Password is required for authentication")
                raise InvalidParameterError("password", "[HIDDEN]", "認証にはパスワードが必要です")
            
            self.logger.info(f"Authenticating user: {username}")
            
            # データベース接続チェック
            if not db.is_active:
                self.logger.error("Database session is not active")
                raise DatabaseConnectionError("データベースセッションがアクティブではありません")
            
            # ユーザー取得
            try:
                user = await self.get_by_username(db, username)
            except UserNotFoundError:
                self.logger.warning(f"Authentication failed: user {username} not found")
                raise InvalidCredentialsError()
            
            # パスワード検証
            try:
                if not verify_password(password, user.hashed_password):
                    self.logger.warning(f"Authentication failed: invalid password for user {username}")
                    raise InvalidCredentialsError()
            except Exception as e:
                self.logger.error(f"Error verifying password for user {username}: {str(e)}")
                raise InvalidCredentialsError()
            
            self.logger.info(f"Successfully authenticated user: {username}")
            return user
            
        except (InvalidParameterError, DatabaseConnectionError, InvalidCredentialsError):
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error during authentication for user {username}: {str(e)}")
            raise DatabaseQueryError(f"認証中にデータベースエラーが発生しました: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error during authentication for user {username}: {str(e)}")
            raise DatabaseQueryError(f"認証中に予期しないエラーが発生しました: {str(e)}") from e


# シングルトンインスタンス
user_crud = UserCRUD()
