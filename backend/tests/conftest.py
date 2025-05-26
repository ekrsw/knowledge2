"""
テスト用の共通フィクスチャとセットアップ
"""
import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, date
from uuid import uuid4
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import User, Article, Knowledge, RefreshToken, TokenBlacklist
from app.schemas import UserCreate, ArticleCreate, KnowledgeCreate
from app.core.security import get_password_hash
from app.models.knowledge import StatusEnum, ChangeTypeEnum


# テスト用のインメモリSQLiteデータベース設定
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """セッションスコープのイベントループ"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """テスト用データベースエンジン"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
        },
    )
    
    # テーブル作成
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # クリーンアップ
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """テスト用データベースセッション（各テストでロールバック）"""
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # トランザクション開始
        transaction = await session.begin()
        
        try:
            yield session
        finally:
            # テスト後にロールバック
            await transaction.rollback()


@pytest_asyncio.fixture
async def sample_user(db_session: AsyncSession) -> User:
    """サンプルユーザー"""
    user = User(
        id=uuid4(),
        username="testuser",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User",
        is_admin=False
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """管理者ユーザー"""
    user = User(
        id=uuid4(),
        username="admin",
        hashed_password=get_password_hash("adminpassword123"),
        full_name="Admin User",
        is_admin=True
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def sample_article(db_session: AsyncSession) -> Article:
    """サンプル記事"""
    article = Article(
        article_uuid=str(uuid4()),
        article_number="ART-001",
        title="Sample Article",
        content="This is a sample article content.",
        is_active=True
    )
    db_session.add(article)
    await db_session.flush()
    await db_session.refresh(article)
    return article


@pytest_asyncio.fixture
async def sample_knowledge(db_session: AsyncSession, sample_user: User, sample_article: Article) -> Knowledge:
    """サンプルナレッジ"""
    knowledge = Knowledge(
        id=uuid4(),
        article_number=sample_article.article_number,
        change_type=ChangeTypeEnum.modify,
        title="Sample Knowledge",
        info_category="テスト",
        keywords="test,sample",
        importance=True,
        target="開発者",
        open_publish_start=date.today(),
        open_publish_end=date.today() + timedelta(days=30),
        question="これはテスト用の質問ですか？",
        answer="はい、これはテスト用の回答です。",
        add_comments="追加コメント",
        remarks="備考",
        status=StatusEnum.draft,
        created_by=sample_user.id
    )
    db_session.add(knowledge)
    await db_session.flush()
    await db_session.refresh(knowledge)
    return knowledge


@pytest_asyncio.fixture
async def sample_refresh_token(db_session: AsyncSession, sample_user: User) -> RefreshToken:
    """サンプルリフレッシュトークン"""
    token = RefreshToken(
        token="sample_refresh_token_12345",
        user_id=sample_user.id,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db_session.add(token)
    await db_session.flush()
    await db_session.refresh(token)
    return token


@pytest_asyncio.fixture
async def sample_blacklist_entry(db_session: AsyncSession) -> TokenBlacklist:
    """サンプルブラックリストエントリ"""
    entry = TokenBlacklist(
        jti="sample_jti_12345",
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    db_session.add(entry)
    await db_session.flush()
    await db_session.refresh(entry)
    return entry


# テストデータ作成用のヘルパー関数
class TestDataFactory:
    """テストデータ作成用ファクトリー"""
    
    @staticmethod
    def create_user_data(**kwargs) -> UserCreate:
        """ユーザー作成データ"""
        defaults = {
            "username": f"user_{uuid4().hex[:8]}",
            "password": "password123",
            "full_name": "Test User",
            "is_admin": False
        }
        defaults.update(kwargs)
        return UserCreate(**defaults)
    
    @staticmethod
    def create_article_data(**kwargs) -> ArticleCreate:
        """記事作成データ"""
        defaults = {
            "article_uuid": str(uuid4()),
            "article_number": f"ART-{uuid4().hex[:6].upper()}",
            "title": "Test Article",
            "content": "Test content"
        }
        defaults.update(kwargs)
        return ArticleCreate(**defaults)
    
    @staticmethod
    def create_knowledge_data(article_number: str = None, **kwargs) -> KnowledgeCreate:
        """ナレッジ作成データ"""
        defaults = {
            "article_number": article_number or f"ART-{uuid4().hex[:6].upper()}",
            "change_type": ChangeTypeEnum.modify,
            "title": "Test Knowledge",
            "info_category": "テスト",
            "keywords": "test",
            "importance": False,
            "target": "開発者",
            "open_publish_start": date.today(),
            "open_publish_end": date.today() + timedelta(days=30),
            "question": "テスト質問",
            "answer": "テスト回答",
            "add_comments": "追加コメント",
            "remarks": "備考"
        }
        defaults.update(kwargs)
        return KnowledgeCreate(**defaults)


@pytest.fixture
def test_data_factory():
    """テストデータファクトリーのフィクスチャ"""
    return TestDataFactory


# 複数のテストデータを作成するヘルパー
@pytest_asyncio.fixture
async def multiple_users(db_session: AsyncSession) -> list[User]:
    """複数のユーザーを作成"""
    users = []
    for i in range(5):
        user = User(
            id=uuid4(),
            username=f"user{i}",
            hashed_password=get_password_hash(f"password{i}"),
            full_name=f"User {i}",
            is_admin=(i == 0)  # 最初のユーザーのみ管理者
        )
        db_session.add(user)
        users.append(user)
    
    await db_session.flush()
    for user in users:
        await db_session.refresh(user)
    
    return users


@pytest_asyncio.fixture
async def multiple_articles(db_session: AsyncSession) -> list[Article]:
    """複数の記事を作成"""
    articles = []
    for i in range(10):
        article = Article(
            article_uuid=str(uuid4()),
            article_number=f"ART-{i:03d}",
            title=f"Article {i}",
            content=f"Content for article {i}",
            is_active=(i % 2 == 0)  # 偶数番号のみアクティブ
        )
        db_session.add(article)
        articles.append(article)
    
    await db_session.flush()
    for article in articles:
        await db_session.refresh(article)
    
    return articles


@pytest_asyncio.fixture
async def multiple_knowledge(db_session: AsyncSession, sample_user: User, multiple_articles: list[Article]) -> list[Knowledge]:
    """複数のナレッジを作成"""
    knowledge_list = []
    statuses = [StatusEnum.draft, StatusEnum.submitted, StatusEnum.approved]
    
    for i, article in enumerate(multiple_articles[:6]):  # 最初の6記事に対してナレッジ作成
        knowledge = Knowledge(
            id=uuid4(),
            article_number=article.article_number,
            change_type=ChangeTypeEnum.modify if i % 2 == 0 else ChangeTypeEnum.delete,
            title=f"テストナレッジ {i}",
            info_category="テスト",
            keywords=f"keyword{i},test",
            importance=(i % 2 == 0),
            target="開発者",
            open_publish_start=date.today() - timedelta(days=i),
            open_publish_end=date.today() + timedelta(days=30 - i),
            question=f"質問 {i}",
            answer=f"回答 {i}",
            status=statuses[i % len(statuses)],
            created_by=sample_user.id
        )
        db_session.add(knowledge)
        knowledge_list.append(knowledge)
    
    await db_session.flush()
    for knowledge in knowledge_list:
        await db_session.refresh(knowledge)
    
    return knowledge_list
