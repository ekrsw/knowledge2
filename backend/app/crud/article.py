from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List, Optional
import csv
import io
from uuid import UUID

from app.core.exceptions import ArticleNotFoundError, DuplicateArticleError, DatabaseQueryError
from app.core.logging import get_logger
from app.models import Article
from app.schemas import ArticleCreate


class ArticleCRUD:
    """記事関連のCRUD操作"""
    logger = get_logger(__name__)
    async def get_by_uuid(self, db: AsyncSession, article_uuid: UUID) -> Optional[Article]:
        """IDで記事を取得"""
        self.logger.info(f"Retrieving article by uuid: {article_uuid}")
        result = await db.execute(select(Article).filter(Article.article_uuid == article_uuid))
        article =  result.scalar_one_or_none()
        if article:
            self.logger.info(f"Found article with uuid: {article_uuid}")
        else:
            self.logger.info(f"Article with uuid {article_uuid} not found")
        return article
    
    async def get_by_number(self, db: AsyncSession, article_number: str) -> Optional[Article]:
        """記事番号で記事を取得"""
        self.logger.info(f"Retrieving article by article number: {article_number}")
        result = await db.execute(
            select(Article).where(Article.article_number == article_number)
        )
        article = result.scalar_one_or_none()
        if article:
            self.logger.info(f"Found article with article number: {article_number}")
        else:
            self.logger.info(f"Article with article number {article_number} not found")
        return article
    
    async def get_multi(
        self, 
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Article]:
        """記事一覧を取得（有効な記事のみ）"""
        self.logger.info(f"Retrieving all articles")
        try:
            result = await db.execute(
                select(Article)
                .where(Article.is_active == True)
                .offset(skip)
                .limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Error retrieving all articles: {str(e)}")
            raise DatabaseQueryError(f"Failed to retrieve all articles: {str(e)}") from e

    
    async def search(
        self, 
        db: AsyncSession, 
        query: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Article]:
        """記事番号またはタイトルで記事を検索"""
        result = await db.execute(
            select(Article)
            .where(
                Article.is_active == True,
                or_(
                    Article.article_number.contains(query),
                    Article.title.contains(query)
                )
            )
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def create(self, db: AsyncSession, obj_in: ArticleCreate) -> Article:
        """新しい記事を作成"""
        self.logger.info(f"Creating new article: {obj_in.article_number}")
        # 記事番号の重複チェック
        existing_article = await self.get_by_number(db, obj_in.article_number)
        if existing_article:
            raise DuplicateArticleError(obj_in.article_number)
        
        db_obj = Article(
            article_uuid=obj_in.article_uuid,
            article_number=obj_in.article_number,
            title=obj_in.title
        )
        db.add(db_obj)
        await db.flush()
        # commitはsessionのfinallyで行う
        return db_obj
    
    async def import_from_csv(self, db: AsyncSession, csv_content: str) -> dict:
        """CSVから記事を一括インポート"""
        result = {"success": 0, "errors": [], "duplicates": []}
        
        try:
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            
            for row_num, row in enumerate(csv_reader, start=2):  # ヘッダー行を考慮して2から開始
                try:
                    # 必須フィールドのチェック
                    if not all(key in row for key in ['article_uuid', 'article_number', 'title']):
                        result["errors"].append(f"行 {row_num}: 必須フィールドが不足しています")
                        continue
                    
                    # 重複チェック
                    existing_article = await self.get_by_number(db, row['article_number'])
                    if existing_article:
                        result["duplicates"].append(f"行 {row_num}: 記事番号 {row['article_number']} は既に存在します")
                        continue
                    
                    # 記事作成
                    article_data = ArticleCreate(
                        article_uuid=row['article_uuid'],
                        article_number=row['article_number'],
                        title=row['title'],
                        content=row.get('content', '')
                    )
                    
                    await self.create(db, article_data)
                    result["success"] += 1
                    
                except Exception as e:
                    result["errors"].append(f"行 {row_num}: {str(e)}")
                    
        except Exception as e:
            result["errors"].append(f"CSV解析エラー: {str(e)}")
        
        return result
    
    def generate_article_url(self, article_uuid: str) -> str:
        """記事のURLを生成"""
        base_url = "http://sv-vw-ejap:5555/SupportCenter/main.aspx"
        params = f"?etc=127&extraqs=%3fetc%3d127%26id%3d%257b{article_uuid}%257d&newWindow=true&pagetype=entityrecord"
        return base_url + params


# シングルトンインスタンス
article_crud = ArticleCRUD()