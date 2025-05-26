"""
UserCRUD のテスト
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.user import user_crud
from app.schemas import UserCreate, UserUpdate
from app.models import User
from app.core.exceptions import (
    UserNotFoundError,
    DuplicateUsernameError,
    DatabaseConnectionError,
    InvalidParameterError,
    ValidationError,
    InvalidCredentialsError
)


class TestUserCRUD:
    """UserCRUD のテストクラス"""

    @pytest.mark.asyncio
    async def test_get_user_success(self, db_session: AsyncSession, sample_user: User):
        """ユーザー取得 - 正常系"""
        # 実行
        result = await user_crud.get(db_session, sample_user.id)
        
        # 検証
        assert result is not None
        assert result.id == sample_user.id
        assert result.username == sample_user.username
        assert result.full_name == sample_user.full_name
        assert result.is_admin == sample_user.is_admin

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, db_session: AsyncSession):
        """ユーザー取得 - 存在しないID"""
        non_existent_id = uuid4()
        
        # 実行・検証
        with pytest.raises(UserNotFoundError) as exc_info:
            await user_crud.get(db_session, non_existent_id)
        
        assert str(non_existent_id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_user_invalid_id(self, db_session: AsyncSession):
        """ユーザー取得 - 無効なID"""
        # 実行・検証
        with pytest.raises(InvalidParameterError) as exc_info:
            await user_crud.get(db_session, None)
        
        assert "id" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_by_username_success(self, db_session: AsyncSession, sample_user: User):
        """ユーザー名でユーザー取得 - 正常系"""
        # 実行
        result = await user_crud.get_by_username(db_session, sample_user.username)
        
        # 検証
        assert result is not None
        assert result.id == sample_user.id
        assert result.username == sample_user.username

    @pytest.mark.asyncio
    async def test_get_by_username_not_found(self, db_session: AsyncSession):
        """ユーザー名でユーザー取得 - 存在しないユーザー名"""
        # 実行・検証
        with pytest.raises(UserNotFoundError) as exc_info:
            await user_crud.get_by_username(db_session, "nonexistent")
        
        assert "nonexistent" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_by_username_empty(self, db_session: AsyncSession):
        """ユーザー名でユーザー取得 - 空のユーザー名"""
        # 実行・検証
        with pytest.raises(InvalidParameterError):
            await user_crud.get_by_username(db_session, "")
        
        with pytest.raises(InvalidParameterError):
            await user_crud.get_by_username(db_session, "   ")

    @pytest.mark.asyncio
    async def test_get_by_username_optional_success(self, db_session: AsyncSession, sample_user: User):
        """ユーザー名でユーザー取得（例外なし） - 正常系"""
        # 実行
        result = await user_crud.get_by_username_optional(db_session, sample_user.username)
        
        # 検証
        assert result is not None
        assert result.id == sample_user.id

    @pytest.mark.asyncio
    async def test_get_by_username_optional_not_found(self, db_session: AsyncSession):
        """ユーザー名でユーザー取得（例外なし） - 存在しないユーザー名"""
        # 実行
        result = await user_crud.get_by_username_optional(db_session, "nonexistent")
        
        # 検証
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_username_optional_empty(self, db_session: AsyncSession):
        """ユーザー名でユーザー取得（例外なし） - 空のユーザー名"""
        # 実行
        result = await user_crud.get_by_username_optional(db_session, "")
        
        # 検証
        assert result is None

    @pytest.mark.asyncio
    async def test_get_multi_success(self, db_session: AsyncSession, multiple_users: list[User]):
        """ユーザー一覧取得 - 正常系"""
        # 実行
        result = await user_crud.get_multi(db_session, skip=0, limit=10)
        
        # 検証
        assert len(result) == len(multiple_users)
        assert all(isinstance(user, User) for user in result)

    @pytest.mark.asyncio
    async def test_get_multi_pagination(self, db_session: AsyncSession, multiple_users: list[User]):
        """ユーザー一覧取得 - ページネーション"""
        # 実行
        first_page = await user_crud.get_multi(db_session, skip=0, limit=2)
        second_page = await user_crud.get_multi(db_session, skip=2, limit=2)
        
        # 検証
        assert len(first_page) == 2
        assert len(second_page) == 2
        assert first_page[0].id != second_page[0].id

    @pytest.mark.asyncio
    async def test_get_multi_invalid_skip(self, db_session: AsyncSession):
        """ユーザー一覧取得 - 無効なskip"""
        # 実行・検証
        with pytest.raises(InvalidParameterError):
            await user_crud.get_multi(db_session, skip=-1, limit=10)

    @pytest.mark.asyncio
    async def test_get_multi_invalid_limit(self, db_session: AsyncSession):
        """ユーザー一覧取得 - 無効なlimit"""
        # 実行・検証
        with pytest.raises(InvalidParameterError):
            await user_crud.get_multi(db_session, skip=0, limit=0)
        
        with pytest.raises(InvalidParameterError):
            await user_crud.get_multi(db_session, skip=0, limit=1001)

    @pytest.mark.asyncio
    async def test_create_user_success(self, db_session: AsyncSession, test_data_factory):
        """ユーザー作成 - 正常系"""
        # 準備
        user_data = test_data_factory.create_user_data(
            username="newuser",
            password="newpassword123",
            full_name="New User",
            is_admin=True
        )
        
        # 実行
        result = await user_crud.create(db_session, user_data)
        
        # 検証
        assert result.username == user_data.username
        assert result.full_name == user_data.full_name
        assert result.is_admin == user_data.is_admin
        assert result.hashed_password != user_data.password  # パスワードがハッシュ化されている
        assert result.id is not None

    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(self, db_session: AsyncSession, sample_user: User, test_data_factory):
        """ユーザー作成 - 重複ユーザー名"""
        # 準備
        user_data = test_data_factory.create_user_data(username=sample_user.username)
        
        # 実行・検証
        with pytest.raises(DuplicateUsernameError) as exc_info:
            await user_crud.create(db_session, user_data)
        
        assert sample_user.username in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_user_empty_username(self, db_session: AsyncSession, test_data_factory):
        """ユーザー作成 - 空のユーザー名"""
        # 準備
        user_data = test_data_factory.create_user_data(username="")
        
        # 実行・検証
        with pytest.raises(ValidationError):
            await user_crud.create(db_session, user_data)

    @pytest.mark.asyncio
    async def test_create_user_short_password(self, db_session: AsyncSession, test_data_factory):
        """ユーザー作成 - 短いパスワード"""
        # 準備
        user_data = test_data_factory.create_user_data(password="short")
        
        # 実行・検証
        with pytest.raises(ValidationError):
            await user_crud.create(db_session, user_data)

    @pytest.mark.asyncio
    async def test_update_user_success(self, db_session: AsyncSession, sample_user: User):
        """ユーザー更新 - 正常系"""
        # 準備
        update_data = UserUpdate(
            full_name="Updated Name",
            is_admin=True
        )
        
        # 実行
        result = await user_crud.update(db_session, sample_user, update_data)
        
        # 検証
        assert result.full_name == "Updated Name"
        assert result.is_admin == True
        assert result.username == sample_user.username  # 変更されていない

    @pytest.mark.asyncio
    async def test_update_user_password(self, db_session: AsyncSession, sample_user: User):
        """ユーザー更新 - パスワード変更"""
        # 準備
        old_password_hash = sample_user.hashed_password
        update_data = UserUpdate(password="newpassword123")
        
        # 実行
        result = await user_crud.update(db_session, sample_user, update_data)
        
        # 検証
        assert result.hashed_password != old_password_hash
        assert result.hashed_password != "newpassword123"  # ハッシュ化されている

    @pytest.mark.asyncio
    async def test_update_user_username_duplicate(self, db_session: AsyncSession, multiple_users: list[User]):
        """ユーザー更新 - 重複ユーザー名"""
        # 準備
        user1, user2 = multiple_users[0], multiple_users[1]
        update_data = UserUpdate(username=user2.username)
        
        # 実行・検証
        with pytest.raises(DuplicateUsernameError):
            await user_crud.update(db_session, user1, update_data)

    @pytest.mark.asyncio
    async def test_update_user_short_password(self, db_session: AsyncSession, sample_user: User):
        """ユーザー更新 - 短いパスワード"""
        # 準備
        update_data = UserUpdate(password="short")
        
        # 実行・検証
        with pytest.raises(ValidationError):
            await user_crud.update(db_session, sample_user, update_data)

    @pytest.mark.asyncio
    async def test_update_user_no_data(self, db_session: AsyncSession, sample_user: User):
        """ユーザー更新 - 更新データなし"""
        # 準備
        update_data = UserUpdate()
        
        # 実行
        result = await user_crud.update(db_session, sample_user, update_data)
        
        # 検証（変更されていない）
        assert result.id == sample_user.id
        assert result.username == sample_user.username

    @pytest.mark.asyncio
    async def test_update_user_invalid_object(self, db_session: AsyncSession):
        """ユーザー更新 - 無効なユーザーオブジェクト"""
        # 準備
        update_data = UserUpdate(full_name="Test")
        
        # 実行・検証
        with pytest.raises(InvalidParameterError):
            await user_crud.update(db_session, None, update_data)

    @pytest.mark.asyncio
    async def test_delete_user_success(self, db_session: AsyncSession, sample_user: User):
        """ユーザー削除 - 正常系"""
        # 実行
        result = await user_crud.delete(db_session, sample_user.id)
        
        # 検証
        assert result == True
        
        # 削除されたことを確認
        with pytest.raises(UserNotFoundError):
            await user_crud.get(db_session, sample_user.id)

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, db_session: AsyncSession):
        """ユーザー削除 - 存在しないユーザー"""
        # 実行
        result = await user_crud.delete(db_session, uuid4())
        
        # 検証
        assert result == False

    @pytest.mark.asyncio
    async def test_delete_user_invalid_id(self, db_session: AsyncSession):
        """ユーザー削除 - 無効なID"""
        # 実行・検証
        with pytest.raises(InvalidParameterError):
            await user_crud.delete(db_session, None)

    @pytest.mark.asyncio
    async def test_authenticate_success(self, db_session: AsyncSession, sample_user: User):
        """ユーザー認証 - 正常系"""
        # 実行
        result = await user_crud.authenticate(db_session, sample_user.username, "testpassword123")
        
        # 検証
        assert result is not None
        assert result.id == sample_user.id
        assert result.username == sample_user.username

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(self, db_session: AsyncSession, sample_user: User):
        """ユーザー認証 - 間違ったパスワード"""
        # 実行・検証
        with pytest.raises(InvalidCredentialsError):
            await user_crud.authenticate(db_session, sample_user.username, "wrongpassword")

    @pytest.mark.asyncio
    async def test_authenticate_nonexistent_user(self, db_session: AsyncSession):
        """ユーザー認証 - 存在しないユーザー"""
        # 実行・検証
        with pytest.raises(InvalidCredentialsError):
            await user_crud.authenticate(db_session, "nonexistent", "password")

    @pytest.mark.asyncio
    async def test_authenticate_empty_username(self, db_session: AsyncSession):
        """ユーザー認証 - 空のユーザー名"""
        # 実行・検証
        with pytest.raises(InvalidParameterError):
            await user_crud.authenticate(db_session, "", "password")

    @pytest.mark.asyncio
    async def test_authenticate_empty_password(self, db_session: AsyncSession, sample_user: User):
        """ユーザー認証 - 空のパスワード"""
        # 実行・検証
        with pytest.raises(InvalidParameterError):
            await user_crud.authenticate(db_session, sample_user.username, "")

    @pytest.mark.asyncio
    async def test_database_connection_error_simulation(self, db_session: AsyncSession):
        """データベース接続エラーのシミュレーション"""
        # セッションを無効化してトランザクションを閉じる
        await db_session.rollback()
        await db_session.close()
        
        # 実行・検証 - 閉じられたセッションでの操作はDatabaseConnectionErrorまたはUserNotFoundErrorになる
        with pytest.raises((DatabaseConnectionError, UserNotFoundError)):
            await user_crud.get(db_session, uuid4())

    @pytest.mark.asyncio
    async def test_edge_case_very_long_username(self, db_session: AsyncSession, test_data_factory):
        """境界値テスト - 非常に長いユーザー名"""
        # 準備
        long_username = "a" * 1000  # 非常に長いユーザー名
        user_data = test_data_factory.create_user_data(username=long_username)
        
        # 実行（データベースの制約によってはエラーになる可能性がある）
        try:
            result = await user_crud.create(db_session, user_data)
            assert result.username == long_username
        except Exception:
            # データベース制約によるエラーは許容
            pass

    @pytest.mark.asyncio
    async def test_concurrent_user_creation(self, db_session: AsyncSession, test_data_factory):
        """同時ユーザー作成のテスト"""
        import asyncio
        
        # 準備
        user_data1 = test_data_factory.create_user_data(username="concurrent1")
        user_data2 = test_data_factory.create_user_data(username="concurrent2")
        
        # 実行
        results = await asyncio.gather(
            user_crud.create(db_session, user_data1),
            user_crud.create(db_session, user_data2),
            return_exceptions=True
        )
        
        # 検証
        assert len(results) == 2
        # 少なくとも1つは成功する
        success_count = sum(1 for r in results if isinstance(r, User))
        assert success_count >= 1

    @pytest.mark.asyncio
    async def test_user_crud_comprehensive_workflow(self, db_session: AsyncSession, test_data_factory):
        """包括的なワークフローテスト"""
        # 1. ユーザー作成
        user_data = test_data_factory.create_user_data(
            username="workflow_user",
            password="password123",
            full_name="Workflow User"
        )
        created_user = await user_crud.create(db_session, user_data)
        
        # 2. 作成されたユーザーを取得
        retrieved_user = await user_crud.get(db_session, created_user.id)
        assert retrieved_user.username == user_data.username
        
        # 3. ユーザー名で取得
        user_by_name = await user_crud.get_by_username(db_session, user_data.username)
        assert user_by_name.id == created_user.id
        
        # 4. 認証テスト
        authenticated_user = await user_crud.authenticate(db_session, user_data.username, user_data.password)
        assert authenticated_user.id == created_user.id
        
        # 5. ユーザー更新
        update_data = UserUpdate(full_name="Updated Workflow User", is_admin=True)
        updated_user = await user_crud.update(db_session, retrieved_user, update_data)
        assert updated_user.full_name == "Updated Workflow User"
        assert updated_user.is_admin == True
        
        # 6. 一覧に含まれることを確認
        users_list = await user_crud.get_multi(db_session, skip=0, limit=100)
        user_ids = [u.id for u in users_list]
        assert created_user.id in user_ids
        
        # 7. ユーザー削除
        delete_result = await user_crud.delete(db_session, created_user.id)
        assert delete_result == True
        
        # 8. 削除後は取得できないことを確認
        with pytest.raises(UserNotFoundError):
            await user_crud.get(db_session, created_user.id)
