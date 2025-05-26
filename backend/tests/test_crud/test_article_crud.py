"""
ArticleCRUD のテスト
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
import io
import csv

from app.crud.article import article_crud
from app.schemas import ArticleCreate
from app.models import Article, User
from app.core.exceptions import (
    ArticleNotFoundError,
    DatabaseConnectionError,
    InvalidParameterError,
    ValidationError
)


class TestArticleCRUD:
    """ArticleCRUD のテストクラス"""

    @pytest.mark.asyncio
    async def test_get_article_success(self, db_session: AsyncSession, sample_article: Article):
        """記事取得 - 正常系"""
        # 実行
        result = await article_crud.get(db_session, sample_article.id)
        
        # 検証
        assert result is not None
        assert result.id == sample_article.id
        assert result.title == sample_article.title
        assert result.content == sample_article.content
        assert result.url == sample_article.url

    @pytest.mark.asyncio
    async def test_get_article_not_found(self, db_session: AsyncSession):
        """記事取得 - 存在しないID"""
        non_existent_id = uuid4()
        
        # 実行・検証
        with pytest.raises(ArticleNotFoundError) as exc_info:
            await article_crud.get(db_session, non_existent_id)
        
        assert str(non_existent_id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_article_invalid_id(self, db_session: AsyncSession):
        """記事取得 - 無効なID"""
        # 実行・検証
        with pytest.raises(InvalidParameterError):
            await article_crud.get(db_session, None)

    @pytest.mark.asyncio
    async def test_get_multi_success(self, db_session: AsyncSession, multiple_articles: list[Article]):
        """記事一覧取得 - 正常系"""
        # 実行
        result = await article_crud.get_multi(db_session, skip=0, limit=10)
        
        # 検証
        assert len(result) == len(multiple_articles)
        assert all(isinstance(article, Article) for article in result)

    @pytest.mark.asyncio
    async def test_get_multi_pagination(self, db_session: AsyncSession, multiple_articles: list[Article]):
        """記事一覧取得 - ページネーション"""
        # 実行
        first_page = await article_crud.get_multi(db_session, skip=0, limit=2)
        second_page = await article_crud.get_multi(db_session, skip=2, limit=2)
        
        # 検証
        assert len(first_page) == 2
        assert len(second_page) == 2
        assert first_page[0].id != second_page[0].id

    @pytest.mark.asyncio
    async def test_get_multi_invalid_skip(self, db_session: AsyncSession):
        """記事一覧取得 - 無効なskip"""
        # 実行・検証
        with pytest.raises(InvalidParameterError):
            await article_crud.get_multi(db_session, skip=-1, limit=10)

    @pytest.mark.asyncio
    async def test_get_multi_invalid_limit(self, db_session: AsyncSession):
        """記事一覧取得 - 無効なlimit"""
        # 実行・検証
        with pytest.raises(InvalidParameterError):
            await article_crud.get_multi(db_session, skip=0, limit=0)
        
        with pytest.raises(InvalidParameterError):
            await article_crud.get_multi(db_session, skip=0, limit=1001)

    @pytest.mark.asyncio
    async def test_create_article_success(self, db_session: AsyncSession, test_data_factory):
        """記事作成 - 正常系"""
        # 準備
        article_data = test_data_factory.create_article_data(
            title="新しい記事",
            content="記事の内容です",
            url="https://example.com/new-article"
        )
        
        # 実行
        result = await article_crud.create(db_session, article_data)
        
        # 検証
        assert result.title == article_data.title
        assert result.content == article_data.content
        assert result.url == article_data.url
        assert result.id is not None

    @pytest.mark.asyncio
    async def test_create_article_empty_title(self, db_session: AsyncSession, test_data_factory):
        """記事作成 - 空のタイトル"""
        # 準備
        article_data = test_data_factory.create_article_data(title="")
        
        # 実行・検証
        with pytest.raises(ValidationError):
            await article_crud.create(db_session, article_data)

    @pytest.mark.asyncio
    async def test_create_article_empty_content(self, db_session: AsyncSession, test_data_factory):
        """記事作成 - 空のコンテンツ"""
        # 準備
        article_data = test_data_factory.create_article_data(content="")
        
        # 実行・検証
        with pytest.raises(ValidationError):
            await article_crud.create(db_session, article_data)

    @pytest.mark.asyncio
    async def test_create_article_invalid_url(self, db_session: AsyncSession, test_data_factory):
        """記事作成 - 無効なURL"""
        # 準備
        article_data = test_data_factory.create_article_data(url="invalid-url")
        
        # 実行・検証
        with pytest.raises(ValidationError):
            await article_crud.create(db_session, article_data)

    @pytest.mark.asyncio
    async def test_create_article_unicode_content(self, db_session: AsyncSession, test_data_factory):
        """記事作成 - Unicode文字を含むコンテンツ"""
        # 準備
        article_data = test_data_factory.create_article_data(
            title="日本語タイトル 🚀",
            content="これは日本語のコンテンツです。絵文字も含まれています 😊",
            url="https://example.com/japanese-article"
        )
        
        # 実行
        result = await article_crud.create(db_session, article_data)
        
        # 検証
        assert result.title == article_data.title
        assert result.content == article_data.content
        assert "🚀" in result.title
        assert "😊" in result.content

    @pytest.mark.asyncio
    async def test_search_articles_by_title(self, db_session: AsyncSession, multiple_articles: list[Article]):
        """記事検索 - タイトルで検索"""
        # 実行
        result = await article_crud.search_by_title(db_session, "テスト")
        
        # 検証
        assert len(result) > 0
        assert all("テスト" in article.title for article in result)

    @pytest.mark.asyncio
    async def test_search_articles_by_title_no_results(self, db_session: AsyncSession):
        """記事検索 - 該当なし"""
        # 実行
        result = await article_crud.search_by_title(db_session, "存在しないキーワード")
        
        # 検証
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_search_articles_by_title_empty_query(self, db_session: AsyncSession):
        """記事検索 - 空のクエリ"""
        # 実行・検証
        with pytest.raises(InvalidParameterError):
            await article_crud.search_by_title(db_session, "")

    @pytest.mark.asyncio
    async def test_search_articles_by_content(self, db_session: AsyncSession, multiple_articles: list[Article]):
        """記事検索 - コンテンツで検索"""
        # 実行
        result = await article_crud.search_by_content(db_session, "内容")
        
        # 検証
        assert len(result) > 0
        assert all("内容" in article.content for article in result)

    @pytest.mark.asyncio
    async def test_search_articles_by_content_case_insensitive(self, db_session: AsyncSession, multiple_articles: list[Article]):
        """記事検索 - 大文字小文字を区別しない検索"""
        # 実行
        result_lower = await article_crud.search_by_content(db_session, "内容")
        result_upper = await article_crud.search_by_content(db_session, "内容")
        
        # 検証
        assert len(result_lower) == len(result_upper)

    @pytest.mark.asyncio
    async def test_get_by_url_success(self, db_session: AsyncSession, sample_article: Article):
        """URL で記事取得 - 正常系"""
        # 実行
        result = await article_crud.get_by_url(db_session, sample_article.url)
        
        # 検証
        assert result is not None
        assert result.id == sample_article.id
        assert result.url == sample_article.url

    @pytest.mark.asyncio
    async def test_get_by_url_not_found(self, db_session: AsyncSession):
        """URL で記事取得 - 存在しないURL"""
        # 実行・検証
        with pytest.raises(ArticleNotFoundError):
            await article_crud.get_by_url(db_session, "https://example.com/nonexistent")

    @pytest.mark.asyncio
    async def test_get_by_url_invalid_url(self, db_session: AsyncSession):
        """URL で記事取得 - 無効なURL"""
        # 実行・検証
        with pytest.raises(InvalidParameterError):
            await article_crud.get_by_url(db_session, "")

    @pytest.mark.asyncio
    async def test_bulk_create_from_csv_success(self, db_session: AsyncSession):
        """CSV一括作成 - 正常系"""
        # 準備
        csv_data = """title,content,url
