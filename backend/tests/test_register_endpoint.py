"""
ユーザー登録エンドポイントのテスト
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, AsyncMock

from app.main import app
from app.models import User
from app.db.session import get_async_session
from app.core.exceptions import (
    DuplicateUsernameError,
    ValidationError,
    DatabaseConnectionError,
    DatabaseIntegrityError
)


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession):
    """非同期テストクライアント"""
    # データベースセッションをオーバーライド
    async def override_get_async_session():
        yield db_session
    
    app.dependency_overrides[get_async_session] = override_get_async_session
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    # オーバーライドをクリア
    app.dependency_overrides.clear()


class TestRegisterEndpoint:
    """ユーザー登録エンドポイントのテスト"""

    async def test_register_success(self, async_client: AsyncClient, db_session: AsyncSession):
        """正常なユーザー登録"""
        user_data = {
            "username": "newuser",
            "full_name": "New User",
            "password": "password123"
        }
        
        response = await async_client.post(
            "/api/v1/auth/register",
            json=user_data
        )
        
        assert response.status_code == 201
        result = response.json()
        assert result["username"] == "newuser"
        assert result["full_name"] == "New User"
        assert result["is_admin"] == False
        assert "id" in result
        assert "hashed_password" not in result

    async def test_register_duplicate_username(
        self, 
        async_client: AsyncClient, 
        sample_user: User
    ):
        """重複するユーザー名での登録（409エラー）"""
        user_data = {
            "username": sample_user.username,  # 既存のユーザー名
            "full_name": "Duplicate User",
            "password": "password123"
        }
        
        response = await async_client.post(
            "/api/v1/auth/register",
            json=user_data
        )
        
        assert response.status_code == 409
        assert f"ユーザー名 '{sample_user.username}' は既に使用されています" in response.json()["detail"]

    async def test_register_short_password(self, async_client: AsyncClient):
        """短いパスワードでの登録（400エラー）"""
        user_data = {
            "username": "shortpass",
            "full_name": "Short Password User",
            "password": "short"  # 8文字未満
        }
        
        response = await async_client.post(
            "/api/v1/auth/register",
            json=user_data
        )
        
        assert response.status_code == 400
        assert "パスワードは8文字以上である必要があります" in response.json()["detail"]

    async def test_register_empty_username(self, async_client: AsyncClient):
        """空のユーザー名での登録（422エラー）"""
        user_data = {
            "username": "",
            "full_name": "Empty Username",
            "password": "password123"
        }
        
        response = await async_client.post(
            "/api/v1/auth/register",
            json=user_data
        )
        
        # FastAPIのバリデーションエラー
        assert response.status_code == 422

    async def test_register_missing_fields(self, async_client: AsyncClient):
        """必須フィールドが不足している場合（422エラー）"""
        user_data = {
            "username": "incomplete"
            # full_nameとpasswordが不足
        }
        
        response = await async_client.post(
            "/api/v1/auth/register",
            json=user_data
        )
        
        assert response.status_code == 422
        errors = response.json()["detail"]
        assert len(errors) >= 2  # 少なくとも2つのフィールドエラー

    async def test_register_with_admin_field(self, async_client: AsyncClient):
        """is_adminフィールドを含めた登録（無視される）"""
        user_data = {
            "username": "tryingadmin",
            "full_name": "Trying Admin",
            "password": "password123",
            "is_admin": True  # このフィールドは無視される
        }
        
        response = await async_client.post(
            "/api/v1/auth/register",
            json=user_data
        )
        
        assert response.status_code == 201
        result = response.json()
        assert result["is_admin"] == False  # 常にFalse

    async def test_register_special_characters_username(self, async_client: AsyncClient):
        """特殊文字を含むユーザー名での登録"""
        user_data = {
            "username": "user@123",
            "full_name": "Special User",
            "password": "password123"
        }
        
        response = await async_client.post(
            "/api/v1/auth/register",
            json=user_data
        )
        
        assert response.status_code == 201
        result = response.json()
        assert result["username"] == "user@123"

    async def test_register_long_username(self, async_client: AsyncClient):
        """長いユーザー名での登録"""
        user_data = {
            "username": "a" * 100,  # 100文字
            "full_name": "Long Username User",
            "password": "password123"
        }
        
        response = await async_client.post(
            "/api/v1/auth/register",
            json=user_data
        )
        
        # データベースの制限による
        assert response.status_code in [201, 400, 422]

    async def test_register_unicode_full_name(self, async_client: AsyncClient):
        """Unicode文字を含むフルネームでの登録"""
        user_data = {
            "username": "unicodeuser",
            "full_name": "山田太郎",
            "password": "password123"
        }
        
        response = await async_client.post(
            "/api/v1/auth/register",
            json=user_data
        )
        
        assert response.status_code == 201
        result = response.json()
        assert result["full_name"] == "山田太郎"

    @patch('app.crud.user.user_crud.create')
    async def test_register_database_connection_error(
        self,
        mock_create,
        async_client: AsyncClient
    ):
        """データベース接続エラー（503エラー）"""
        mock_create.side_effect = DatabaseConnectionError("データベースセッションがアクティブではありません")
        
        user_data = {
            "username": "dbconnectionerror",
            "full_name": "DB Connection Error",
            "password": "password123"
        }
        
        response = await async_client.post(
            "/api/v1/auth/register",
            json=user_data
        )
        
        assert response.status_code == 503
        assert "データベースサービスが利用できません" in response.json()["detail"]

    @patch('app.crud.user.user_crud.create')
    async def test_register_database_integrity_error(
        self,
        mock_create,
        async_client: AsyncClient
    ):
        """データベース整合性エラー（400エラー）"""
        mock_create.side_effect = DatabaseIntegrityError("整合性制約違反")
        
        user_data = {
            "username": "integrityerror",
            "full_name": "Integrity Error",
            "password": "password123"
        }
        
        response = await async_client.post(
            "/api/v1/auth/register",
            json=user_data
        )
        
        assert response.status_code == 400
        assert "データの整合性に問題があります" in response.json()["detail"]

    @patch('app.crud.user.user_crud.create')
    async def test_register_validation_error(
        self,
        mock_create,
        async_client: AsyncClient
    ):
        """バリデーションエラー（400エラー）"""
        mock_create.side_effect = ValidationError("カスタムバリデーションエラー")
        
        user_data = {
            "username": "validationerror",
            "full_name": "Validation Error",
            "password": "password123"
        }
        
        response = await async_client.post(
            "/api/v1/auth/register",
            json=user_data
        )
        
        assert response.status_code == 400
        assert "カスタムバリデーションエラー" in response.json()["detail"]

    @patch('app.crud.user.user_crud.create')
    async def test_register_unexpected_error(
        self,
        mock_create,
        async_client: AsyncClient
    ):
        """予期しないエラー（500エラー）"""
        mock_create.side_effect = Exception("予期しないエラー")
        
        user_data = {
            "username": "unexpectederror",
            "full_name": "Unexpected Error",
            "password": "password123"
        }
        
        response = await async_client.post(
            "/api/v1/auth/register",
            json=user_data
        )
        
        assert response.status_code == 500
        assert "ユーザー登録中にエラーが発生しました" in response.json()["detail"]

    async def test_register_null_values(self, async_client: AsyncClient):
        """null値での登録（422エラー）"""
        user_data = {
            "username": None,
            "full_name": None,
            "password": None
        }
        
        response = await async_client.post(
            "/api/v1/auth/register",
            json=user_data
        )
        
        assert response.status_code == 422

    async def test_register_empty_json(self, async_client: AsyncClient):
        """空のJSONでの登録（422エラー）"""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={}
        )
        
        assert response.status_code == 422

    async def test_register_invalid_json(self, async_client: AsyncClient):
        """無効なJSONでの登録（422エラー）"""
        response = await async_client.post(
            "/api/v1/auth/register",
            content='{"invalid json}'
        )
        
        assert response.status_code == 422

    async def test_register_case_sensitive_username(
        self, 
        async_client: AsyncClient,
        db_session: AsyncSession
    ):
        """大文字小文字を区別するユーザー名"""
        # 小文字で登録
        user_data1 = {
            "username": "testuser",
            "full_name": "Test User 1",
            "password": "password123"
        }
        
        response1 = await async_client.post(
            "/api/v1/auth/register",
            json=user_data1
        )
        
        assert response1.status_code == 201
        
        # 大文字で登録（別ユーザーとして扱われる）
        user_data2 = {
            "username": "TESTUSER",
            "full_name": "Test User 2",
            "password": "password123"
        }
        
        response2 = await async_client.post(
            "/api/v1/auth/register",
            json=user_data2
        )
        
        # データベースの設定による（大文字小文字を区別する場合は201、しない場合は409）
        assert response2.status_code in [201, 409]

    async def test_register_whitespace_handling(self, async_client: AsyncClient):
        """空白文字の処理"""
        user_data = {
            "username": "  spaceuser  ",  # 前後に空白
            "full_name": "  Space User  ",
            "password": "password123"
        }
        
        response = await async_client.post(
            "/api/v1/auth/register",
            json=user_data
        )
        
        # 実装による（空白をトリムする場合は201、しない場合も201）
        assert response.status_code == 201
        if response.status_code == 201:
            result = response.json()
            # ユーザー名は保存時にトリムされる可能性がある
            assert result["username"] in ["spaceuser", "  spaceuser  "]


class TestRegisterEndpointIntegration:
    """登録エンドポイントの統合テスト"""

    async def test_register_then_login(
        self, 
        async_client: AsyncClient,
        db_session: AsyncSession
    ):
        """登録後すぐにログイン"""
        # ユーザー登録
        user_data = {
            "username": "newloginuser",
            "full_name": "New Login User",
            "password": "password123"
        }
        
        register_response = await async_client.post(
            "/api/v1/auth/register",
            json=user_data
        )
        
        assert register_response.status_code == 201
        
        # 登録したユーザーでログイン
        login_data = {
            "username": "newloginuser",
            "password": "password123"
        }
        
        login_response = await async_client.post(
            "/api/v1/auth/login",
            data=login_data
        )
        
        assert login_response.status_code == 200
        tokens = login_response.json()
        assert "access_token" in tokens
        assert "refresh_token" in tokens

    async def test_register_multiple_users_sequentially(
        self, 
        async_client: AsyncClient,
        db_session: AsyncSession
    ):
        """複数ユーザーの連続登録"""
        users = [
            {
                "username": f"sequser{i}",
                "full_name": f"Sequential User {i}",
                "password": "password123"
            }
            for i in range(5)
        ]
        
        for user_data in users:
            response = await async_client.post(
                "/api/v1/auth/register",
                json=user_data
            )
            assert response.status_code == 201
            result = response.json()
            assert result["username"] == user_data["username"]

    async def test_register_same_username_after_failed_attempt(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession
    ):
        """失敗した登録試行後の同じユーザー名での再試行"""
        # 最初の試行（パスワードが短い）
        user_data1 = {
            "username": "retryuser",
            "full_name": "Retry User",
            "password": "short"  # 短すぎる
        }
        
        response1 = await async_client.post(
            "/api/v1/auth/register",
            json=user_data1
        )
        
        assert response1.status_code == 400
        
        # 同じユーザー名で正しいパスワードで再試行
        user_data2 = {
            "username": "retryuser",
            "full_name": "Retry User",
            "password": "password123"
        }
        
        response2 = await async_client.post(
            "/api/v1/auth/register",
            json=user_data2
        )
        
        assert response2.status_code == 201
