from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
from typing import Any, Optional
import uuid

from app.api.deps import get_current_user
from app.core.security import (
    create_access_token, create_refresh_token, verify_refresh_token, verify_password,
    blacklist_token, revoke_refresh_token
)
from app.core.config import settings
from app.core.exceptions import (
    DatabaseConnectionError,
    DatabaseIntegrityError,
    DuplicateUsernameError,
    InvalidCredentialsError,
    InvalidParameterError,
    UserNotFoundError,
    ValidationError
)
from app.core.logging import get_request_logger
from app.crud.user import user_crud
from app.db.session import get_async_session
from app.models import User
from app.schemas import UserCreate, UserRegister, User as UserSchema, TokenResponse, RefreshTokenRequest, LogoutRequest, PasswordUpdate


router = APIRouter()

async def create_access_token_for_user(
        logger: Any,
        sub: str,
        is_admin: bool,
        username: str,
        expires_delta: timedelta = None
        ) -> str:
    """
    ユーザーのアクセストークンを生成するヘルパー関数
    """
    # アクセストークン生成
    try:
        access_token = await create_access_token(
            data={"sub": sub,
                "is_admin": str(is_admin).lower(),
                "username": username},
            expires_delta=expires_delta
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="秘密鍵が設定されていないか、無効です",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"アクセストークン生成失敗: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="アクセストークンの生成に失敗しました",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return access_token


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
    access_token = await create_access_token_for_user(
        logger=logger,
        sub=str(db_user.id),
        is_admin=db_user.is_admin,
        username=db_user.username,
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
        
    except DuplicateUsernameError as e:
        logger.warning(f"ユーザー名重複エラー: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message
        )
    except ValidationError as e:
        logger.warning(f"バリデーションエラー: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except DatabaseConnectionError as e:
        logger.error(f"データベース接続エラー: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="データベースサービスが利用できません"
        )
    except DatabaseIntegrityError as e:
        logger.error(f"データベース整合性エラー: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="データの整合性に問題があります"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ユーザー登録中にエラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ユーザー登録中にエラーが発生しました"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    request: Request,
    token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_async_session)
    ):
    """リフレッシュトークンを使用してアクセストークンを更新"""
    logger = get_request_logger(request)
    logger.info("リフレッシュトークンリクエスト")
    
    try:
        # リフレッシュトークンを検証
        user_id = await verify_refresh_token(token_data.refresh_token, db)
        if not user_id:
            logger.warning("無効なリフレッシュトークン")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無効なリフレッシュトークンです"
            )
        
        # ユーザー情報を取得
        user = await user_crud.get(db, id=uuid.UUID(user_id))
        if not user:
            logger.warning(f"ユーザーが見つかりません: user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ユーザーが見つかりません"
            )
        
        # 新しいアクセストークンを作成
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        new_access_token = await create_access_token_for_user(
            logger=logger,
            sub=str(user.id),
            is_admin=user.is_admin,
            username=user.username,
            expires_delta=access_token_expires
        )
        # 古いアクセストークンをブラックリストに追加
        blacklist_result = await blacklist_token(token_data.access_token)
        logger.info(f"アクセストークンブラックリスト登録: {blacklist_result}")
        if not blacklist_result:
            logger.warning(f"アクセストークンブラックリスト登録失敗: {token_data.access_token}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="古いアクセストークンのブラックリスト登録に失敗しました。トークンを更新できません。"
            )
        
        # 新しいリフレッシュトークンを作成（トークンローテーション）
        new_refresh_token = await create_refresh_token(user.id, db)
        
        # 古いリフレッシュトークンを削除
        from app.crud.refresh_token import refresh_token_crud
        await refresh_token_crud.delete_refresh_token(db, token_data.refresh_token)
        
        logger.info(f"トークン更新成功: ユーザー名={user.username}")
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"トークン更新中にエラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="トークン更新中にエラーが発生しました"
        )


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    token_data: Optional[LogoutRequest] = None
):
    """ユーザーをログアウトし、アクセストークンとリフレッシュトークンを無効化"""
    logger = get_request_logger(request)
    logger.info(f"ログアウトリクエスト: ユーザーID={current_user.id}")
    
    try:
        # アクセストークンをブラックリストに追加
        # アクセストークンはAuthorizationヘッダーから取得
        authorization = request.headers.get("authorization")
        if authorization and authorization.startswith("Bearer "):
            access_token = authorization.split(" ")[1]
            blacklist_result = await blacklist_token(access_token, db)
            if not blacklist_result:
                logger.warning(f"アクセストークンブラックリスト登録失敗: {access_token}")
        
        # リフレッシュトークンが提供されている場合は無効化
        if token_data and token_data.refresh_token:
            revoke_result = await revoke_refresh_token(token_data.refresh_token, db)
            if not revoke_result:
                logger.warning(f"リフレッシュトークン削除失敗: {token_data.refresh_token}")
        
        logger.info(f"ログアウト成功: ユーザー名={current_user.username}")
        return {"message": "ログアウトしました"}
        
    except Exception as e:
        logger.error(f"ログアウト中にエラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ログアウト中にエラーが発生しました"
        )


@router.get("/me", response_model=UserSchema)
async def get_current_user_info(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """現在のユーザー情報を取得"""
    logger = get_request_logger(request)
    logger.info(f"ユーザー情報取得リクエスト: ユーザーID={current_user.id}")
    
    return current_user


@router.put("/password")
async def update_password(
    request: Request,
    password_data: PasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """認証されたユーザーのパスワードを更新"""
    logger = get_request_logger(request)
    logger.info(f"パスワード更新リクエスト: ユーザーID={current_user.id}")
    
    try:
        # 現在のパスワードを検証
        if not verify_password(password_data.old_password, current_user.hashed_password):
            logger.warning(f"パスワード更新失敗: ユーザー '{current_user.username}' の現在のパスワードが不正です")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="現在のパスワードが正しくありません"
            )
        
        # 新しいパスワードと現在のパスワードが同じかチェック
        if verify_password(password_data.new_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="新しいパスワードは現在のパスワードと異なる必要があります"
            )
        
        # パスワードを更新
        from app.core.security import get_password_hash
        hashed_new_password = get_password_hash(password_data.new_password)
        
        await user_crud.update_password(
            db=db, 
            user_id=current_user.id, 
            hashed_password=hashed_new_password
        )
        
        logger.info(f"パスワード更新成功: ユーザー名={current_user.username}")
        return {"message": "パスワードが正常に更新されました"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"パスワード更新中にエラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="パスワード更新中にエラーが発生しました"
        )
