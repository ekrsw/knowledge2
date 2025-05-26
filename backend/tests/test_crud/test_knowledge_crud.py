"""
KnowledgeCRUD のテスト
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, timedelta, date
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.knowledge import knowledge_crud
from app.schemas import KnowledgeCreate, KnowledgeUpdate
from app.models import Knowledge, User
from app.models.knowledge import StatusEnum, ChangeTypeEnum
from app.core.exceptions import (
    KnowledgeNotFoundError,
    DatabaseError,
    ValidationError,
    AuthorizationError
)


class TestKnowledgeCRUD:
    """KnowledgeCRUD のテストクラス"""

    @pytest.mark.asyncio
    async def test_get_knowledge_success(self, db_session: AsyncSession, sample_knowledge: Knowledge):
        """ナレッジ取得 - 正常系"""
        # 実行
        result = await knowledge_crud.get(db_session, sample_knowledge.id)
        
        # 検証
        assert result is not None
        assert result.id == sample_knowledge.id
        assert result.title == sample_knowledge.title
        assert result.answer == sample_knowledge.answer
        assert result.status == sample_knowledge.status

    @pytest.mark.asyncio
    async def test_get_knowledge_not_found(self, db_session: AsyncSession):
        """ナレッジ取得 - 存在しないID"""
        non_existent_id = uuid4()
        
        # 実行
        result = await knowledge_crud.get(db_session, non_existent_id)
        
        # 検証
        assert result is None

    @pytest.mark.asyncio
    async def test_get_multi_success(self, db_session: AsyncSession, multiple_knowledge: list[Knowledge]):
        """ナレッジ一覧取得 - 正常系"""
        # 実行
        result = await knowledge_crud.get_multi(db_session, skip=0, limit=10)
        
        # 検証
        assert len(result) == len(multiple_knowledge)
        assert all(isinstance(knowledge, Knowledge) for knowledge in result)

    @pytest.mark.asyncio
    async def test_get_multi_pagination(self, db_session: AsyncSession, multiple_knowledge: list[Knowledge]):
        """ナレッジ一覧取得 - ページネーション"""
        # 実行
        first_page = await knowledge_crud.get_multi(db_session, skip=0, limit=2)
        second_page = await knowledge_crud.get_multi(db_session, skip=2, limit=2)
        
        # 検証
        assert len(first_page) == 2
        assert len(second_page) == 2
        assert first_page[0].id != second_page[0].id

    @pytest.mark.asyncio
    async def test_get_multi_invalid_skip(self, db_session: AsyncSession):
        """ナレッジ一覧取得 - 無効なskip"""
        # 実行・検証
        with pytest.raises(ValidationError):
            await knowledge_crud.get_multi(db_session, skip=-1, limit=10)

    @pytest.mark.asyncio
    async def test_get_multi_invalid_limit(self, db_session: AsyncSession):
        """ナレッジ一覧取得 - 無効なlimit"""
        # 実行・検証
        with pytest.raises(ValidationError):
            await knowledge_crud.get_multi(db_session, skip=0, limit=0)
        
        with pytest.raises(ValidationError):
            await knowledge_crud.get_multi(db_session, skip=0, limit=1001)

    @pytest.mark.asyncio
    async def test_get_by_status_success(self, db_session: AsyncSession, multiple_knowledge: list[Knowledge]):
        """ステータス別ナレッジ取得 - 正常系"""
        # 実行
        draft_knowledge = await knowledge_crud.get_by_status(db_session, StatusEnum.draft)
        
        # 検証
        assert all(k.status == StatusEnum.draft for k in draft_knowledge)

    @pytest.mark.asyncio
    async def test_get_by_status_no_results(self, db_session: AsyncSession):
        """ステータス別ナレッジ取得 - 該当なし"""
        # 実行
        result = await knowledge_crud.get_by_status(db_session, StatusEnum.published)
        
        # 検証
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_by_status_invalid_skip(self, db_session: AsyncSession):
        """ステータス別ナレッジ取得 - 無効なskip"""
        # 実行・検証
        with pytest.raises(ValidationError):
            await knowledge_crud.get_by_status(db_session, StatusEnum.draft, skip=-1)

    @pytest.mark.asyncio
    async def test_get_by_user_success(self, db_session: AsyncSession, sample_user: User, sample_knowledge: Knowledge):
        """ユーザー別ナレッジ取得 - 正常系"""
        # 実行
        result = await knowledge_crud.get_by_user(db_session, sample_user.id)
        
        # 検証
        assert len(result) > 0
        assert all(k.created_by == sample_user.id for k in result)

    @pytest.mark.asyncio
    async def test_get_by_user_no_results(self, db_session: AsyncSession):
        """ユーザー別ナレッジ取得 - 該当なし"""
        # 実行
        result = await knowledge_crud.get_by_user(db_session, uuid4())
        
        # 検証
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_by_user_invalid_skip(self, db_session: AsyncSession, sample_user: User):
        """ユーザー別ナレッジ取得 - 無効なskip"""
        # 実行・検証
        with pytest.raises(ValidationError):
            await knowledge_crud.get_by_user(db_session, sample_user.id, skip=-1)

    @pytest.mark.asyncio
    async def test_get_by_article_success(self, db_session: AsyncSession, sample_knowledge: Knowledge):
        """記事別ナレッジ取得 - 正常系"""
        # 実行
        result = await knowledge_crud.get_by_article(db_session, sample_knowledge.article_number)
        
        # 検証
        assert len(result) > 0
        assert all(k.article_number == sample_knowledge.article_number for k in result)

    @pytest.mark.asyncio
    async def test_get_by_article_no_results(self, db_session: AsyncSession):
        """記事別ナレッジ取得 - 該当なし"""
        # 実行
        result = await knowledge_crud.get_by_article(db_session, "NONEXISTENT")
        
        # 検証
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_by_article_empty_article_number(self, db_session: AsyncSession):
        """記事別ナレッジ取得 - 空の記事番号"""
        # 実行・検証
        with pytest.raises(ValidationError):
            await knowledge_crud.get_by_article(db_session, "")

    @pytest.mark.asyncio
    async def test_create_knowledge_success(self, db_session: AsyncSession, sample_user: User, test_data_factory):
        """ナレッジ作成 - 正常系"""
        # 準備
        knowledge_data = test_data_factory.create_knowledge_data(
            article_number="ART001",
            change_type=ChangeTypeEnum.modify,
            title="新しいナレッジ",
            question="質問内容",
            answer="回答内容"
        )
        
        # 実行
        result = await knowledge_crud.create(db_session, knowledge_data, sample_user.id)
        
        # 検証
        assert result.title == knowledge_data.title
        assert result.answer == knowledge_data.answer
        assert result.created_by == sample_user.id
        assert result.status == StatusEnum.draft
        assert result.id is not None

    @pytest.mark.asyncio
    async def test_create_knowledge_with_all_fields(self, db_session: AsyncSession, sample_user: User, test_data_factory):
        """ナレッジ作成 - 全フィールド指定"""
        # 準備
        knowledge_data = test_data_factory.create_knowledge_data(
            article_number="ART002",
            change_type=ChangeTypeEnum.delete,
            title="削除提案ナレッジ",
            info_category="削除",
            keywords="削除,提案",
            importance=True,
            target="管理者",
            open_publish_start=date.today(),
            open_publish_end=date.today() + timedelta(days=30),
            question="なぜ削除が必要ですか？",
            answer="古い情報のため削除が必要です。",
            add_comments="追加のコメント",
            remarks="特記事項"
        )
        
        # 実行
        result = await knowledge_crud.create(db_session, knowledge_data, sample_user.id)
        
        # 検証
        assert result.title == knowledge_data.title
        assert result.info_category == knowledge_data.info_category
        assert result.keywords == knowledge_data.keywords
        assert result.importance == knowledge_data.importance
        assert result.target == knowledge_data.target
        assert result.open_publish_start == knowledge_data.open_publish_start
        assert result.open_publish_end == knowledge_data.open_publish_end
        assert result.question == knowledge_data.question
        assert result.answer == knowledge_data.answer
        assert result.add_comments == knowledge_data.add_comments
        assert result.remarks == knowledge_data.remarks
        assert result.change_type == knowledge_data.change_type
        assert result.created_by == sample_user.id

    @pytest.mark.asyncio
    async def test_update_knowledge_success(self, db_session: AsyncSession, sample_knowledge: Knowledge):
        """ナレッジ更新 - 正常系"""
        # 準備
        update_data = KnowledgeUpdate(
            title="更新されたタイトル",
            answer="更新された回答"
        )
        
        # 実行
        result = await knowledge_crud.update(db_session, sample_knowledge, update_data)
        
        # 検証
        assert result.title == "更新されたタイトル"
        assert result.answer == "更新された回答"
        assert result.id == sample_knowledge.id

    @pytest.mark.asyncio
    async def test_update_knowledge_no_data(self, db_session: AsyncSession, sample_knowledge: Knowledge):
        """ナレッジ更新 - 更新データなし"""
        # 準備
        update_data = KnowledgeUpdate()
        
        # 実行
        result = await knowledge_crud.update(db_session, sample_knowledge, update_data)
        
        # 検証（変更されていない）
        assert result.id == sample_knowledge.id
        assert result.title == sample_knowledge.title

    @pytest.mark.asyncio
    async def test_update_knowledge_partial_update(self, db_session: AsyncSession, sample_knowledge: Knowledge):
        """ナレッジ更新 - 部分更新"""
        # 準備
        original_title = sample_knowledge.title
        update_data = KnowledgeUpdate(importance=True)
        
        # 実行
        result = await knowledge_crud.update(db_session, sample_knowledge, update_data)
        
        # 検証
        assert result.importance == True
        assert result.title == original_title  # 変更されていない

    @pytest.mark.asyncio
    async def test_update_status_draft_to_submitted_by_creator(self, db_session: AsyncSession, sample_knowledge: Knowledge, sample_user: User):
        """ステータス更新 - 作成者がドラフトから提出へ"""
        # 実行
        result = await knowledge_crud.update_status(
            db_session, 
            sample_knowledge, 
            StatusEnum.submitted,
            sample_user
        )
        
        # 検証
        assert result.status == StatusEnum.submitted
        assert result.submitted_at is not None

    @pytest.mark.asyncio
    async def test_update_status_submitted_to_approved_by_admin(self, db_session: AsyncSession, sample_knowledge: Knowledge, admin_user: User):
        """ステータス更新 - 管理者が提出から承認へ"""
        # 準備：まず提出状態にする
        sample_knowledge.status = StatusEnum.submitted
        await db_session.flush()
        
        # 実行
        result = await knowledge_crud.update_status(
            db_session, 
            sample_knowledge, 
            StatusEnum.approved,
            admin_user
        )
        
        # 検証
        assert result.status == StatusEnum.approved
        assert result.approved_at is not None
        assert result.approved_by == admin_user.id

    @pytest.mark.asyncio
    async def test_update_status_unauthorized_user(self, db_session: AsyncSession, sample_knowledge: Knowledge):
        """ステータス更新 - 権限のないユーザー"""
        # 準備：別のユーザーを作成
        other_user = User(
            id=uuid4(),
            username="otheruser",
            hashed_password="hashedpassword",
            full_name="Other User",
            is_admin=False
        )
        db_session.add(other_user)
        await db_session.flush()
        
        # 実行・検証
        with pytest.raises(AuthorizationError):
            await knowledge_crud.update_status(
                db_session, 
                sample_knowledge, 
                StatusEnum.submitted,
                other_user
            )

    @pytest.mark.asyncio
    async def test_update_status_invalid_transition_by_creator(self, db_session: AsyncSession, sample_knowledge: Knowledge, sample_user: User):
        """ステータス更新 - 作成者による無効な遷移"""
        # 実行・検証（ドラフトから直接承認は無効）
        with pytest.raises(AuthorizationError):
            await knowledge_crud.update_status(
                db_session, 
                sample_knowledge, 
                StatusEnum.approved,
                sample_user
            )

    @pytest.mark.asyncio
    async def test_delete_knowledge_success_by_creator(self, db_session: AsyncSession, sample_knowledge: Knowledge, sample_user: User):
        """ナレッジ削除 - 作成者による削除"""
        # 実行
        result = await knowledge_crud.delete(db_session, sample_knowledge.id, sample_user.id)
        
        # 検証
        assert result == True
        
        # 削除されたことを確認
        deleted_knowledge = await knowledge_crud.get(db_session, sample_knowledge.id)
        assert deleted_knowledge is None

    @pytest.mark.asyncio
    async def test_delete_knowledge_not_found(self, db_session: AsyncSession, sample_user: User):
        """ナレッジ削除 - 存在しないナレッジ"""
        # 実行
        result = await knowledge_crud.delete(db_session, uuid4(), sample_user.id)
        
        # 検証
        assert result == False

    @pytest.mark.asyncio
    async def test_delete_knowledge_unauthorized_user(self, db_session: AsyncSession, sample_knowledge: Knowledge):
        """ナレッジ削除 - 権限のないユーザー"""
        # 実行
        result = await knowledge_crud.delete(db_session, sample_knowledge.id, uuid4())
        
        # 検証
        assert result == False

    @pytest.mark.asyncio
    async def test_concurrent_knowledge_creation(self, db_session: AsyncSession, sample_user: User, test_data_factory):
        """同時ナレッジ作成のテスト"""
        import asyncio
        
        # 準備
        knowledge_data1 = test_data_factory.create_knowledge_data(
            article_number="ART001",
            change_type=ChangeTypeEnum.modify,
            title="同時作成1"
        )
        knowledge_data2 = test_data_factory.create_knowledge_data(
            article_number="ART002",
            change_type=ChangeTypeEnum.modify,
            title="同時作成2"
        )
        
        # 実行
        results = await asyncio.gather(
            knowledge_crud.create(db_session, knowledge_data1, sample_user.id),
            knowledge_crud.create(db_session, knowledge_data2, sample_user.id),
            return_exceptions=True
        )
        
        # 検証
        assert len(results) == 2
        success_count = sum(1 for r in results if isinstance(r, Knowledge))
        assert success_count >= 1

    @pytest.mark.asyncio
    async def test_edge_case_very_long_title(self, db_session: AsyncSession, sample_user: User, test_data_factory):
        """境界値テスト - 非常に長いタイトル"""
        # 準備
        long_title = "a" * 200  # 200文字のタイトル
        knowledge_data = test_data_factory.create_knowledge_data(
            article_number="ART001",
            change_type=ChangeTypeEnum.modify,
            title=long_title
        )
        
        # 実行
        result = await knowledge_crud.create(db_session, knowledge_data, sample_user.id)
        
        # 検証
        assert result.title == long_title

    @pytest.mark.asyncio
    async def test_unicode_content_handling(self, db_session: AsyncSession, sample_user: User, test_data_factory):
        """Unicode文字を含むコンテンツのテスト"""
        # 準備
        knowledge_data = test_data_factory.create_knowledge_data(
            article_number="ART001",
            change_type=ChangeTypeEnum.modify,
            title="日本語タイトル 🚀",
            question="これは日本語の質問です。絵文字も含まれています 😊",
            answer="これは日本語の回答です。絵文字も含まれています 🎉"
        )
        
        # 実行
        result = await knowledge_crud.create(db_session, knowledge_data, sample_user.id)
        
        # 検証
        assert result.title == knowledge_data.title
        assert result.answer == knowledge_data.answer
        assert "🚀" in result.title
        assert "🎉" in result.answer

    @pytest.mark.asyncio
    async def test_knowledge_with_date_fields(self, db_session: AsyncSession, sample_user: User, test_data_factory):
        """日付フィールドを含むナレッジのテスト"""
        # 準備
        start_date = date.today()
        end_date = start_date + timedelta(days=30)
        
        knowledge_data = test_data_factory.create_knowledge_data(
            article_number="ART001",
            change_type=ChangeTypeEnum.modify,
            title="日付テスト",
            open_publish_start=start_date,
            open_publish_end=end_date
        )
        
        # 実行
        result = await knowledge_crud.create(db_session, knowledge_data, sample_user.id)
        
        # 検証
        assert result.open_publish_start == start_date
        assert result.open_publish_end == end_date

    @pytest.mark.asyncio
    async def test_knowledge_status_workflow(self, db_session: AsyncSession, sample_user: User, admin_user: User, test_data_factory):
        """ナレッジのステータスワークフローテスト"""
        # 準備：ナレッジ作成
        knowledge_data = test_data_factory.create_knowledge_data(
            article_number="ART001",
            change_type=ChangeTypeEnum.modify,
            title="ワークフローテスト"
        )
        
        knowledge = await knowledge_crud.create(db_session, knowledge_data, sample_user.id)
        assert knowledge.status == StatusEnum.draft
        
        # ステップ1: ドラフト → 提出
        knowledge = await knowledge_crud.update_status(db_session, knowledge, StatusEnum.submitted, sample_user)
        assert knowledge.status == StatusEnum.submitted
        assert knowledge.submitted_at is not None
        
        # ステップ2: 提出 → 承認（管理者）
        knowledge = await knowledge_crud.update_status(db_session, knowledge, StatusEnum.approved, admin_user)
        assert knowledge.status == StatusEnum.approved
        assert knowledge.approved_at is not None
        assert knowledge.approved_by == admin_user.id
        
        # ステップ3: 承認 → 公開（管理者）
        knowledge = await knowledge_crud.update_status(db_session, knowledge, StatusEnum.published, admin_user)
        assert knowledge.status == StatusEnum.published

    @pytest.mark.asyncio
    async def test_get_multi_with_different_limits(self, db_session: AsyncSession, multiple_knowledge: list[Knowledge]):
        """異なるlimit値でのget_multiテスト"""
        # limit=1
        result1 = await knowledge_crud.get_multi(db_session, skip=0, limit=1)
        assert len(result1) == 1
        
        # limit=3
        result3 = await knowledge_crud.get_multi(db_session, skip=0, limit=3)
        assert len(result3) == 3
        
        # limit=100（全件取得）
        result_all = await knowledge_crud.get_multi(db_session, skip=0, limit=100)
        assert len(result_all) == len(multiple_knowledge)

    @pytest.mark.asyncio
    async def test_get_by_status_with_pagination(self, db_session: AsyncSession, multiple_knowledge: list[Knowledge]):
        """ステータス別取得でのページネーションテスト"""
        # ドラフト状態のナレッジを取得
        draft_page1 = await knowledge_crud.get_by_status(db_session, StatusEnum.draft, skip=0, limit=1)
        draft_page2 = await knowledge_crud.get_by_status(db_session, StatusEnum.draft, skip=1, limit=1)
        
        # 異なるナレッジが取得されることを確認
        if len(draft_page1) > 0 and len(draft_page2) > 0:
            assert draft_page1[0].id != draft_page2[0].id

    @pytest.mark.asyncio
    async def test_update_knowledge_all_fields(self, db_session: AsyncSession, sample_knowledge: Knowledge):
        """ナレッジの全フィールド更新テスト"""
        # 準備
        new_date = date.today() + timedelta(days=60)
        update_data = KnowledgeUpdate(
            title="完全更新タイトル",
            info_category="更新カテゴリ",
            keywords="更新,キーワード",
            importance=True,
            target="更新対象",
            open_publish_start=new_date,
            open_publish_end=new_date + timedelta(days=30),
            question="更新された質問",
            answer="更新された回答",
            add_comments="更新されたコメント",
            remarks="更新された備考"
        )
        
        # 実行
        result = await knowledge_crud.update(db_session, sample_knowledge, update_data)
        
        # 検証
        assert result.title == update_data.title
        assert result.info_category == update_data.info_category
        assert result.keywords == update_data.keywords
        assert result.importance == update_data.importance
        assert result.target == update_data.target
        assert result.open_publish_start == update_data.open_publish_start
        assert result.open_publish_end == update_data.open_publish_end
        assert result.question == update_data.question
        assert result.answer == update_data.answer
        assert result.add_comments == update_data.add_comments
        assert result.remarks == update_data.remarks
