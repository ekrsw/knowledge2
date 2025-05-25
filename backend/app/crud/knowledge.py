from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from app.core.exceptions import (
    KnowledgeNotFoundError, 
    ArticleNotFoundError, 
    DatabaseError,
    AuthorizationError,
    ValidationError
)
from app.core.logging import get_logger
from app.models import Knowledge, StatusEnum, ChangeTypeEnum, User
from app.schemas import KnowledgeCreate, KnowledgeUpdate


class KnowledgeCRUD:
    """ナレッジ関連のCRUD操作"""
    logger = get_logger(__name__)
    async def get(self, db: AsyncSession, id: UUID) -> Optional[Knowledge]:
        """IDでナレッジを取得"""
        try:
            self.logger.info(f"Retrieving knowledge by id: {id}")
            result = await db.execute(
                select(Knowledge)
                .options(selectinload(Knowledge.author), selectinload(Knowledge.approver))
                .filter(Knowledge.id == id)
            )
            knowledge = result.scalar_one_or_none()
            if knowledge:
                self.logger.info(f"Found knowledge with id: {id}")
            else:
                self.logger.warning(f"Knowledge with id {id} not found")
            return knowledge
        except Exception as e:
            self.logger.error(f"Error retrieving knowledge by id {id}: {str(e)}")
            raise DatabaseError(f"ナレッジの取得中にエラーが発生しました: {str(e)}") from e
    
    async def get_multi(
        self, 
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Knowledge]:
        """ナレッジ一覧を取得（新しい順）"""
        try:
            # パラメータ検証
            if skip < 0:
                raise ValidationError("skipは0以上である必要があります")
            if limit <= 0 or limit > 1000:
                raise ValidationError("limitは1以上1000以下である必要があります")
            
            self.logger.info(f"Retrieving knowledge list (skip={skip}, limit={limit})")
            result = await db.execute(
                select(Knowledge)
                .options(selectinload(Knowledge.author), selectinload(Knowledge.approver))
                .order_by(desc(Knowledge.created_at))
                .offset(skip)
                .limit(limit)
            )
            knowledge_list = result.scalars().all()
            self.logger.info(f"Retrieved {len(knowledge_list)} knowledge items")
            return knowledge_list
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Error retrieving knowledge list: {str(e)}")
            raise DatabaseError(f"ナレッジ一覧の取得中にエラーが発生しました: {str(e)}") from e
    
    async def get_by_status(
        self, 
        db: AsyncSession, 
        status: StatusEnum, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Knowledge]:
        """ステータス別ナレッジ一覧を取得"""
        try:
            # パラメータ検証
            if skip < 0:
                raise ValidationError("skipは0以上である必要があります")
            if limit <= 0 or limit > 1000:
                raise ValidationError("limitは1以上1000以下である必要があります")
            
            self.logger.info(f"Retrieving knowledge by status: {status} (skip={skip}, limit={limit})")
            result = await db.execute(
                select(Knowledge)
                .options(selectinload(Knowledge.author), selectinload(Knowledge.approver))
                .where(Knowledge.status == status)
                .order_by(desc(Knowledge.created_at))
                .offset(skip)
                .limit(limit)
            )
            knowledge_list = result.scalars().all()
            self.logger.info(f"Retrieved {len(knowledge_list)} knowledge items with status {status}")
            return knowledge_list
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Error retrieving knowledge by status {status}: {str(e)}")
            raise DatabaseError(f"ステータス別ナレッジ一覧の取得中にエラーが発生しました: {str(e)}") from e
    
    async def get_by_user(
        self, 
        db: AsyncSession, 
        user_id: UUID, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Knowledge]:
        """特定ユーザーのナレッジ一覧を取得"""
        try:
            # パラメータ検証
            if skip < 0:
                raise ValidationError("skipは0以上である必要があります")
            if limit <= 0 or limit > 1000:
                raise ValidationError("limitは1以上1000以下である必要があります")
            
            self.logger.info(f"Retrieving knowledge by user: {user_id} (skip={skip}, limit={limit})")
            result = await db.execute(
                select(Knowledge)
                .options(selectinload(Knowledge.author), selectinload(Knowledge.approver))
                .where(Knowledge.created_by == user_id)
                .order_by(desc(Knowledge.created_at))
                .offset(skip)
                .limit(limit)
            )
            knowledge_list = result.scalars().all()
            self.logger.info(f"Retrieved {len(knowledge_list)} knowledge items for user {user_id}")
            return knowledge_list
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Error retrieving knowledge by user {user_id}: {str(e)}")
            raise DatabaseError(f"ユーザー別ナレッジ一覧の取得中にエラーが発生しました: {str(e)}") from e
    
    async def get_by_article(
        self, 
        db: AsyncSession, 
        article_number: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Knowledge]:
        """特定記事に対するナレッジ一覧を取得"""
        try:
            # パラメータ検証
            if not article_number or not article_number.strip():
                raise ValidationError("記事番号は必須です")
            if skip < 0:
                raise ValidationError("skipは0以上である必要があります")
            if limit <= 0 or limit > 1000:
                raise ValidationError("limitは1以上1000以下である必要があります")
            
            self.logger.info(f"Retrieving knowledge by article: {article_number} (skip={skip}, limit={limit})")
            result = await db.execute(
                select(Knowledge)
                .options(selectinload(Knowledge.author), selectinload(Knowledge.approver))
                .where(Knowledge.article_number == article_number)
                .order_by(desc(Knowledge.created_at))
                .offset(skip)
                .limit(limit)
            )
            knowledge_list = result.scalars().all()
            self.logger.info(f"Retrieved {len(knowledge_list)} knowledge items for article {article_number}")
            return knowledge_list
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Error retrieving knowledge by article {article_number}: {str(e)}")
            raise DatabaseError(f"記事別ナレッジ一覧の取得中にエラーが発生しました: {str(e)}") from e
    
    async def create(
        self, 
        db: AsyncSession, 
        obj_in: KnowledgeCreate, 
        user_id: UUID
    ) -> Knowledge:
        """新しいナレッジを作成"""
        try:
            self.logger.info(f"Creating new knowledge with title: {obj_in.title} by user: {user_id}")
            
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
            await db.flush()
            
            self.logger.info(f"Successfully created knowledge with id: {db_obj.id}")
            
            # 関連データを含めて再取得
            return await self.get(db, db_obj.id)
        except Exception as e:
            self.logger.error(f"Error creating knowledge: {str(e)}")
            raise DatabaseError(f"ナレッジの作成中にエラーが発生しました: {str(e)}") from e
    
    async def update(
        self, 
        db: AsyncSession, 
        db_obj: Knowledge, 
        obj_in: KnowledgeUpdate
    ) -> Knowledge:
        """ナレッジを更新"""
        try:
            self.logger.info(f"Updating knowledge with id: {db_obj.id}")
            
            update_data = obj_in.dict(exclude_unset=True)
            
            if not update_data:
                self.logger.warning(f"No update data provided for knowledge {db_obj.id}")
                return db_obj
            
            for field, value in update_data.items():
                setattr(db_obj, field, value)
            
            await db.commit()
            await db.refresh(db_obj)
            
            self.logger.info(f"Successfully updated knowledge with id: {db_obj.id}")
            
            # 関連データを含めて再取得
            return await self.get(db, db_obj.id)
        except Exception as e:
            self.logger.error(f"Error updating knowledge {db_obj.id}: {str(e)}")
            await db.rollback()
            raise DatabaseError(f"ナレッジの更新中にエラーが発生しました: {str(e)}") from e
    
    async def update_status(
        self, 
        db: AsyncSession, 
        db_obj: Knowledge, 
        new_status: StatusEnum, 
        user: User
    ) -> Knowledge:
        """ナレッジのステータスを更新（権限チェック付き）"""
        try:
            current_status = db_obj.status
            self.logger.info(f"Updating knowledge status from {current_status} to {new_status} for knowledge {db_obj.id} by user {user.id}")
            
            # 権限チェック
            if user.is_admin:
                # 管理者は全てのステータス変更を許可
                self.logger.info(f"Admin user {user.id} updating knowledge status")
            elif db_obj.created_by == user.id:
                # 作成者は draft → submitted, submitted → draft のみ許可
                if not ((current_status == StatusEnum.draft and new_status == StatusEnum.submitted) or
                       (current_status == StatusEnum.submitted and new_status == StatusEnum.draft)):
                    self.logger.warning(f"Unauthorized status change attempt by user {user.id} for knowledge {db_obj.id}")
                    raise AuthorizationError(f"ステータスの変更権限がありません。現在のステータス: {current_status}, 変更先: {new_status}")
            else:
                # その他のユーザーは変更不可
                self.logger.warning(f"Unauthorized status change attempt by user {user.id} for knowledge {db_obj.id}")
                raise AuthorizationError("このナレッジのステータスを変更する権限がありません")
            
            db_obj.status = new_status
            
            # submitted状態になった時にsubmitted_atを設定
            if new_status == StatusEnum.submitted and current_status != StatusEnum.submitted:
                db_obj.submitted_at = datetime.utcnow()
                self.logger.info(f"Set submitted_at for knowledge {db_obj.id}")
            
            # approved状態になった時にapproved_atとapproved_byを設定
            if new_status == StatusEnum.approved and current_status != StatusEnum.approved:
                db_obj.approved_at = datetime.utcnow()
                db_obj.approved_by = user.id
                self.logger.info(f"Set approved_at and approved_by for knowledge {db_obj.id}")
            
            # approved状態から他の状態に変更された時にapproved_atとapproved_byをクリア
            if current_status == StatusEnum.approved and new_status != StatusEnum.approved:
                db_obj.approved_at = None
                db_obj.approved_by = None
                self.logger.info(f"Cleared approved_at and approved_by for knowledge {db_obj.id}")
            
            await db.flush()
            # commitはsessionのfinallyで行う
            
            self.logger.info(f"Successfully updated knowledge status to {new_status} for knowledge {db_obj.id}")
            
            # 関連データを含めて再取得
            return await self.get(db, db_obj.id)
        except (AuthorizationError, ValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Error updating knowledge status for {db_obj.id}: {str(e)}")
            await db.rollback()
            raise DatabaseError(f"ナレッジステータスの更新中にエラーが発生しました: {str(e)}") from e
    
    async def delete(self, db: AsyncSession, id: UUID, user_id: UUID) -> bool:
        """ナレッジを削除（作成者のみ）"""
        try:
            self.logger.info(f"Attempting to delete knowledge {id} by user {user_id}")
            
            result = await db.execute(
                select(Knowledge).where(
                    and_(Knowledge.id == id, Knowledge.created_by == user_id)
                )
            )
            db_obj = result.scalar_one_or_none()
            
            if not db_obj:
                self.logger.warning(f"Knowledge {id} not found or user {user_id} is not the creator")
                return False
            
            await db.delete(db_obj)
            await db.flush()
            # commitはsessionのfinallyで行う
            
            self.logger.info(f"Successfully deleted knowledge {id}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting knowledge {id}: {str(e)}")
            await db.rollback()
            raise DatabaseError(f"ナレッジの削除中にエラーが発生しました: {str(e)}") from e


# シングルトンインスタンス
knowledge_crud = KnowledgeCRUD()
