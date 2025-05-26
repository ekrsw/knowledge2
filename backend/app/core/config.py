import os
from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from typing import Optional, Literal


class Settings(BaseSettings):
    # 環境設定
    ENVIRONMENT: Literal["development", "testing", "production"] = "development"

    # アプリケーション設定
    APP_NAME: str = "ナレッジ投稿システム"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True

    # ロギング設定
    LOG_LEVEL: str = "INFO"
    LOG_TO_FILE: bool = False
    LOG_FILE_PATH: str = "logs/knowledge_service.log"

    # データベース設定
    DATABASE_URL: str = "sqlite+aiosqlite:///./knowledge.db"
    SQLALCHEMY_ECHO: bool = True
    TZ: str = "Asia/Tokyo"

    # セキュリティ設定
    ALGORITHM: str = "RS256"
    PRIVATE_KEY_PATH: str = "keys/private.pem"  # 秘密鍵のパス
    PUBLIC_KEY_PATH: str = "keys/public.pem"   # 公開鍵のパス
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    TOKEN_BLACKLIST_ENABLED: bool = True

    # CORS設定
    CORS_ORIGINS: list[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    # ページネーション設定
    DEFAULT_PAGE_SIZE: int = 100
    MAX_PAGE_SIZE: int = 1000

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


settings = Settings()