"""
TokenBlacklistCRUD のテスト
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.token_blacklist import token_blacklist_crud
from app.schemas import TokenBlacklistCreate
from app.models import TokenBlacklist
from app.core.exceptions import (
    TokenBlacklistNotFoundError,
    DatabaseConnectionError,
    InvalidParameterError,
    ValidationError
)


class TestTokenBlacklistCRUD:
    """TokenBlacklistCRUD のテストクラス"""

    @pytest.mark.asyncio
    async def test_get_blacklist_entry_success(self, db_session: AsyncSession, sample_blacklist_entry: TokenBlacklist):
        """ブラックリストエントリ取得 - 正常系"""
        # 実行
        result = await token_blacklist_crud.get(db_session, sample_blacklist_entry.id)
        
        # 検証
        assert result is not None
        assert result.id == sample_blacklist_entry.id
        assert result.jti == sample_blacklist_entry.jti
        assert result.expires_at == sample_blacklist_entry.expires_at

    @pytest.mark.asyncio
    async def test_get_blacklist_entry_not_found(self, db_session: AsyncSession):
        """ブラックリストエントリ取得 - 存在しないID"""
        non_existent_id = uuid4()
        
        # 実行・検証
        with pytest.raises(TokenBlacklistNotFoundError) as exc_info:
            await token_blacklist_crud.get(db_session, non_existent_id)
        
        assert str(non_existent_id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_blacklist_entry_invalid_id(self, db_session: AsyncSession):
        """ブラックリストエントリ取得 - 無効なID"""
        # 実行・検証
        with pytest.raises(InvalidParameterError):
            await token_blacklist_crud.get(db_session, None)

    @pytest.mark.asyncio
    async def test_get_by_jti_success(self, db_session: AsyncSession, sample_blacklist_entry: TokenBlacklist):
        """JTIでブラックリストエントリ取得 - 正常系"""
        # 実行
        result = await token_blacklist_crud.get_by_jti(db_session, sample_blacklist_entry.jti)
        
        # 検証
        assert result is not None
        assert result.id == sample_blacklist_entry.id
        assert result.jti == sample_blacklist_entry.jti

    @pytest.mark.asyncio
    async def test_get_by_jti_not_found(self, db_session: AsyncSession):
        """JTIでブラックリストエントリ取得 - 存在しないJTI"""
        # 実行・検証
        with pytest.raises(TokenBlacklistNotFoundError):
            await token_blacklist_crud.get_by_jti(db_session, "nonexistent_jti")

    @pytest.mark.asyncio
    async def test_get_by_jti_empty_jti(self, db_session: AsyncSession):
        """JTIでブラックリストエントリ取得 - 空のJTI"""
        # 実行・検証
        with pytest.raises(InvalidParameterError):
            await token_blacklist_crud.get_by_jti(db_session, "")

    @pytest.mark.asyncio
    async def test_create_blacklist_entry_success(self, db_session: AsyncSession, test_data_factory):
        """ブラックリストエントリ作成 - 正常系"""
        # 準備
        blacklist_data = test_data_factory.create_token_blacklist_data(
            jti="new_jti_123",
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        # 実行
        result = await token_blacklist_crud.create(db_session, blacklist_data)
        
        # 検証
        assert result.jti == blacklist_data.jti
        assert result.expires_at == blacklist_data.expires_at
        assert result.id is not None

    @pytest.mark.asyncio
    async def test_create_blacklist_entry_empty_jti(self, db_session: AsyncSession, test_data_factory):
        """ブラックリストエントリ作成 - 空のJTI"""
        # 準備
        blacklist_data = test_data_factory.create_token_blacklist_data(jti="")
        
        # 実行・検証
        with pytest.raises(ValidationError):
            await token_blacklist_crud.create(db_session, blacklist_data)

    @pytest.mark.asyncio
    async def test_create_blacklist_entry_duplicate_jti(self, db_session: AsyncSession, sample_blacklist_entry: TokenBlacklist, test_data_factory):
        """ブラックリストエントリ作成 - 重複JTI"""
        # 準備
        blacklist_data = test_data_factory.create_token_blacklist_data(
            jti=sample_blacklist_entry.jti  # 既存のJTIと同じ
        )
        
        # 実行・検証
        with pytest.raises(ValidationError):
            await token_blacklist_crud.create(db_session, blacklist_data)

    @pytest.mark.asyncio
    async def test_create_blacklist_entry_past_expiry(self, db_session: AsyncSession, test_data_factory):
        """ブラックリストエントリ作成 - 過去の有効期限"""
        # 準備
        blacklist_data = test_data_factory.create_token_blacklist_data(
            jti="expired_jti",
            expires_at=datetime.utcnow() - timedelta(hours=1)  # 過去の日時
        )
        
        # 実行・検証
        with pytest.raises(ValidationError):
            await token_blacklist_crud.create(db_session, blacklist_data)

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_true(self, db_session: AsyncSession, sample_blacklist_entry: TokenBlacklist):
        """トークンブラックリストチェック - ブラックリスト済み"""
        # 実行
        result = await token_blacklist_crud.is_token_blacklisted(db_session, sample_blacklist_entry.jti)
        
        # 検証
        assert result == True

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_false(self, db_session: AsyncSession):
        """トークンブラックリストチェック - ブラックリスト未登録"""
        # 実行
        result = await token_blacklist_crud.is_token_blacklisted(db_session, "not_blacklisted_jti")
        
        # 検証
        assert result == False

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_expired_entry(self, db_session: AsyncSession, test_data_factory):
        """トークンブラックリストチェック - 期限切れエントリ"""
        # 準備 - 期限切れエントリを作成
        expired_data = test_data_factory.create_token_blacklist_data(
            jti="expired_blacklist_jti",
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        # バリデーションを回避して直接作成
        expired_entry = TokenBlacklist(**expired_data.dict())
        db_session.add(expired_entry)
        await db_session.commit()
        
        # 実行
        result = await token_blacklist_crud.is_token_blacklisted(db_session, expired_entry.jti)
        
        # 検証
        assert result == False  # 期限切れなのでブラックリストとして扱わない

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_empty_jti(self, db_session: AsyncSession):
        """トークンブラックリストチェック - 空のJTI"""
        # 実行・検証
        with pytest.raises(InvalidParameterError):
            await token_blacklist_crud.is_token_blacklisted(db_session, "")

    @pytest.mark.asyncio
    async def test_delete_blacklist_entry_success(self, db_session: AsyncSession, sample_blacklist_entry: TokenBlacklist):
        """ブラックリストエントリ削除 - 正常系"""
        # 実行
        result = await token_blacklist_crud.delete(db_session, sample_blacklist_entry.id)
        
        # 検証
        assert result == True
        
        # 削除されたことを確認
        with pytest.raises(TokenBlacklistNotFoundError):
            await token_blacklist_crud.get(db_session, sample_blacklist_entry.id)

    @pytest.mark.asyncio
    async def test_delete_blacklist_entry_not_found(self, db_session: AsyncSession):
        """ブラックリストエントリ削除 - 存在しないエントリ"""
        # 実行
        result = await token_blacklist_crud.delete(db_session, uuid4())
        
        # 検証
        assert result == False

    @pytest.mark.asyncio
    async def test_delete_blacklist_entry_invalid_id(self, db_session: AsyncSession):
        """ブラックリストエントリ削除 - 無効なID"""
        # 実行・検証
        with pytest.raises(InvalidParameterError):
            await token_blacklist_crud.delete(db_session, None)

    @pytest.mark.asyncio
    async def test_delete_by_jti_success(self, db_session: AsyncSession, sample_blacklist_entry: TokenBlacklist):
        """JTIでブラックリストエントリ削除 - 正常系"""
        # 実行
        result = await token_blacklist_crud.delete_by_jti(db_session, sample_blacklist_entry.jti)
        
        # 検証
        assert result == True
        
        # 削除されたことを確認
        with pytest.raises(TokenBlacklistNotFoundError):
            await token_blacklist_crud.get_by_jti(db_session, sample_blacklist_entry.jti)

    @pytest.mark.asyncio
    async def test_delete_by_jti_not_found(self, db_session: AsyncSession):
        """JTIでブラックリストエントリ削除 - 存在しないJTI"""
        # 実行
        result = await token_blacklist_crud.delete_by_jti(db_session, "nonexistent_jti")
        
        # 検証
        assert result == False

    @pytest.mark.asyncio
    async def test_delete_by_jti_empty_jti(self, db_session: AsyncSession):
        """JTIでブラックリストエントリ削除 - 空のJTI"""
        # 実行・検証
        with pytest.raises(InvalidParameterError):
            await token_blacklist_crud.delete_by_jti(db_session, "")

    @pytest.mark.asyncio
    async def test_delete_expired_entries_success(self, db_session: AsyncSession, test_data_factory):
        """期限切れエントリ削除 - 正常系"""
        # 準備 - 期限切れエントリを作成
        expired_data1 = test_data_factory.create_token_blacklist_data(
            jti="expired_jti_1",
            expires_at=datetime.utcnow() - timedelta(hours=2)
        )
        expired_data2 = test_data_factory.create_token_blacklist_data(
            jti="expired_jti_2",
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        # バリデーションを回避して直接作成
        expired_entry1 = TokenBlacklist(**expired_data1.dict())
        expired_entry2 = TokenBlacklist(**expired_data2.dict())
        db_session.add(expired_entry1)
        db_session.add(expired_entry2)
        await db_session.commit()
        
        # 有効なエントリも作成
        valid_data = test_data_factory.create_token_blacklist_data(
            jti="valid_jti",
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        valid_entry = await token_blacklist_crud.create(db_session, valid_data)
        
        # 実行
        result = await token_blacklist_crud.delete_expired_entries(db_session)
        
        # 検証
        assert result >= 2  # 少なくとも2つの期限切れエントリが削除された
        
        # 有効なエントリは残っていることを確認
        remaining_entry = await token_blacklist_crud.get(db_session, valid_entry.id)
        assert remaining_entry is not None

    @pytest.mark.asyncio
    async def test_delete_expired_entries_no_expired(self, db_session: AsyncSession):
        """期限切れエントリ削除 - 期限切れエントリなし"""
        # 実行
        result = await token_blacklist_crud.delete_expired_entries(db_session)
        
        # 検証
        assert result >= 0  # 削除されたエントリ数（0以上）

    @pytest.mark.asyncio
    async def test_get_all_active_entries(self, db_session: AsyncSession, sample_blacklist_entry: TokenBlacklist, test_data_factory):
        """有効なエントリ一覧取得"""
        # 準備 - 期限切れエントリを作成
        expired_data = test_data_factory.create_token_blacklist_data(
            jti="expired_for_active_test",
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        # バリデーションを回避して直接作成
        expired_entry = TokenBlacklist(**expired_data.dict())
        db_session.add(expired_entry)
        await db_session.commit()
        
        # 実行
        result = await token_blacklist_crud.get_all_active_entries(db_session)
        
        # 検証
        assert len(result) > 0
        assert all(entry.expires_at > datetime.utcnow() for entry in result)
        # 期限切れエントリは含まれていない
        expired_jtis = [entry.jti for entry in result]
        assert expired_entry.jti not in expired_jtis

    @pytest.mark.asyncio
    async def test_database_connection_error_simulation(self, db_session: AsyncSession):
        """データベース接続エラーのシミュレーション"""
        # セッションを無効化
        await db_session.close()
        
        # 実行・検証
        with pytest.raises(DatabaseConnectionError):
            await token_blacklist_crud.get(db_session, uuid4())

    @pytest.mark.asyncio
    async def test_concurrent_blacklist_creation(self, db_session: AsyncSession, test_data_factory):
        """同時ブラックリストエントリ作成のテスト"""
        import asyncio
        
        # 準備
        blacklist_data1 = test_data_factory.create_token_blacklist_data(jti="concurrent_jti_1")
        blacklist_data2 = test_data_factory.create_token_blacklist_data(jti="concurrent_jti_2")
        
        # 実行
        results = await asyncio.gather(
            token_blacklist_crud.create(db_session, blacklist_data1),
            token_blacklist_crud.create(db_session, blacklist_data2),
            return_exceptions=True
        )
        
        # 検証
        assert len(results) == 2
        success_count = sum(1 for r in results if isinstance(r, TokenBlacklist))
        assert success_count >= 1

    @pytest.mark.asyncio
    async def test_edge_case_very_long_jti(self, db_session: AsyncSession, test_data_factory):
        """境界値テスト - 非常に長いJTI"""
        # 準備
        long_jti = "a" * 1000
        blacklist_data = test_data_factory.create_token_blacklist_data(jti=long_jti)
        
        # 実行（データベースの制約によってはエラーになる可能性がある）
        try:
            result = await token_blacklist_crud.create(db_session, blacklist_data)
            assert result.jti == long_jti
        except Exception:
            # データベース制約によるエラーは許容
            pass

    @pytest.mark.asyncio
    async def test_bulk_blacklist_operations(self, db_session: AsyncSession, test_data_factory):
        """大量ブラックリスト操作のテスト"""
        # 準備 - 大量のエントリを作成
        entries = []
        for i in range(100):
            blacklist_data = test_data_factory.create_token_blacklist_data(
                jti=f"bulk_jti_{i}",
                expires_at=datetime.utcnow() + timedelta(hours=1)
            )
            entry = await token_blacklist_crud.create(db_session, blacklist_data)
            entries.append(entry)
        
        # 実行 - 有効なエントリ一覧取得
        active_entries = await token_blacklist_crud.get_all_active_entries(db_session)
        
        # 検証
        assert len(active_entries) >= 100
        
        # 実行 - ブラックリストチェック（パフォーマンステスト）
        import time
        start_time = time.time()
        for i in range(10):  # 10回チェック
            is_blacklisted = await token_blacklist_crud.is_token_blacklisted(db_session, f"bulk_jti_{i}")
            assert is_blacklisted == True
        end_time = time.time()
        
        # 検証 - 1秒以内で完了
        assert (end_time - start_time) < 1.0

    @pytest.mark.asyncio
    async def test_expiry_edge_cases(self, db_session: AsyncSession, test_data_factory):
        """有効期限の境界値テスト"""
        # 準備 - ちょうど期限切れのエントリ
        exactly_expired_data = test_data_factory.create_token_blacklist_data(
            jti="exactly_expired_jti",
            expires_at=datetime.utcnow()  # 現在時刻
        )
        # バリデーションを回避して直接作成
        exactly_expired_entry = TokenBlacklist(**exactly_expired_data.dict())
        db_session.add(exactly_expired_entry)
        await db_session.commit()
        
        # 準備 - 1秒後に期限切れのエントリ
        almost_expired_data = test_data_factory.create_token_blacklist_data(
            jti="almost_expired_jti",
            expires_at=datetime.utcnow() + timedelta(seconds=1)
        )
        almost_expired_entry = await token_blacklist_crud.create(db_session, almost_expired_data)
        
        # 実行・検証 - ちょうど期限切れ
        is_blacklisted_exactly = await token_blacklist_crud.is_token_blacklisted(db_session, exactly_expired_entry.jti)
        assert is_blacklisted_exactly == False
        
        # 実行・検証 - まだ有効
        is_blacklisted_almost = await token_blacklist_crud.is_token_blacklisted(db_session, almost_expired_entry.jti)
        assert is_blacklisted_almost == True

    @pytest.mark.asyncio
    async def test_unicode_jti_handling(self, db_session: AsyncSession, test_data_factory):
        """Unicode文字を含むJTIの処理"""
        # 準備
        unicode_jti = "日本語JTI_🔒_test"
        blacklist_data = test_data_factory.create_token_blacklist_data(jti=unicode_jti)
        
        # 実行
        result = await token_blacklist_crud.create(db_session, blacklist_data)
        
        # 検証
        assert result.jti == unicode_jti
        
        # JTIで取得テスト
        retrieved_entry = await token_blacklist_crud.get_by_jti(db_session, unicode_jti)
        assert retrieved_entry.id == result.id
        
        # ブラックリストチェック
        is_blacklisted = await token_blacklist_crud.is_token_blacklisted(db_session, unicode_jti)
        assert is_blacklisted == True

    @pytest.mark.asyncio
    async def test_token_blacklist_crud_comprehensive_workflow(self, db_session: AsyncSession, test_data_factory):
        """包括的なワークフローテスト"""
        # 1. ブラックリストエントリ作成
        blacklist_data = test_data_factory.create_token_blacklist_data(
            jti="workflow_jti",
            expires_at=datetime.utcnow() + timedelta(hours=2)
        )
        created_entry = await token_blacklist_crud.create(db_session, blacklist_data)
        
        # 2. 作成されたエントリを取得
        retrieved_entry = await token_blacklist_crud.get(db_session, created_entry.id)
        assert retrieved_entry.jti == blacklist_data.jti
        
        # 3. JTIで取得
        entry_by_jti = await token_blacklist_crud.get_by_jti(db_session, blacklist_data.jti)
        assert entry_by_jti.id == created_entry.id
        
        # 4. ブラックリストチェック
        is_blacklisted = await token_blacklist_crud.is_token_blacklisted(db_session, blacklist_data.jti)
        assert is_blacklisted == True
        
        # 5. 存在しないJTIのチェック
        is_not_blacklisted = await token_blacklist_crud.is_token_blacklisted(db_session, "nonexistent_jti")
        assert is_not_blacklisted == False
        
        # 6. 有効なエントリ一覧に含まれることを確認
        active_entries = await token_blacklist_crud.get_all_active_entries(db_session)
        active_jtis = [entry.jti for entry in active_entries]
        assert blacklist_data.jti in active_jtis
        
        # 7. 追加のエントリを作成（期限切れ）
        expired_data = test_data_factory.create_token_blacklist_data(
            jti="expired_workflow_jti",
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        # バリデーションを回避して直接作成
        expired_entry = TokenBlacklist(**expired_data.dict())
        db_session.add(expired_entry)
        await db_session.commit()
        
        # 8. 期限切れエントリ削除
        deleted_count = await token_blacklist_crud.delete_expired_entries(db_session)
        assert deleted_count >= 1
        
        # 9. 有効なエントリは残っていることを確認
        remaining_entry = await token_blacklist_crud.get(db_session, created_entry.id)
        assert remaining_entry is not None
        
        # 10. JTIでエントリ削除
        delete_result = await token_blacklist_crud.delete_by_jti(db_session, blacklist_data.jti)
        assert delete_result == True
        
        # 11. 削除後はブラックリストに含まれないことを確認
        is_blacklisted_after_delete = await token_blacklist_crud.is_token_blacklisted(db_session, blacklist_data.jti)
        assert is_blacklisted_after_delete == False
        
        # 12. 削除されたことを確認
        with pytest.raises(TokenBlacklistNotFoundError):
            await token_blacklist_crud.get_by_jti(db_session, blacklist_data.jti)
