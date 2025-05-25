from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from app.core.exceptions import KnowledgeNotFoundError, ArticleNotFoundError, DatabaseQueryError
from app.core.logging import get_logger
from app.models import Knowledge, StatusEnum, ChangeTypeEnum, User
from app.schemas import KnowledgeCreate, KnowledgeUpdate


class KnowledgeCRUD:
    """ナレッジ関連のCRUD操作"""
    logger = get_logger(__name__)
    async def get(self, db: AsyncSession, id: UUID) -> Optional[Knowledge]:
        """IDでナレッジを取得"""
        self.logger.info(f"Retrieving knowledge by id: {id}")
        result = await db.execute(
            select(Knowledge)
            .options(selectinload(Knowledge.author), selectinload(Knowledge.approver))
            .filter(Knowledge.id == id)
        )
        knowledge = result.scalar_one_or_none()
        if knowledge:
            self.logger.info(f"Found knowledge with id: {id}")
        return knowledge
    
    async def get_multi(
        self, 
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Knowledge]:
        """ナレッジ一覧を取得（新しい順）"""
        self.logger.info(f"Retrieved all knowledge")
        try:
            result = await db.execute(
                select(Knowledge)
                .options(selectinload(Knowledge.author), selectinload(Knowledge.approver))
                .order_by(desc(Knowledge.created_at))
                .offset(skip)
                .limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Error retrieving all knowledge: {str(e)}")
            raise DatabaseQueryError(f"Failed to retrieve all knowledge: {str(e)}") from e
    
    async def get_by_status(
        self, 
        db: AsyncSession, 
        status: StatusEnum, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Knowledge]:
        """ステータス別ナレッジ一覧を取得"""
        try:
            result = await db.execute(
                select(Knowledge)
                .options(selectinload(Knowledge.author), selectinload(Knowledge.approver))
                .where(Knowledge.status == status)
                .order_by(desc(Knowledge.created_at))
                .offset(skip)
                .limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Error retrieving all knowledge: {str(e)}")
            raise DatabaseQueryError(f"Failed to retrieve all knowledge: {str(e)}") from e
    
    async def get_by_user(
        self, 
        db: AsyncSession, 
        user_id: UUID, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Knowledge]:
        """特定ユーザーのナレッジ一覧を取得"""
        try:
            result = await db.execute(
                select(Knowledge)
                .options(selectinload(Knowledge.author), selectinload(Knowledge.approver))
                .where(Knowledge.created_by == user_id)
                .order_by(desc(Knowledge.created_at))
                .offset(skip)
                .limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Error retrieving all knowledge: {str(e)}")
            raise DatabaseQueryError(f"Failed to retrieve all knowledge: {str(e)}") from e
    
    async def get_by_article(
        self, 
        db: AsyncSession, 
        article_number: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Knowledge]:
        """特定記事に対するナレッジ一覧を取得"""
        try:
            result = await db.execute(
                select(Knowledge)
                .options(selectinload(Knowledge.author), selectinload(Knowledge.approver))
                .where(Knowledge.article_number == article_number)
                .order_by(desc(Knowledge.created_at))
                .offset(skip)
                .limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Error retrieving all knowledge: {str(e)}")
            raise DatabaseQueryError(f"Failed to retrieve all knowledge: {str(e)}") from e
    
    async def create(
        self, 
        db: AsyncSession, 
        obj_in: KnowledgeCreate, 
        user_id: UUID
    ) -> Knowledge:
        """新しいナレッジを作成"""
        # 記事番号の存在チェックは呼び出し元で行う
        db_obj = Knowledge(
            article_number=obj_in.article_number,
            change_type=obj_in.change_type,
            title=obj_in.title,
            info_category=obj_in.info_category,
            keywords=obj_in.keywords,
            importance=obj_in.importance,
            target=obj_in.target,
            open_publish_start=obj_in.open_publish_start,
            open_publish_end=obj_in.open_publish_end,
            question=obj_in.question,
            answer=obj_in.answer,
            add_comments=obj_in.add_comments,
            remarks=obj_in.remarks,
            created_by=user_id
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        
        # 関連データを含めて再取得
        return await self.get(db, db_obj.id)
    
    async def update(
        self, 
        db: AsyncSession, 
        db_obj: Knowledge, 
        obj_in: KnowledgeUpdate
    ) -> Knowledge:
        """ナレッジを更新"""
        update_data = obj_in.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        await db.commit()
        await db.refresh(db_obj)
        
        # 関連データを含めて再取得
        return await self.get(db, db_obj.id)
    
    async def update_status(
        self, 
        db: AsyncSession, 
        db_obj: Knowledge, 
        new_status: StatusEnum, 
        user: User
    ) -> Knowledge:
        """ナレッジのステータスを更新（権限チェック付き）"""
        current_status = db_obj.status
        
        # 権限チェック
        if user.is_admin:
            # 管理者は全てのステータス変更を許可
            pass
        elif db_obj.created_by == user.id:
            # 作成者は draft → submitted, submitted → draft のみ許可
            if not ((current_status == StatusEnum.draft and new_status == StatusEnum.submitted) or
                   (current_status == StatusEnum.submitted and new_status == StatusEnum.draft)):
                raise KnowledgeNotFoundError(db_obj.id)
        else:
            # その他のユーザーは変更不可
            raise KnowledgeNotFoundError(db_obj.id)
        
        db_obj.status = new_status
        
        # submitted状態になった時にsubmitted_atを設定
        if new_status == StatusEnum.submitted and current_status != StatusEnum.submitted:
            db_obj.submitted_at = datetime.utcnow()
        
        # approved状態になった時にapproved_atとapproved_byを設定
        if new_status == StatusEnum.approved and current_status != StatusEnum.approved:
            db_obj.approved_at = datetime.utcnow()
            db_obj.approved_by = user.id
        
        # approved状態から他の状態に変更された時にapproved_atとapproved_byをクリア
        if current_status == StatusEnum.approved and new_status != StatusEnum.approved:
            db_obj.approved_at = None
            db_obj.approved_by = None
        
        await db.flush()
        # commitはsessionのfinallyで行う
        
        # 関連データを含めて再取得
        return await self.get(db, db_obj.id)
    
    async def delete(self, db: AsyncSession, id: UUID, user_id: UUID) -> bool:
        """ナレッジを削除（作成者のみ）"""
        result = await db.execute(
            select(Knowledge).where(
                and_(Knowledge.id == id, Knowledge.created_by == user_id)
            )
        )
        db_obj = result.scalar_one_or_none()
        
        if not db_obj:
            return False
        
        await db.delete(db_obj)
        await db.flush()
        # commitはsessionのfinallyで行う
        return True


# シングルトンインスタンス
knowledge_crud = KnowledgeCRUD()
