from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator

from app.core.exceptions import InvalidTokenError, UserNotFoundError
from app.db.session import get_async_session
from app.models import User
from app.core.security import verify_token
from app.crud.user import user_crud

# セキュリティ設定
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_session)
) -> User:
    """現在のユーザーを取得する依存性（ブラックリストチェック付き）"""
    token = credentials.credentials
    
    try:
        payload = await verify_token(token)
        if payload is None:
            raise InvalidTokenError("トークンが無効です")
        
        user_id = payload.get("sub")
        if user_id is None:
            raise InvalidTokenError("トークンにuser_idが含まれていません")
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なトークンです",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="トークンの処理中に予期せぬエラーが発生しました",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user = await user_crud.get(db, id=user_id)
        if user is None:
            raise UserNotFoundError(user_id=user_id)
        return user
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザーが見つかりません",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ユーザー情報の取得中にエラーが発生しました"
        )


async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """管理者権限チェック"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理者権限が必要です"
        )
    return current_user