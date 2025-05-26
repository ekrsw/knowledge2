from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
from typing import Any

from app.api.deps import get_current_user
from app.core.security import (
    create_access_token, create_refresh_token, verify_refresh_token, verify_password,
    blacklist_token
)
from app.core.config import settings
from app.core.exceptions import (
    DatabaseConnectionError,
    DuplicateUsernameError,
    InvalidCredentialsError,
    InvalidParameterError,
    UserNotFoundError
    )
from app.core.logging import get_request_logger
from app.crud.user import user_crud
from app.db.session import get_async_session
from app.models import User
from app.schemas import UserCreate, UserRegister, User as UserSchema, TokenResponse, RefreshTokenRequest


router = APIRouter()

@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    async_session: AsyncSession = Depends(get_async_session)
    ) -> Any:
    logger = get_request_logger(request)
    logger.info(f"ログインリクエスト: ユーザー名={form_data.username}")

    # ユーザー認証
    try:
        db_user = await user_crud.get_by_username(async_session, username=form_data.username)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザー名またはパスワードが正しくありません",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidParameterError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ユーザー名が必要です",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except DatabaseConnectionError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="データベースセッションがアクティブではありません",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"ユーザー認証失敗: {str(e)}")
        raise HTTPException(status_code=500, detail="ユーザー認証失敗")

    # パスワード検証
    if not verify_password(form_data.password, db_user.hashed_password):
        logger.warning(f"ログイン失敗: ユーザー '{form_data.username}' のパスワードが不正です")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザー名またはパスワードが正しくありません",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # アクセストークン生成
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = await create_access_token(
        data={"sub": str(db_user.id),
              "is_admin": str(db_user.is_admin),
              "username": db_user.username},
        expires_delta=access_token_expires
    )
    
    # リフレッシュトークン生成
    refresh_token = await create_refresh_token(user_id=str(db_user.id), db=async_session)

    logger.info(f"ログイン成功: ユーザーID={db_user.id}, ユーザー名={db_user.username}")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/register", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def register_user(
    request: Request,
    user: UserRegister,
    db: AsyncSession = Depends(get_async_session)
):
    """新しいユーザーを作成（管理者権限なし）"""
    logger = get_request_logger(request)
    logger.info(f"ユーザー登録リクエスト: ユーザー名={user.username}")
    
    try:
        # UserRegisterからUserCreateオブジェクトを作成（is_admin=Falseで固定）
        user_create = UserCreate(
            username=user.username,
            full_name=user.full_name,
            password=user.password,
            is_admin=False  # 一般ユーザー登録では管理者権限を付与しない
        )
        
        db_user = await user_crud.create(db=db, obj_in=user_create)
        logger.info(f"ユーザー登録成功: ユーザー名={db_user.username}")
        return db_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ユーザー登録中にエラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ユーザー登録中にエラーが発生しました"
        )

