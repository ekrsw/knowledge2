from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from app.api.deps import get_current_user, get_admin_user
from app.core.exceptions import (
    InvalidParameterError,
    DatabaseConnectionError,
    UserNotFoundError
)
from app.core.logging import get_request_logger
from app.crud.user import user_crud
from app.db.session import get_async_session
from app.models import User
from app.schemas import User as UserSchema, UserWithKnowledge

router = APIRouter()


@router.get("/", response_model=List[UserSchema])
async def read_users(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_session)
):
    """ユーザー一覧を取得"""
    logger = get_request_logger(request)
    logger.info(f"ユーザー一覧取得リクエスト: skip={skip}, limit={limit}")
    
    try:
        users = await user_crud.get_multi(db, skip=skip, limit=limit)
        logger.info(f"ユーザー一覧取得成功: {len(users)}件")
        return users
    except Exception as e:
        logger.error(f"ユーザー一覧取得中にエラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ユーザー一覧の取得中にエラーが発生しました"
        )


@router.get("/{user_id}", response_model=UserWithKnowledge)
async def read_user(
    request: Request,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session)
):
    """特定のユーザーとナレッジを取得"""
    logger = get_request_logger(request)
    logger.info(f"ユーザー詳細取得リクエスト: user_id={user_id}")
    
    try:
        db_user = await user_crud.get(db, id=user_id)
        return db_user
    except InvalidParameterError:
        raise
    except DatabaseConnectionError:
        raise
    except UserNotFoundError:
        raise
    except SQLAlchemyError:
        raise
    except Exception as e:
        logger.error(f"ユーザー詳細取得中にエラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ユーザー詳細の取得中にエラーが発生しました"
        )