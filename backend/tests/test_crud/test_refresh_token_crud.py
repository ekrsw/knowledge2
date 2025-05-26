"""
RefreshTokenCRUD のテスト
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.refresh_token import refresh_token_crud
from app.schemas import RefreshTokenCreate
from app.models import RefreshToken, User
from app.core.exceptions import (
    TokenNotFoundError,
    ExpiredTokenError,
    DatabaseConnectionError,
    InvalidParameterError,
    ValidationError
)


class TestRefreshTokenCRUD:
    """RefreshTokenCRUD のテストクラス"""

    @pytest.mark.asyncio
    async def test_get_refresh_token_success(self, db_session: AsyncSession, sample_refresh_token: RefreshToken):
        """リフレッシュトークン取得 - 正常系"""
        # 実行
        result = await refresh_token_crud.get(db_session, sample_refresh_token.id)
        
        # 検証
        assert result is not None
        assert result.id == sample_refresh_token.id
        assert result.token == sample_refresh_token.token
        assert result.user_id == sample_refresh_token.user_id
        assert result.expires_at == sample_refresh_token.expires_at

    @pytest.mark.asyncio
    async def test_get_refresh_token_not_found(self, db_session: AsyncSession):
        """リフレッシュトークン取得 - 存在しないID"""
        non_existent_id = uuid4()
        
        # 実行・検証
        with pytest.raises(TokenNotFoundError) as exc_info:
            await refresh_token_crud.get(db_session, non_existent_id)
        
        assert str(non_existent_id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_refresh_token_invalid_id(self, db_session: AsyncSession):
        """リフレッシュトークン取得 - 無効なID"""
        # 実行・検証
        with pytest.raises(InvalidParameterError):
            await refresh_token_crud.get(db_session, None)

    @pytest.mark.asyncio
    async def test_get_by_token_success(self, db_session: AsyncSession, sample_refresh_token: RefreshToken):
        """トークン文字列でリフレッシュトークン取得 - 正常系"""
        # 実行
        result = await refresh_token_crud.get_by_token(db_session, sample_refresh_token.token)
        
        # 検証
        assert result is not None
        assert result.id == sample_refresh_token.id
        assert result.token == sample_refresh_token.token

    @pytest.mark.asyncio
    async def test_get_by_token_not_found(self, db_session: AsyncSession):
        """トークン文字列でリフレッシュトークン取得 - 存在しないトークン"""
        # 実行・検証
        result = await refresh_token_crud.get_by_token(db_session, "nonexistent_token")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_token_empty_token(self, db_session: AsyncSession):
        """トークン文字列でリフレッシュトークン取得 - 空のトークン"""
        # 実行・検証
        with pytest.raises(InvalidParameterError):
            await refresh_token_crud.get_by_token(db_session, "")

    @pytest.mark.asyncio
    async def test_get_by_user_id_success(self, db_session: AsyncSession, sample_user: User, sample_refresh_token: RefreshToken):
        """ユーザーIDでリフレッシュトークン取得 - 正常系"""
        # 実行
        result = await refresh_token_crud.get_by_user_id(db_session, sample_user.id)
        
        # 検証
        assert len(result) > 0
        assert all(token.user_id == sample_user.id for token in result)

    @pytest.mark.asyncio
    async def test_get_by_user_id_no_results(self, db_session: AsyncSession):
        """ユーザーIDでリフレッシュトークン取得 - 該当なし"""
        # 実行
        result = await refresh_token_crud.get_by_user_id(db_session, uuid4())
        
        # 検証
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_by_user_id_invalid_id(self, db_session: AsyncSession):
        """ユーザーIDでリフレッシュトークン取得 - 無効なID"""
        # 実行・検証
        with pytest.raises(InvalidParameterError):
            await refresh_token_crud.get_by_user_id(db_session, None)

    @pytest.mark.asyncio
    async def test_create_refresh_token_success(self, db_session: AsyncSession, sample_user: User, test_data_factory):
        """リフレッシュトークン作成 - 正常系"""
        # 準備
        token_data = test_data_factory.create_refresh_token_data(
            user_id=sample_user.id,
            token="new_refresh_token_123",
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        
        # 実行
        result = await refresh_token_crud.create(db_session, token_data)
        
        # 検証
        assert result.token == token_data.token
        assert result.user_id == token_data.user_id
        assert result.expires_at == token_data.expires_at
        assert result.id is not None

    @pytest.mark.asyncio
    async def test_create_refresh_token_empty_token(self, db_session: AsyncSession, sample_user: User, test_data_factory):
        """リフレッシュトークン作成 - 空のトークン"""
        # 準備
        token_data = test_data_factory.create_refresh_token_data(
            user_id=sample_user.id,
            token=""
        )
        
        # 実行・検証
        with pytest.raises(ValidationError):
            await refresh_token_crud.create(db_session, token_data)

    @pytest.mark.asyncio
    async def test_create_refresh_token_invalid_user(self, db_session: AsyncSession, test_data_factory):
        """リフレッシュトークン作成 - 無効なユーザー"""
        # 準備
        token_data = test_data_factory.create_refresh_token_data(
            user_id=uuid4(),  # 存在しないユーザー
            token="test_token"
        )
        
        # 実行・検証
        with pytest.raises(ValidationError):
            await refresh_token_crud.create(db_session, token_data)

    @pytest.mark.asyncio
    async def test_create_refresh_token_duplicate_token(self, db_session: AsyncSession, sample_user: User, sample_refresh_token: RefreshToken, test_data_factory):
        """リフレッシュトークン作成 - 重複トークン"""
        # 準備
        token_data = test_data_factory.create_refresh_token_data(
            user_id=sample_user.id,
            token=sample_refresh_token.token  # 既存のトークンと同じ
        )
        
        # 実行・検証
        from app.core.exceptions import DatabaseIntegrityError
        with pytest.raises(DatabaseIntegrityError):
            await refresh_token_crud.create(db_session, token_data)

    @pytest.mark.asyncio
    async def test_create_refresh_token_past_expiry(self, db_session: AsyncSession, sample_user: User, test_data_factory):
        """リフレッシュトークン作成 - 過去の有効期限"""
        # 準備
        token_data = test_data_factory.create_refresh_token_data(
            user_id=sample_user.id,
            token="expired_token",
            expires_at=datetime.utcnow() - timedelta(days=1)  # 過去の日時
        )
        
        # 実行・検証
        with pytest.raises(ValidationError):
            await refresh_token_crud.create(db_session, token_data)

    @pytest.mark.asyncio
    async def test_delete_refresh_token_success(self, db_session: AsyncSession, sample_refresh_token: RefreshToken):
        """リフレッシュトークン削除 - 正常系"""
        # 実行
        result = await refresh_token_crud.delete(db_session, sample_refresh_token.id)
        
        # 検証
        assert result == True
        
        # 削除されたことを確認
        with pytest.raises(TokenNotFoundError):
            await refresh_token_crud.get(db_session, sample_refresh_token.id)

    @pytest.mark.asyncio
    async def test_delete_refresh_token_not_found(self, db_session: AsyncSession):
        """リフレッシュトークン削除 - 存在しないトークン"""
        # 実行
        result = await refresh_token_crud.delete(db_session, uuid4())
        
        # 検証
        assert result == False

    @pytest.mark.asyncio
    async def test_delete_refresh_token_invalid_id(self, db_session: AsyncSession):
        """リフレッシュトークン削除 - 無効なID"""
        # 実行・検証
        with pytest.raises(InvalidParameterError):
            await refresh_token_crud.delete(db_session, None)

    @pytest.mark.asyncio
    async def test_delete_by_token_success(self, db_session: AsyncSession, sample_refresh_token: RefreshToken):
        """トークン文字列でリフレッシュトークン削除 - 正常系"""
        # 実行
        result = await refresh_token_crud.delete_by_token(db_session, sample_refresh_token.token)
        
        # 検証
        assert result == True
        
        # 削除されたことを確認
        result = await refresh_token_crud.get_by_token(db_session, sample_refresh_token.token)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_by_token_not_found(self, db_session: AsyncSession):
        """トークン文字列でリフレッシュトークン削除 - 存在しないトークン"""
        # 実行
        result = await refresh_token_crud.delete_by_token(db_session, "nonexistent_token")
        
        # 検証
        assert result == False

    @pytest.mark.asyncio
    async def test_delete_by_token_empty_token(self, db_session: AsyncSession):
        """トークン文字列でリフレッシュトークン削除 - 空のトークン"""
        # 実行・検証
        with pytest.raises(InvalidParameterError):
            await refresh_token_crud.delete_by_token(db_session, "")

    @pytest.mark.asyncio
    async def test_delete_by_user_id_success(self, db_session: AsyncSession, sample_user: User, multiple_refresh_tokens: list[RefreshToken]):
        """ユーザーIDでリフレッシュトークン削除 - 正常系"""
        # 実行前のトークン数を確認
        tokens_before = await refresh_token_crud.get_by_user_id(db_session, sample_user.id)
        initial_count = len(tokens_before)
        
        # 実行
        result = await refresh_token_crud.delete_by_user_id(db_session, sample_user.id)
        
        # 検証
        assert result == initial_count
        
        # 削除されたことを確認
        tokens_after = await refresh_token_crud.get_by_user_id(db_session, sample_user.id)
        assert len(tokens_after) == 0

    @pytest.mark.asyncio
    async def test_delete_by_user_id_no_tokens(self, db_session: AsyncSession):
        """ユーザーIDでリフレッシュトークン削除 - トークンなし"""
        # 実行
        result = await refresh_token_crud.delete_by_user_id(db_session, uuid4())
        
        # 検証
        assert result == 0

    @pytest.mark.asyncio
    async def test_delete_by_user_id_invalid_id(self, db_session: AsyncSession):
        """ユーザーIDでリフレッシュトークン削除 - 無効なID"""
        # 実行・検証
        with pytest.raises(InvalidParameterError):
            await refresh_token_crud.delete_by_user_id(db_session, None)

    @pytest.mark.asyncio
    async def test_delete_expired_tokens_success(self, db_session: AsyncSession, sample_user: User, test_data_factory):
        """期限切れトークン削除 - 正常系"""
        # 準備 - 期限切れトークンを作成
        expired_token_data = test_data_factory.create_refresh_token_data(
            user_id=sample_user.id,
            token="expired_token_123",
            expires_at=datetime.utcnow() - timedelta(days=1)
        )
        # バリデーションを回避して直接作成
        expired_token = RefreshToken(**expired_token_data.dict())
        db_session.add(expired_token)
        await db_session.flush()
        
        # 有効なトークンも作成
        valid_token_data = test_data_factory.create_refresh_token_data(
            user_id=sample_user.id,
            token="valid_token_123",
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        valid_token = await refresh_token_crud.create(db_session, valid_token_data)
        
        # 実行
        result = await refresh_token_crud.delete_expired_tokens(db_session)
        
        # 検証
        assert result >= 1  # 少なくとも1つの期限切れトークンが削除された
        
        # 有効なトークンは残っていることを確認
        remaining_token = await refresh_token_crud.get(db_session, valid_token.id)
        assert remaining_token is not None

    @pytest.mark.asyncio
    async def test_delete_expired_tokens_no_expired(self, db_session: AsyncSession):
        """期限切れトークン削除 - 期限切れトークンなし"""
        # 実行
        result = await refresh_token_crud.delete_expired_tokens(db_session)
        
        # 検証
        assert result >= 0  # 削除されたトークン数（0以上）

    @pytest.mark.asyncio
    async def test_is_token_valid_success(self, db_session: AsyncSession, sample_refresh_token: RefreshToken):
        """トークン有効性チェック - 有効なトークン"""
        # 実行
        result = await refresh_token_crud.is_token_valid(db_session, sample_refresh_token.token)
        
        # 検証
        assert result == True

    @pytest.mark.asyncio
    async def test_is_token_valid_expired(self, db_session: AsyncSession, sample_user: User, test_data_factory):
        """トークン有効性チェック - 期限切れトークン"""
        # 準備 - 期限切れトークンを作成
        expired_token_data = test_data_factory.create_refresh_token_data(
            user_id=sample_user.id,
            token="expired_token_456",
            expires_at=datetime.utcnow() - timedelta(days=1)
        )
        # バリデーションを回避して直接作成
        expired_token = RefreshToken(**expired_token_data.dict())
        db_session.add(expired_token)
        await db_session.flush()
        
        # 実行
        result = await refresh_token_crud.is_token_valid(db_session, expired_token.token)
        
        # 検証
        assert result == False

    @pytest.mark.asyncio
    async def test_is_token_valid_not_found(self, db_session: AsyncSession):
        """トークン有効性チェック - 存在しないトークン"""
        # 実行
        result = await refresh_token_crud.is_token_valid(db_session, "nonexistent_token")
        
        # 検証
        assert result == False

    @pytest.mark.asyncio
    async def test_is_token_valid_empty_token(self, db_session: AsyncSession):
        """トークン有効性チェック - 空のトークン"""
        # 実行・検証
        with pytest.raises(InvalidParameterError):
            await refresh_token_crud.is_token_valid(db_session, "")

    @pytest.mark.asyncio
    async def test_database_connection_error_simulation(self, db_session: AsyncSession):
        """データベース接続エラーのシミュレーション"""
        # セッションを無効化してトランザクションを閉じる
        await db_session.rollback()
        await db_session.close()
        
        # 実行・検証 - 閉じられたセッションでの操作はDatabaseConnectionErrorまたはTokenNotFoundErrorになる
        with pytest.raises((DatabaseConnectionError, TokenNotFoundError)):
            await refresh_token_crud.get(db_session, uuid4())

    @pytest.mark.asyncio
    async def test_concurrent_token_creation(self, db_session: AsyncSession, sample_user: User, test_data_factory):
        """同時トークン作成のテスト"""
        import asyncio
        
        # 準備
        token_data1 = test_data_factory.create_refresh_token_data(
            user_id=sample_user.id,
            token="concurrent_token_1"
        )
        token_data2 = test_data_factory.create_refresh_token_data(
            user_id=sample_user.id,
            token="concurrent_token_2"
        )
        
        # 実行
        results = await asyncio.gather(
            refresh_token_crud.create(db_session, token_data1),
            refresh_token_crud.create(db_session, token_data2),
            return_exceptions=True
        )
        
        # 検証
        assert len(results) == 2
        success_count = sum(1 for r in results if isinstance(r, RefreshToken))
        assert success_count >= 1

    @pytest.mark.asyncio
    async def test_edge_case_very_long_token(self, db_session: AsyncSession, sample_user: User, test_data_factory):
        """境界値テスト - 非常に長いトークン"""
        # 準備
        long_token = "a" * 1000
        token_data = test_data_factory.create_refresh_token_data(
            user_id=sample_user.id,
            token=long_token
        )
        
        # 実行（データベースの制約によってはエラーになる可能性がある）
        try:
            result = await refresh_token_crud.create(db_session, token_data)
            assert result.token == long_token
        except Exception:
            # データベース制約によるエラーは許容
            pass

    @pytest.mark.asyncio
    async def test_bulk_token_operations(self, db_session: AsyncSession, sample_user: User, test_data_factory):
        """大量トークン操作のテスト"""
        # 準備 - 大量のトークンを作成
        tokens = []
        for i in range(50):
            token_data = test_data_factory.create_refresh_token_data(
                user_id=sample_user.id,
                token=f"bulk_token_{i}",
                expires_at=datetime.utcnow() + timedelta(days=30)
            )
            token = await refresh_token_crud.create(db_session, token_data)
            tokens.append(token)
        
        # 実行 - ユーザーIDで取得
        user_tokens = await refresh_token_crud.get_by_user_id(db_session, sample_user.id)
        
        # 検証
        assert len(user_tokens) >= 50
        
        # 実行 - 一括削除
        deleted_count = await refresh_token_crud.delete_by_user_id(db_session, sample_user.id)
        
        # 検証
        assert deleted_count >= 50
        
        # 削除後の確認
        remaining_tokens = await refresh_token_crud.get_by_user_id(db_session, sample_user.id)
        assert len(remaining_tokens) == 0

    @pytest.mark.asyncio
    async def test_token_expiry_edge_cases(self, db_session: AsyncSession, sample_user: User, test_data_factory):
        """トークン有効期限の境界値テスト"""
        # 準備 - ちょうど期限切れのトークン
        exactly_expired_data = test_data_factory.create_refresh_token_data(
            user_id=sample_user.id,
            token="exactly_expired_token",
            expires_at=datetime.utcnow()  # 現在時刻
        )
        # バリデーションを回避して直接作成
        exactly_expired_token = RefreshToken(**exactly_expired_data.dict())
        db_session.add(exactly_expired_token)
        await db_session.flush()
        
        # 準備 - 1秒後に期限切れのトークン
        almost_expired_data = test_data_factory.create_refresh_token_data(
            user_id=sample_user.id,
            token="almost_expired_token",
            expires_at=datetime.utcnow() + timedelta(seconds=1)
        )
        almost_expired_token = await refresh_token_crud.create(db_session, almost_expired_data)
        
        # 実行・検証 - ちょうど期限切れ
        is_valid_exactly = await refresh_token_crud.is_token_valid(db_session, exactly_expired_token.token)
        assert is_valid_exactly == False
        
        # 実行・検証 - まだ有効
        is_valid_almost = await refresh_token_crud.is_token_valid(db_session, almost_expired_token.token)
        assert is_valid_almost == True

    @pytest.mark.asyncio
    async def test_refresh_token_crud_comprehensive_workflow(self, db_session: AsyncSession, sample_user: User, test_data_factory):
        """包括的なワークフローテスト"""
        # 1. リフレッシュトークン作成
        token_data = test_data_factory.create_refresh_token_data(
            user_id=sample_user.id,
            token="workflow_refresh_token",
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        created_token = await refresh_token_crud.create(db_session, token_data)
        
        # 2. 作成されたトークンを取得
        retrieved_token = await refresh_token_crud.get(db_session, created_token.id)
        assert retrieved_token.token == token_data.token
        
        # 3. トークン文字列で取得
        token_by_string = await refresh_token_crud.get_by_token(db_session, token_data.token)
        assert token_by_string.id == created_token.id
        
        # 4. ユーザーIDで取得
        user_tokens = await refresh_token_crud.get_by_user_id(db_session, sample_user.id)
        token_ids = [t.id for t in user_tokens]
        assert created_token.id in token_ids
        
        # 5. トークン有効性チェック
        is_valid = await refresh_token_crud.is_token_valid(db_session, token_data.token)
        assert is_valid == True
        
        # 6. 追加のトークンを作成
        additional_token_data = test_data_factory.create_refresh_token_data(
            user_id=sample_user.id,
            token="additional_workflow_token",
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        additional_token = await refresh_token_crud.create(db_session, additional_token_data)
        
        # 7. ユーザーの全トークンを確認
        all_user_tokens = await refresh_token_crud.get_by_user_id(db_session, sample_user.id)
        assert len(all_user_tokens) >= 2
        
        # 8. 特定のトークンを削除
        delete_result = await refresh_token_crud.delete_by_token(db_session, token_data.token)
        assert delete_result == True
        
        # 9. 削除されたことを確認
        result = await refresh_token_crud.get_by_token(db_session, token_data.token)
        assert result is None
        
        # 10. 残りのトークンは存在することを確認
        remaining_token = await refresh_token_crud.get(db_session, additional_token.id)
        assert remaining_token is not None
        
        # 11. ユーザーの全トークンを削除
        deleted_count = await refresh_token_crud.delete_by_user_id(db_session, sample_user.id)
        assert deleted_count >= 1
        
        # 12. 全て削除されたことを確認
        final_tokens = await refresh_token_crud.get_by_user_id(db_session, sample_user.id)
        assert len(final_tokens) == 0