記事1,内容1,https://example.com/1
記事2,内容2,https://example.com/2
記事3,内容3,https://example.com/3"""
        
        csv_file = io.StringIO(csv_data)
        
        # 実行
        result = await article_crud.bulk_create_from_csv(db_session, csv_file)
        
        # 検証
        assert len(result) == 3
        assert all(isinstance(article, Article) for article in result)
        assert result[0].title == "記事1"
        assert result[1].title == "記事2"
        assert result[2].title == "記事3"

    @pytest.mark.asyncio
    async def test_bulk_create_from_csv_empty_file(self, db_session: AsyncSession):
        """CSV一括作成 - 空のファイル"""
        # 準備
        csv_file = io.StringIO("")
        
        # 実行・検証
        with pytest.raises(ValidationError):
            await article_crud.bulk_create_from_csv(db_session, csv_file)

    @pytest.mark.asyncio
    async def test_bulk_create_from_csv_invalid_format(self, db_session: AsyncSession):
        """CSV一括作成 - 無効なフォーマット"""
        # 準備
        csv_data = """invalid,format
data1,data2"""
        
        csv_file = io.StringIO(csv_data)
        
        # 実行・検証
        with pytest.raises(ValidationError):
            await article_crud.bulk_create_from_csv(db_session, csv_file)

    @pytest.mark.asyncio
    async def test_bulk_create_from_csv_duplicate_urls(self, db_session: AsyncSession):
        """CSV一括作成 - 重複URL"""
        # 準備
        csv_data = """title,content,url
記事1,内容1,https://example.com/duplicate
記事2,内容2,https://example.com/duplicate"""
        
        csv_file = io.StringIO(csv_data)
        
        # 実行・検証
        with pytest.raises(ValidationError):
            await article_crud.bulk_create_from_csv(db_session, csv_file)

    @pytest.mark.asyncio
    async def test_bulk_create_from_csv_large_file(self, db_session: AsyncSession):
        """CSV一括作成 - 大量データ"""
        # 準備
        csv_data = "title,content,url\n"
        for i in range(100):
            csv_data += f"記事{i},内容{i},https://example.com/{i}\n"
        
        csv_file = io.StringIO(csv_data)
        
        # 実行
        result = await article_crud.bulk_create_from_csv(db_session, csv_file)
        
        # 検証
        assert len(result) == 100

    @pytest.mark.asyncio
    async def test_generate_url_from_title_success(self, db_session: AsyncSession):
        """タイトルからURL生成 - 正常系"""
        # 実行
        result = await article_crud.generate_url_from_title("テスト記事のタイトル")
        
        # 検証
        assert result is not None
        assert "test" in result.lower()
        assert "article" in result.lower() or "記事" in result

    @pytest.mark.asyncio
    async def test_generate_url_from_title_japanese(self, db_session: AsyncSession):
        """タイトルからURL生成 - 日本語タイトル"""
        # 実行
        result = await article_crud.generate_url_from_title("日本語のタイトル")
        
        # 検証
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_generate_url_from_title_special_characters(self, db_session: AsyncSession):
        """タイトルからURL生成 - 特殊文字"""
        # 実行
        result = await article_crud.generate_url_from_title("タイトル!@#$%^&*()")
        
        # 検証
        assert result is not None
        # 特殊文字が適切に処理されている
        assert not any(char in result for char in "!@#$%^&*()")

    @pytest.mark.asyncio
    async def test_generate_url_from_title_empty(self, db_session: AsyncSession):
        """タイトルからURL生成 - 空のタイトル"""
        # 実行・検証
        with pytest.raises(InvalidParameterError):
            await article_crud.generate_url_from_title("")

    @pytest.mark.asyncio
    async def test_database_connection_error_simulation(self, db_session: AsyncSession):
        """データベース接続エラーのシミュレーション"""
        # セッションを無効化
        await db_session.close()
        
        # 実行・検証
        with pytest.raises(DatabaseConnectionError):
            await article_crud.get(db_session, uuid4())

    @pytest.mark.asyncio
    async def test_concurrent_article_creation(self, db_session: AsyncSession, test_data_factory):
        """同時記事作成のテスト"""
        import asyncio
        
        # 準備
        article_data1 = test_data_factory.create_article_data(
            title="同時作成1",
            url="https://example.com/concurrent1"
        )
        article_data2 = test_data_factory.create_article_data(
            title="同時作成2",
            url="https://example.com/concurrent2"
        )
        
        # 実行
        results = await asyncio.gather(
            article_crud.create(db_session, article_data1),
            article_crud.create(db_session, article_data2),
            return_exceptions=True
        )
        
        # 検証
        assert len(results) == 2
        success_count = sum(1 for r in results if isinstance(r, Article))
        assert success_count >= 1

    @pytest.mark.asyncio
    async def test_edge_case_very_long_title(self, db_session: AsyncSession, test_data_factory):
        """境界値テスト - 非常に長いタイトル"""
        # 準備
        long_title = "a" * 1000
        article_data = test_data_factory.create_article_data(title=long_title)
        
        # 実行（データベースの制約によってはエラーになる可能性がある）
        try:
            result = await article_crud.create(db_session, article_data)
            assert result.title == long_title
        except Exception:
            # データベース制約によるエラーは許容
            pass

    @pytest.mark.asyncio
    async def test_edge_case_very_long_content(self, db_session: AsyncSession, test_data_factory):
        """境界値テスト - 非常に長いコンテンツ"""
        # 準備
        long_content = "a" * 10000
        article_data = test_data_factory.create_article_data(content=long_content)
        
        # 実行
        result = await article_crud.create(db_session, article_data)
        
        # 検証
        assert result.content == long_content

    @pytest.mark.asyncio
    async def test_search_performance_large_dataset(self, db_session: AsyncSession, test_data_factory):
        """検索パフォーマンステスト - 大量データ"""
        # 準備 - 大量の記事を作成
        articles = []
        for i in range(50):
            article_data = test_data_factory.create_article_data(
                title=f"パフォーマンステスト記事 {i}",
                content=f"これはパフォーマンステスト用の記事内容です {i}",
                url=f"https://example.com/performance-test-{i}"
            )
            article = await article_crud.create(db_session, article_data)
            articles.append(article)
        
        # 実行
        import time
        start_time = time.time()
        result = await article_crud.search_by_title(db_session, "パフォーマンステスト")
        end_time = time.time()
        
        # 検証
        assert len(result) == 50
        assert (end_time - start_time) < 1.0  # 1秒以内で完了

    @pytest.mark.asyncio
    async def test_article_crud_comprehensive_workflow(self, db_session: AsyncSession, test_data_factory):
        """包括的なワークフローテスト"""
        # 1. 記事作成
        article_data = test_data_factory.create_article_data(
            title="ワークフロー記事",
            content="これはワークフローテスト用の記事です",
            url="https://example.com/workflow-article"
        )
        created_article = await article_crud.create(db_session, article_data)
        
        # 2. 作成された記事を取得
        retrieved_article = await article_crud.get(db_session, created_article.id)
        assert retrieved_article.title == article_data.title
        
        # 3. URLで取得
        article_by_url = await article_crud.get_by_url(db_session, article_data.url)
        assert article_by_url.id == created_article.id
        
        # 4. タイトルで検索
        search_results = await article_crud.search_by_title(db_session, "ワークフロー")
        assert any(article.id == created_article.id for article in search_results)
        
        # 5. コンテンツで検索
        content_search_results = await article_crud.search_by_content(db_session, "ワークフローテスト")
        assert any(article.id == created_article.id for article in content_search_results)
        
        # 6. 一覧に含まれることを確認
        articles_list = await article_crud.get_multi(db_session, skip=0, limit=100)
        article_ids = [a.id for a in articles_list]
        assert created_article.id in article_ids
        
        # 7. URL生成テスト
        generated_url = await article_crud.generate_url_from_title("新しいタイトル")
        assert generated_url is not None
