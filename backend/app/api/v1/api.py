from fastapi import APIRouter

from app.api.v1.endpoints import users, articles, knowledge, auth

api_router = APIRouter()

# 各エンドポイントのルーターを登録
api_router.include_router(auth.router, prefix="/auth", tags=["認証"])
api_router.include_router(users.router, prefix="/users", tags=["ユーザー"])
#api_router.include_router(articles.router, prefix="/articles", tags=["記事"])
#api_router.include_router(knowledge.router, prefix="/knowledge", tags=["ナレッジ"])