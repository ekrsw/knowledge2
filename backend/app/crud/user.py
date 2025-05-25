from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID

from app.core.exceptions import UserNotFoundError, DuplicateUsernameError, DatabaseQueryError
from app.core.logging import get_logger
from app.models import User
from app.schemas import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password


class UserCRUD:
    """ユーザー関連のCRUD操作"""
    logger = get_logger(__name__)
    
    async def get(self, db: AsyncSession, id: UUID) -> Optional[User]:
        """IDでユーザーを取得"""
        self.logger.info(f"Retrieving user by id: {id}")
        result = await db.execute(select(User).filter(User.id == id))
        user = result.scalar_one_or_none()
        if user:
            self.logger.info(f"Found user with id: {id}")
        else:
            self.logger.info(f"User with id {id} not found")
            raise UserNotFoundError
        return user
    
    async def get_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        """ユーザー名でユーザーを取得"""
        self.logger.info(f"Retrieving user by username: {username}")
        result = await db.execute(select(User).filter(User.username == username))
        user = result.scalar_one_or_none()
        if user:
            self.logger.info(f"Found user with username: {username}")
        else:
            self.logger.warning(f"User with username {username} not found")
            raise UserNotFoundError(username=username)
        return user
    
    async def get_by_username_optional(self, db: AsyncSession, username: str) -> Optional[User]:
        """ユーザー名でユーザーを取得（例外を投げない）"""
        self.logger.info(f"Retrieving user by username: {username}")
        result = await db.execute(select(User).filter(User.username == username))
        user = result.scalar_one_or_none()
        if user:
            self.logger.info(f"Found user with username: {username}")
        else:
            self.logger.info(f"User with username {username} not found")
        return user
    
    async def get_multi(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
        """ユーザー一覧を取得"""
        self.logger.info("Retrieving all users")
        try:
            result = await db.execute(select(User).offset(skip).limit(limit))
            users = result.scalars().all()
            self.logger.info(f"Retrieved {len(users)} users")
            return users
        except Exception as e:
            self.logger.error(f"Error retrieving all users: {str(e)}")
            raise DatabaseQueryError(f"Failed to retrieve all users: {str(e)}") from e
    
    async def create(self, db: AsyncSession, obj_in: UserCreate) -> User:
        """新しいユーザーを作成"""
        self.logger.info(f"Creating new user with username: {obj_in.username}")
        # ユーザー名の重複チェック
        existing_user = await self.get_by_username_optional(db, obj_in.username)
        if existing_user:
            raise DuplicateUsernameError(obj_in.username)
        
        hashed_password = get_password_hash(obj_in.password)
        db_obj = User(
            username=obj_in.username,
            hashed_password=hashed_password,
            full_name=obj_in.full_name,
            is_admin=obj_in.is_admin
        )
        db.add(db_obj)
        await db.flush()
        # commitはsessionのfinallyで行う
        return db_obj
    
    async def update(self, db: AsyncSession, db_obj: User, obj_in: UserUpdate) -> User:
        """ユーザー情報を更新"""
        self.logger.info(f"Updating user: {User.id}")
        update_data = obj_in.dict(exclude_unset=True)
        
        # パスワードが含まれている場合はハッシュ化
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        await db.flush()
        # commitはsessionのfinallyで行う
        return db_obj
    
    async def delete(self, db: AsyncSession, id: UUID) -> bool:
        """ユーザーを削除"""
        db_obj = await self.get(db, id)
        if not db_obj:
            return False
        
        await db.delete(db_obj)
        await db.flush()
        # commitはsessionのfinallyで行う
        return True
    
    async def authenticate(self, db: AsyncSession, username: str, password: str) -> Optional[User]:
        """ユーザー認証"""
        user = await self.get_by_username(db, username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user


# シングルトンインスタンス
user_crud = UserCRUD()
