from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import List, Optional
import csv
import io
from uuid import UUID

from app.core.exceptions import (
    ArticleNotFoundError, 
    DuplicateArticleError, 
    DatabaseQueryError,
    DatabaseConnectionError,
    DatabaseIntegrityError,
    InvalidParameterError,
    ValidationError,
    CsvProcessingError
)
from app.core.logging import get_logger
from app.models import Article
from app.schemas import ArticleCreate


class ArticleCRUD:
    """記事関連のCRUD操作"""
    logger = get_logger(__name__)
    
    async def get(self, db: AsyncSession, id: UUID) -> Optional[Article]:
        """IDで記事を取得"""
        if not id:
            self.logger.error("Article ID is required")
            raise InvalidParameterError("id", id, "記事IDが必要です")
        
        try:
            self.logger.info(f"Retrieving article by id: {id}")
            
            # データベース接続チェック
            if not db.is_active:
                self.logger.error("Database session is not active")
                raise DatabaseConnectionError("データベースセッションがアクティブではありません")
            
            result = await db.execute(select(Article).filter(Article.id == id))
            article = result.scalar_one_or_none()
            
            if article:
                self.logger.info(f"Found article with id: {id}")
                return article
            else:
                self.logger.info(f"Article with id {id} not found")
                raise ArticleNotFoundError(f"記事ID {id} が見つかりません")
                
        except InvalidParameterError:
            raise
        except DatabaseConnectionError:
            raise
        except ArticleNotFoundError:
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error retrieving article by id {id}: {str(e)}")
            raise DatabaseQueryError(f"記事ID取得中にデータベースエラーが発生しました: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving article by id {id}: {str(e)}")
            raise DatabaseQueryError(f"記事ID取得中に予期しないエラーが発生しました: {str(e)}") from e
    
    async def get_by_uuid(self, db: AsyncSession, article_uuid: UUID) -> Optional[Article]:
        """UUIDで記事を取得"""
        try:
            # パラメータ検証
            if not article_uuid:
                self.logger.error("Article UUID is required")
                raise InvalidParameterError("article_uuid", article_uuid, "記事UUIDが必要です")
            
            self.logger.info(f"Retrieving article by uuid: {article_uuid}")
            
            # データベース接続チェック
            if not db.is_active:
                self.logger.error("Database session is not active")
                raise DatabaseConnectionError("データベースセッションがアクティブではありません")
            
            result = await db.execute(select(Article).filter(Article.article_uuid == article_uuid))
            article = result.scalar_one_or_none()
            
            if article:
                self.logger.info(f"Found article with uuid: {article_uuid}")
            else:
                self.logger.info(f"Article with uuid {article_uuid} not found")
            
            return article
            
        except InvalidParameterError:
            raise
        except DatabaseConnectionError:
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error retrieving article by uuid {article_uuid}: {str(e)}")
            raise DatabaseQueryError(f"記事UUID取得中にデータベースエラーが発生しました: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving article by uuid {article_uuid}: {str(e)}")
            raise DatabaseQueryError(f"記事UUID取得中に予期しないエラーが発生しました: {str(e)}") from e
    
    async def get_by_number(self, db: AsyncSession, article_number: str) -> Optional[Article]:
        """記事番号で記事を取得"""
        try:
            # パラメータ検証
            if not article_number or not article_number.strip():
                self.logger.error("Article number is required and cannot be empty")
                raise InvalidParameterError("article_number", article_number, "記事番号が必要です")
            
            self.logger.info(f"Retrieving article by article number: {article_number}")
            
            # データベース接続チェック
            if not db.is_active:
                self.logger.error("Database session is not active")
                raise DatabaseConnectionError("データベースセッションがアクティブではありません")
            
            result = await db.execute(
                select(Article).where(Article.article_number == article_number)
            )
            article = result.scalar_one_or_none()
            
            if article:
                self.logger.info(f"Found article with article number: {article_number}")
            else:
                self.logger.info(f"Article with article number {article_number} not found")
            
            return article
            
        except InvalidParameterError:
            raise
        except DatabaseConnectionError:
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error retrieving article by number {article_number}: {str(e)}")
            raise DatabaseQueryError(f"記事番号取得中にデータベースエラーが発生しました: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving article by number {article_number}: {str(e)}")
            raise DatabaseQueryError(f"記事番号取得中に予期しないエラーが発生しました: {str(e)}") from e
    
    async def get_multi(
        self, 
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Article]:
        """記事一覧を取得（有効な記事のみ）"""
        # パラメータ検証
        if skip < 0:
            raise InvalidParameterError("skip", skip, "skipは0以上である必要があります")
        if limit <= 0 or limit > 1000:
            raise InvalidParameterError("limit", limit, "limitは1以上1000以下である必要があります")
        
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
    
    async def search_by_title(self, db: AsyncSession, query: str) -> List[Article]:
        """タイトルで記事を検索"""
        if not query or not query.strip():
            raise InvalidParameterError("query", query, "検索クエリが必要です")
        
        try:
            result = await db.execute(
                select(Article)
                .where(
                    Article.is_active == True,
                    Article.title.contains(query)
                )
            )
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Error searching articles by title: {str(e)}")
            raise DatabaseQueryError(f"タイトル検索中にエラーが発生しました: {str(e)}") from e
    
    async def search_by_content(self, db: AsyncSession, query: str) -> List[Article]:
        """コンテンツで記事を検索"""
        if not query or not query.strip():
            raise InvalidParameterError("query", query, "検索クエリが必要です")
        
        try:
            result = await db.execute(
                select(Article)
                .where(
                    Article.is_active == True,
                    Article.content.contains(query)
                )
            )
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Error searching articles by content: {str(e)}")
            raise DatabaseQueryError(f"コンテンツ検索中にエラーが発生しました: {str(e)}") from e
    
    async def get_by_url(self, db: AsyncSession, url: str) -> Optional[Article]:
        """URLで記事を取得（記事UUIDから生成されたURLで検索）"""
        if not url or not url.strip():
            raise InvalidParameterError("url", url, "URLが必要です")
        
        try:
            # URLから記事UUIDを抽出
            import re
            uuid_match = re.search(r'%257b([^%]+)%257d', url)
            if not uuid_match:
                raise ArticleNotFoundError(f"URL {url} から記事UUIDを抽出できません")
            
            article_uuid = uuid_match.group(1)
            result = await db.execute(
                select(Article).where(Article.article_uuid == article_uuid)
            )
            article = result.scalar_one_or_none()
            
            if not article:
                raise ArticleNotFoundError(f"URL {url} の記事が見つかりません")
            
            return article
        except ArticleNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Error retrieving article by URL: {str(e)}")
            raise DatabaseQueryError(f"URL検索中にエラーが発生しました: {str(e)}") from e
    
    async def create(self, db: AsyncSession, obj_in: ArticleCreate) -> Article:
        """新しい記事を作成"""
        # バリデーション
        if not obj_in.title or not obj_in.title.strip():
            raise ValidationError("タイトルが必要です")
        if not obj_in.article_number or not obj_in.article_number.strip():
            raise ValidationError("記事番号が必要です")
        if hasattr(obj_in, 'content') and obj_in.content is not None and not obj_in.content.strip():
            raise ValidationError("コンテンツが必要です")
        
        self.logger.info(f"Creating new article: {obj_in.article_number}")
        # 記事番号の重複チェック
        existing_article = await self.get_by_number(db, obj_in.article_number)
        if existing_article:
            raise DuplicateArticleError(obj_in.article_number)
        
        db_obj = Article(
            article_uuid=obj_in.article_uuid,
            article_number=obj_in.article_number,
            title=obj_in.title,
            content=getattr(obj_in, 'content', None)
        )
        db.add(db_obj)
        await db.flush()
        # commitはsessionのfinallyで行う
        return db_obj
    
    def _is_valid_url(self, url: str) -> bool:
        """URLの妥当性をチェック"""
        import re
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return url_pattern.match(url) is not None
    
    async def bulk_create_from_csv(self, db: AsyncSession, csv_file) -> List[Article]:
        """CSVファイルから記事を一括作成"""
        if not csv_file:
            raise ValidationError("CSVファイルが必要です")
        
        try:
            # CSVファイルの内容を読み取り
            csv_content = csv_file.read()
            if not csv_content.strip():
                raise ValidationError("CSVファイルが空です")
            
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            
            # ヘッダーの検証
            required_headers = ['title', 'content', 'url']
            if not all(header in csv_reader.fieldnames for header in required_headers):
                raise ValidationError(f"必須ヘッダーが不足しています: {required_headers}")
            
            articles = []
            urls_in_csv = set()
            
            for row_num, row in enumerate(csv_reader, start=2):
                # 重複URLチェック（CSV内）
                if row['url'] in urls_in_csv:
                    raise ValidationError(f"CSV内でURLが重複しています: {row['url']}")
                urls_in_csv.add(row['url'])
                
                # UUIDと記事番号を生成
                import uuid
                article_uuid = str(uuid.uuid4())
                article_number = f"CSV-{row_num:05d}"
                
                # 記事作成データの準備
                article_data = ArticleCreate(
                    article_uuid=article_uuid,
                    article_number=article_number,
                    title=row['title'],
                    content=row['content']
                )
                
                # 記事作成
                article = await self.create(db, article_data)
                articles.append(article)
            
            return articles
            
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Error in bulk create from CSV: {str(e)}")
            raise ValidationError(f"CSV処理中にエラーが発生しました: {str(e)}") from e
    
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
    
    async def generate_url_from_title(self, title: str) -> str:
        """タイトルからURLを生成"""
        if not title or not title.strip():
            raise InvalidParameterError("title", title, "タイトルが必要です")
        
        import re
        import unicodedata
        
        # Unicode正規化
        normalized = unicodedata.normalize('NFKD', title)
        
        # 特殊文字を除去し、スペースをハイフンに変換
        cleaned = re.sub(r'[^\w\s-]', '', normalized)
        cleaned = re.sub(r'[-\s]+', '-', cleaned)
        
        # 先頭と末尾のハイフンを除去
        cleaned = cleaned.strip('-')
        
        # 小文字に変換
        url_slug = cleaned.lower()
        
        # 空の場合はデフォルト値を返す
        if not url_slug:
            url_slug = "article"
        
        return f"https://example.com/articles/{url_slug}"
    
    def generate_article_url(self, article_uuid: str) -> str:
        """記事のURLを生成"""
        base_url = "http://sv-vw-ejap:5555/SupportCenter/main.aspx"
        params = f"?etc=127&extraqs=%3fetc%3d127%26id%3d%257b{article_uuid}%257d&newWindow=true&pagetype=entityrecord"
        return base_url + params


# シングルトンインスタンス
article_crud = ArticleCRUD()
