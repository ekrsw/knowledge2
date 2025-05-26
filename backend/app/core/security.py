from datetime import datetime, timedelta, UTC
import json
import secrets
from typing import Dict, Any, Optional
import uuid

from passlib.context import CryptContext
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import app_logger
from app.db.session import get_async_session


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

async def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    非対称暗号を使用してアクセストークンを作成する関数
    
    Args:
        data: トークンに含めるデータ（通常はユーザーID）
        expires_delta: トークンの有効期限（指定がない場合はデフォルト値を使用）
        
    Returns:
        str: 生成されたJWTトークン
    """
    to_encode = data.copy()
    jti = str(uuid.uuid4())
    to_encode.update({"jti": jti})
    
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    # 秘密鍵を使用してトークンを署名
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.PRIVATE_KEY, 
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt

# ブラックリストに追加する関数
async def blacklist_token(token: str, db: AsyncSession) -> bool:
    """トークンをブラックリストに追加する"""
    # ブラックリスト機能が無効の場合は常にTrue（成功）を返す
    if not settings.TOKEN_BLACKLIST_ENABLED:
        return True
        
    try:
        # ここではブラックリストチェックを除外したトークン検証が必要
        # そうしないと無限ループになるので、直接JWTデコードする
        try:
            payload = jwt.decode(token,
                               settings.PUBLIC_KEY,
                               algorithms=[settings.ALGORITHM])
        except JWTError:
            return False
            
        if not payload:
            return False
            
        jti = payload.get("jti")
        if not jti:
            return False  # jtiがない場合は古いトークン形式
            
        exp = payload.get("exp")
        
        # 有効期限をdatetimeオブジェクトに変換
        expires_at = datetime.fromtimestamp(exp, tz=UTC)
        
        # SQLiteに保存
        from app.crud.token_blacklist import token_blacklist_crud
        await token_blacklist_crud.create_blacklist_entry(
            db=db,
            jti=jti,
            expires_at=expires_at
        )
        return True
    except Exception as e:
        app_logger.error(f"トークンのブラックリスト登録中にエラーが発生しました: {str(e)}", exc_info=True)
        return False

# ブラックリストチェック関数
async def is_token_blacklisted(payload: Dict[str, Any], db: AsyncSession) -> bool:
    """トークンがブラックリストに登録されているか確認"""
    # ブラックリスト機能が無効の場合は常にFalse（ブラックリストされていない）を返す
    if not settings.TOKEN_BLACKLIST_ENABLED:
        return False
        
    jti = payload.get("jti")
    if not jti:
        return False  # jtiがない場合は古いトークン形式なのでブラックリスト非対象
        
    # SQLiteでチェック
    try:
        from app.crud.token_blacklist import token_blacklist_crud
        return await token_blacklist_crud.is_blacklisted(db, jti)
    except Exception as e:
        app_logger.error(f"ブラックリストチェック中にエラーが発生しました: {str(e)}")
        return False

async def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    JWTトークンを検証し、ペイロードを返す関数
    
    Args:
        token: 検証するJWTトークン
        
    Returns:
        Optional[Dict[str, Any]]: トークンが有効な場合はペイロード、無効な場合はNone
    """
    try:
        # 公開鍵を使用してトークンを検証
        payload = jwt.decode(token,
                             settings.PUBLIC_KEY,
                             algorithms=[settings.ALGORITHM]
                             )
        
        # ブラックリストチェック（ブラックリスト機能が有効な場合のみ）
        if settings.TOKEN_BLACKLIST_ENABLED:
            # データベースセッションを取得してブラックリストチェック
            async for db in get_async_session():
                try:
                    if await is_token_blacklisted(payload, db):
                        return None
                finally:
                    await db.close()
                break
        
        return payload
    except JWTError:
        return None

async def create_refresh_token(auth_user_id: str, db: AsyncSession) -> str:
    """
    リフレッシュトークンを作成し、SQLiteに保存する関数
    
    Args:
        auth_user_id: ユーザーID
        db: データベースセッション
        
    Returns:
        str: 生成されたリフレッシュトークン
    """
    # ランダムなトークンを生成
    token = secrets.token_urlsafe(32)
    
    # 有効期限を計算
    expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    # SQLiteに保存
    try:
        # UUIDに変換（user_idがUUID形式の場合）
        user_uuid = uuid.UUID(auth_user_id)
        
        from app.crud.refresh_token import refresh_token_crud
        await refresh_token_crud.create_refresh_token(
            db=db,
            token=token,
            user_id=user_uuid,
            expires_at=expires_at
        )
        
        return token
    except Exception as e:
        app_logger.error(f"リフレッシュトークン作成中にエラーが発生しました: {str(e)}")
        raise

async def verify_refresh_token(token: str, db: AsyncSession) -> Optional[str]:
    """
    リフレッシュトークンを検証し、関連するユーザーIDを返す関数
    
    Args:
        token: 検証するリフレッシュトークン
        db: データベースセッション
        
    Returns:
        Optional[str]: トークンが有効な場合はユーザーID、無効な場合はNone
        
    Raises:
        JWTError: トークンの有効期限が切れている場合
    """
    try:
        # SQLiteからトークンを取得
        from app.crud.refresh_token import refresh_token_crud
        refresh_token = await refresh_token_crud.get_by_token(db, token)
        
        if not refresh_token:
            return None
        
        # ユーザーIDを文字列として返す
        return str(refresh_token.user_id)
        
    except Exception as e:
        if "ExpiredTokenError" in str(type(e).__name__):
            app_logger.warning(f"リフレッシュトークンの有効期限切れ")
            # 期限切れのトークンを削除
            await revoke_refresh_token(token, db)
            raise jwt.JWTError("リフレッシュトークンの有効期限が切れています")
        
        app_logger.error(f"リフレッシュトークン検証中にエラーが発生しました: {str(e)}")
        return None

async def revoke_refresh_token(token: str, db: AsyncSession) -> bool:
    """
    リフレッシュトークンを無効化する関数
    
    Args:
        token: 無効化するリフレッシュトークン
        db: データベースセッション
        
    Returns:
        bool: 無効化に成功した場合はTrue、失敗した場合はFalse
    """
    try:
        # SQLiteから削除
        from app.crud.refresh_token import refresh_token_crud
        return await refresh_token_crud.delete_refresh_token(db, token)
    except Exception as e:
        app_logger.error(f"リフレッシュトークン削除中にエラーが発生しました: {str(e)}")
        return False
