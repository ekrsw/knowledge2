from app.core.logging import get_logger
from app.db.session import async_engine
from app.db.base import Base

# このモジュール用のロガーを取得
logger = get_logger(__name__)


class Database:
    """データベース初期化クラス"""
    
    async def init(self):
        """データベースの初期化"""
        try:
            logger.info("Initializing database...")
            
            # テーブルの作成
            async with async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            raise
    
    async def close(self):
        """データベース接続のクローズ"""
        try:
            logger.info("Closing database connections...")
            await async_engine.dispose()
            logger.info("Database connections closed successfully")
        except Exception as e:
            logger.error(f"Error closing database connections: {str(e)}")
            raise