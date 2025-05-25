from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime
from uuid import UUID
import time

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
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.logger.info("KnowledgeCRUD instance initialized")
    async def get(self, db: AsyncSession, id: UUID) -> Optional[Knowledge]:
        """IDでナレッジを取得"""
        start_time = time.time()
        try:
            self.logger.info(f"[GET] Starting knowledge retrieval by id: {id}")
            self.logger.debug(f"[GET] Database session state: {db.is_active}")
            
            # SQLクエリの構築ログ
            self.logger.debug(f"[GET] Building SQL query with selectinload for author and approver")
            
            result = await db.execute(
                select(Knowledge)
                .options(selectinload(Knowledge.author), selectinload(Knowledge.approver))
                .filter(Knowledge.id == id)
            )
            
            self.logger.debug(f"[GET] SQL query executed successfully")
            knowledge = result.scalar_one_or_none()
            
            execution_time = time.time() - start_time
            
            if knowledge:
                self.logger.info(f"[GET] Successfully found knowledge: id={id}, title='{knowledge.title}', status={knowledge.status}, created_by={knowledge.created_by}")
                self.logger.debug(f"[GET] Knowledge details: article_number={knowledge.article_number}, change_type={knowledge.change_type}, importance={knowledge.importance}")
                if knowledge.author:
                    self.logger.debug(f"[GET] Author loaded: {knowledge.author.username} (id={knowledge.author.id})")
                if knowledge.approver:
                    self.logger.debug(f"[GET] Approver loaded: {knowledge.approver.username} (id={knowledge.approver.id})")
                else:
                    self.logger.debug(f"[GET] No approver set for knowledge {id}")
            else:
                self.logger.warning(f"[GET] Knowledge with id {id} not found in database")
                
            self.logger.info(f"[GET] Knowledge retrieval completed in {execution_time:.3f}s")
            return knowledge
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"[GET] Error retrieving knowledge by id {id} after {execution_time:.3f}s: {str(e)}")
            self.logger.error(f"[GET] Exception type: {type(e).__name__}")
            raise DatabaseError(f"ナレッジの取得中にエラーが発生しました: {str(e)}") from e
    
    async def get_multi(
        self, 
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Knowledge]:
        """ナレッジ一覧を取得（新しい順）"""
        start_time = time.time()
        try:
            self.logger.info(f"[GET_MULTI] Starting knowledge list retrieval (skip={skip}, limit={limit})")
            self.logger.debug(f"[GET_MULTI] Database session state: {db.is_active}")
            
            # パラメータ検証
            self.logger.debug(f"[GET_MULTI] Validating parameters: skip={skip}, limit={limit}")
            if skip < 0:
                self.logger.error(f"[GET_MULTI] Invalid skip parameter: {skip} (must be >= 0)")
                raise ValidationError("skipは0以上である必要があります")
            if limit <= 0 or limit > 1000:
                self.logger.error(f"[GET_MULTI] Invalid limit parameter: {limit} (must be 1-1000)")
                raise ValidationError("limitは1以上1000以下である必要があります")
            
            self.logger.debug(f"[GET_MULTI] Parameters validated successfully")
            self.logger.debug(f"[GET_MULTI] Building SQL query with ORDER BY created_at DESC, OFFSET {skip}, LIMIT {limit}")
            
            result = await db.execute(
                select(Knowledge)
                .options(selectinload(Knowledge.author), selectinload(Knowledge.approver))
                .order_by(desc(Knowledge.created_at))
                .offset(skip)
                .limit(limit)
            )
            
            self.logger.debug(f"[GET_MULTI] SQL query executed successfully")
            knowledge_list = result.scalars().all()
            
            execution_time = time.time() - start_time
            
            self.logger.info(f"[GET_MULTI] Retrieved {len(knowledge_list)} knowledge items")
            
            # 各ナレッジの詳細ログ
            if knowledge_list:
                self.logger.debug(f"[GET_MULTI] Knowledge items summary:")
                for i, knowledge in enumerate(knowledge_list):
                    self.logger.debug(f"[GET_MULTI]   {i+1}. id={knowledge.id}, title='{knowledge.title}', status={knowledge.status}, created_by={knowledge.created_by}")
                    
                # ステータス別の集計
                status_counts = {}
                for knowledge in knowledge_list:
                    status = knowledge.status
                    status_counts[status] = status_counts.get(status, 0) + 1
                
                self.logger.info(f"[GET_MULTI] Status distribution: {dict(status_counts)}")
            else:
                self.logger.info(f"[GET_MULTI] No knowledge items found with skip={skip}, limit={limit}")
            
            self.logger.info(f"[GET_MULTI] Knowledge list retrieval completed in {execution_time:.3f}s")
            return knowledge_list
            
        except ValidationError as e:
            execution_time = time.time() - start_time
            self.logger.warning(f"[GET_MULTI] Validation error after {execution_time:.3f}s: {str(e)}")
            raise
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"[GET_MULTI] Error retrieving knowledge list after {execution_time:.3f}s: {str(e)}")
            self.logger.error(f"[GET_MULTI] Exception type: {type(e).__name__}")
            raise DatabaseError(f"ナレッジ一覧の取得中にエラーが発生しました: {str(e)}") from e
    
    async def get_by_status(
        self, 
        db: AsyncSession, 
        status: StatusEnum, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Knowledge]:
        """ステータス別ナレッジ一覧を取得"""
        start_time = time.time()
        try:
            self.logger.info(f"[GET_BY_STATUS] Starting knowledge retrieval by status: {status} (skip={skip}, limit={limit})")
            self.logger.debug(f"[GET_BY_STATUS] Database session state: {db.is_active}")
            
            # パラメータ検証
            self.logger.debug(f"[GET_BY_STATUS] Validating parameters")
            if skip < 0:
                self.logger.error(f"[GET_BY_STATUS] Invalid skip parameter: {skip} (must be >= 0)")
                raise ValidationError("skipは0以上である必要があります")
            if limit <= 0 or limit > 1000:
                self.logger.error(f"[GET_BY_STATUS] Invalid limit parameter: {limit} (must be 1-1000)")
                raise ValidationError("limitは1以上1000以下である必要があります")
            
            self.logger.debug(f"[GET_BY_STATUS] Building SQL query with WHERE status = {status}")
            result = await db.execute(
                select(Knowledge)
                .options(selectinload(Knowledge.author), selectinload(Knowledge.approver))
                .where(Knowledge.status == status)
                .order_by(desc(Knowledge.created_at))
                .offset(skip)
                .limit(limit)
            )
            
            knowledge_list = result.scalars().all()
            execution_time = time.time() - start_time
            
            self.logger.info(f"[GET_BY_STATUS] Retrieved {len(knowledge_list)} knowledge items with status {status}")
            
            if knowledge_list:
                self.logger.debug(f"[GET_BY_STATUS] Knowledge items with status {status}:")
                for i, knowledge in enumerate(knowledge_list):
                    self.logger.debug(f"[GET_BY_STATUS]   {i+1}. id={knowledge.id}, title='{knowledge.title}', created_by={knowledge.created_by}")
            
            self.logger.info(f"[GET_BY_STATUS] Status-based retrieval completed in {execution_time:.3f}s")
            return knowledge_list
            
        except ValidationError as e:
            execution_time = time.time() - start_time
            self.logger.warning(f"[GET_BY_STATUS] Validation error after {execution_time:.3f}s: {str(e)}")
            raise
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"[GET_BY_STATUS] Error retrieving knowledge by status {status} after {execution_time:.3f}s: {str(e)}")
            self.logger.error(f"[GET_BY_STATUS] Exception type: {type(e).__name__}")
            raise DatabaseError(f"ステータス別ナレッジ一覧の取得中にエラーが発生しました: {str(e)}") from e
    
    async def get_by_user(
        self, 
        db: AsyncSession, 
        user_id: UUID, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Knowledge]:
        """特定ユーザーのナレッジ一覧を取得"""
        start_time = time.time()
        try:
            self.logger.info(f"[GET_BY_USER] Starting knowledge retrieval by user: {user_id} (skip={skip}, limit={limit})")
            self.logger.debug(f"[GET_BY_USER] Database session state: {db.is_active}")
            
            # パラメータ検証
            self.logger.debug(f"[GET_BY_USER] Validating parameters")
            if skip < 0:
                self.logger.error(f"[GET_BY_USER] Invalid skip parameter: {skip} (must be >= 0)")
                raise ValidationError("skipは0以上である必要があります")
            if limit <= 0 or limit > 1000:
                self.logger.error(f"[GET_BY_USER] Invalid limit parameter: {limit} (must be 1-1000)")
                raise ValidationError("limitは1以上1000以下である必要があります")
            
            self.logger.debug(f"[GET_BY_USER] Building SQL query with WHERE created_by = {user_id}")
            result = await db.execute(
                select(Knowledge)
                .options(selectinload(Knowledge.author), selectinload(Knowledge.approver))
                .where(Knowledge.created_by == user_id)
                .order_by(desc(Knowledge.created_at))
                .offset(skip)
                .limit(limit)
            )
            
            knowledge_list = result.scalars().all()
            execution_time = time.time() - start_time
            
            self.logger.info(f"[GET_BY_USER] Retrieved {len(knowledge_list)} knowledge items for user {user_id}")
            
            if knowledge_list:
                self.logger.debug(f"[GET_BY_USER] Knowledge items for user {user_id}:")
                status_counts = {}
                for i, knowledge in enumerate(knowledge_list):
                    self.logger.debug(f"[GET_BY_USER]   {i+1}. id={knowledge.id}, title='{knowledge.title}', status={knowledge.status}")
                    status = knowledge.status
                    status_counts[status] = status_counts.get(status, 0) + 1
                
                self.logger.info(f"[GET_BY_USER] User's knowledge status distribution: {dict(status_counts)}")
            
            self.logger.info(f"[GET_BY_USER] User-based retrieval completed in {execution_time:.3f}s")
            return knowledge_list
            
        except ValidationError as e:
            execution_time = time.time() - start_time
            self.logger.warning(f"[GET_BY_USER] Validation error after {execution_time:.3f}s: {str(e)}")
            raise
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"[GET_BY_USER] Error retrieving knowledge by user {user_id} after {execution_time:.3f}s: {str(e)}")
            self.logger.error(f"[GET_BY_USER] Exception type: {type(e).__name__}")
            raise DatabaseError(f"ユーザー別ナレッジ一覧の取得中にエラーが発生しました: {str(e)}") from e
    
    async def get_by_article(
        self, 
        db: AsyncSession, 
        article_number: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Knowledge]:
        """特定記事に対するナレッジ一覧を取得"""
        start_time = time.time()
        try:
            self.logger.info(f"[GET_BY_ARTICLE] Starting knowledge retrieval by article: {article_number} (skip={skip}, limit={limit})")
            self.logger.debug(f"[GET_BY_ARTICLE] Database session state: {db.is_active}")
            
            # パラメータ検証
            self.logger.debug(f"[GET_BY_ARTICLE] Validating parameters")
            if not article_number or not article_number.strip():
                self.logger.error(f"[GET_BY_ARTICLE] Invalid article_number: '{article_number}' (must not be empty)")
                raise ValidationError("記事番号は必須です")
            if skip < 0:
                self.logger.error(f"[GET_BY_ARTICLE] Invalid skip parameter: {skip} (must be >= 0)")
                raise ValidationError("skipは0以上である必要があります")
            if limit <= 0 or limit > 1000:
                self.logger.error(f"[GET_BY_ARTICLE] Invalid limit parameter: {limit} (must be 1-1000)")
                raise ValidationError("limitは1以上1000以下である必要があります")
            
            self.logger.debug(f"[GET_BY_ARTICLE] Building SQL query with WHERE article_number = '{article_number}'")
            result = await db.execute(
                select(Knowledge)
                .options(selectinload(Knowledge.author), selectinload(Knowledge.approver))
                .where(Knowledge.article_number == article_number)
                .order_by(desc(Knowledge.created_at))
                .offset(skip)
                .limit(limit)
            )
            
            knowledge_list = result.scalars().all()
            execution_time = time.time() - start_time
            
            self.logger.info(f"[GET_BY_ARTICLE] Retrieved {len(knowledge_list)} knowledge items for article {article_number}")
            
            if knowledge_list:
                self.logger.debug(f"[GET_BY_ARTICLE] Knowledge items for article {article_number}:")
                status_counts = {}
                change_type_counts = {}
                for i, knowledge in enumerate(knowledge_list):
                    self.logger.debug(f"[GET_BY_ARTICLE]   {i+1}. id={knowledge.id}, title='{knowledge.title}', status={knowledge.status}, change_type={knowledge.change_type}")
                    status = knowledge.status
                    change_type = knowledge.change_type
                    status_counts[status] = status_counts.get(status, 0) + 1
                    change_type_counts[change_type] = change_type_counts.get(change_type, 0) + 1
                
                self.logger.info(f"[GET_BY_ARTICLE] Article's knowledge status distribution: {dict(status_counts)}")
                self.logger.info(f"[GET_BY_ARTICLE] Article's knowledge change type distribution: {dict(change_type_counts)}")
            
            self.logger.info(f"[GET_BY_ARTICLE] Article-based retrieval completed in {execution_time:.3f}s")
            return knowledge_list
            
        except ValidationError as e:
            execution_time = time.time() - start_time
            self.logger.warning(f"[GET_BY_ARTICLE] Validation error after {execution_time:.3f}s: {str(e)}")
            raise
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"[GET_BY_ARTICLE] Error retrieving knowledge by article {article_number} after {execution_time:.3f}s: {str(e)}")
            self.logger.error(f"[GET_BY_ARTICLE] Exception type: {type(e).__name__}")
            raise DatabaseError(f"記事別ナレッジ一覧の取得中にエラーが発生しました: {str(e)}") from e
    
    async def create(
        self, 
        db: AsyncSession, 
        obj_in: KnowledgeCreate, 
        user_id: UUID
    ) -> Knowledge:
        """新しいナレッジを作成"""
        start_time = time.time()
        try:
            self.logger.info(f"[CREATE] Starting knowledge creation by user: {user_id}")
            self.logger.debug(f"[CREATE] Database session state: {db.is_active}")
            
            # 入力データの詳細ログ
            self.logger.info(f"[CREATE] Knowledge data: title='{obj_in.title}', article_number='{obj_in.article_number}', change_type={obj_in.change_type}")
            self.logger.debug(f"[CREATE] Additional data: info_category='{obj_in.info_category}', importance={obj_in.importance}, target='{obj_in.target}'")
            self.logger.debug(f"[CREATE] Keywords: {obj_in.keywords}")
            self.logger.debug(f"[CREATE] Publish period: {obj_in.open_publish_start} to {obj_in.open_publish_end}")
            
            if obj_in.question:
                self.logger.debug(f"[CREATE] Question length: {len(obj_in.question)} characters")
            if obj_in.answer:
                self.logger.debug(f"[CREATE] Answer length: {len(obj_in.answer)} characters")
            if obj_in.add_comments:
                self.logger.debug(f"[CREATE] Additional comments length: {len(obj_in.add_comments)} characters")
            if obj_in.remarks:
                self.logger.debug(f"[CREATE] Remarks length: {len(obj_in.remarks)} characters")
            
            # 記事番号の存在チェックは呼び出し元で行う
            self.logger.debug(f"[CREATE] Creating Knowledge model instance")
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
            
            self.logger.debug(f"[CREATE] Adding knowledge to database session")
            db.add(db_obj)
            
            self.logger.debug(f"[CREATE] Flushing database session")
            await db.flush()
            
            execution_time = time.time() - start_time
            
            self.logger.info(f"[CREATE] Successfully created knowledge with id: {db_obj.id}")
            self.logger.debug(f"[CREATE] Generated knowledge ID: {db_obj.id}")
            self.logger.debug(f"[CREATE] Default status set to: {db_obj.status}")
            self.logger.debug(f"[CREATE] Created at: {db_obj.created_at}")
            
            self.logger.debug(f"[CREATE] Retrieving created knowledge with related data")
            # 関連データを含めて再取得
            result = await self.get(db, db_obj.id)
            
            total_time = time.time() - start_time
            self.logger.info(f"[CREATE] Knowledge creation completed in {total_time:.3f}s (flush: {execution_time:.3f}s)")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"[CREATE] Error creating knowledge after {execution_time:.3f}s: {str(e)}")
            self.logger.error(f"[CREATE] Exception type: {type(e).__name__}")
            self.logger.error(f"[CREATE] Failed data: title='{obj_in.title}', user_id={user_id}")
            raise DatabaseError(f"ナレッジの作成中にエラーが発生しました: {str(e)}") from e
    
    async def update(
        self, 
        db: AsyncSession, 
        db_obj: Knowledge, 
        obj_in: KnowledgeUpdate
    ) -> Knowledge:
        """ナレッジを更新"""
        start_time = time.time()
        try:
            self.logger.info(f"[UPDATE] Starting knowledge update for id: {db_obj.id}")
            self.logger.debug(f"[UPDATE] Database session state: {db.is_active}")
            self.logger.debug(f"[UPDATE] Current knowledge: title='{db_obj.title}', status={db_obj.status}")
            
            update_data = obj_in.dict(exclude_unset=True)
            
            if not update_data:
                self.logger.warning(f"[UPDATE] No update data provided for knowledge {db_obj.id}")
                return db_obj
            
            self.logger.info(f"[UPDATE] Updating {len(update_data)} fields: {list(update_data.keys())}")
            
            # 更新前の値をログ出力
            old_values = {}
            for field in update_data.keys():
                if hasattr(db_obj, field):
                    old_values[field] = getattr(db_obj, field)
            
            self.logger.debug(f"[UPDATE] Old values: {old_values}")
            self.logger.debug(f"[UPDATE] New values: {update_data}")
            
            # フィールドごとの更新ログ
            for field, value in update_data.items():
                old_value = getattr(db_obj, field, None)
                setattr(db_obj, field, value)
                self.logger.debug(f"[UPDATE] Field '{field}': '{old_value}' -> '{value}'")
            
            self.logger.debug(f"[UPDATE] Flushing database session")
            await db.flush()
            
            self.logger.debug(f"[UPDATE] Refreshing knowledge object")
            await db.refresh(db_obj)
            
            execution_time = time.time() - start_time
            
            self.logger.info(f"[UPDATE] Successfully updated knowledge with id: {db_obj.id}")
            self.logger.debug(f"[UPDATE] Updated at: {db_obj.updated_at}")
            
            self.logger.debug(f"[UPDATE] Retrieving updated knowledge with related data")
            # 関連データを含めて再取得
            result = await self.get(db, db_obj.id)
            
            total_time = time.time() - start_time
            self.logger.info(f"[UPDATE] Knowledge update completed in {total_time:.3f}s (flush: {execution_time:.3f}s)")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"[UPDATE] Error updating knowledge {db_obj.id} after {execution_time:.3f}s: {str(e)}")
            self.logger.error(f"[UPDATE] Exception type: {type(e).__name__}")
            self.logger.error(f"[UPDATE] Failed update data: {update_data}")
            
            raise DatabaseError(f"ナレッジの更新中にエラーが発生しました: {str(e)}") from e
    
    async def update_status(
        self, 
        db: AsyncSession, 
        db_obj: Knowledge, 
        new_status: StatusEnum, 
        user: User
    ) -> Knowledge:
        """ナレッジのステータスを更新（権限チェック付き）"""
        start_time = time.time()
        try:
            current_status = db_obj.status
            self.logger.info(f"[UPDATE_STATUS] Starting status update from {current_status} to {new_status} for knowledge {db_obj.id} by user {user.id}")
            self.logger.debug(f"[UPDATE_STATUS] Database session state: {db.is_active}")
            self.logger.debug(f"[UPDATE_STATUS] Knowledge details: title='{db_obj.title}', created_by={db_obj.created_by}")
            self.logger.debug(f"[UPDATE_STATUS] User details: username='{user.username}', is_admin={user.is_admin}")
            
            # 権限チェック
            self.logger.debug(f"[UPDATE_STATUS] Performing authorization check")
            if user.is_admin:
                # 管理者は全てのステータス変更を許可
                self.logger.info(f"[UPDATE_STATUS] Admin user {user.id} ({user.username}) authorized for status change")
            elif db_obj.created_by == user.id:
                # 作成者は draft → submitted, submitted → draft のみ許可
                self.logger.debug(f"[UPDATE_STATUS] Creator authorization check: current={current_status}, new={new_status}")
                if not ((current_status == StatusEnum.draft and new_status == StatusEnum.submitted) or
                       (current_status == StatusEnum.submitted and new_status == StatusEnum.draft)):
                    self.logger.warning(f"[UPDATE_STATUS] Unauthorized status change attempt by creator {user.id} for knowledge {db_obj.id}")
                    self.logger.warning(f"[UPDATE_STATUS] Invalid transition: {current_status} -> {new_status}")
                    raise AuthorizationError(f"ステータスの変更権限がありません。現在のステータス: {current_status}, 変更先: {new_status}")
                else:
                    self.logger.info(f"[UPDATE_STATUS] Creator {user.id} ({user.username}) authorized for status change")
            else:
                # その他のユーザーは変更不可
                self.logger.warning(f"[UPDATE_STATUS] Unauthorized status change attempt by user {user.id} for knowledge {db_obj.id}")
                self.logger.warning(f"[UPDATE_STATUS] User {user.id} is neither admin nor creator (created_by={db_obj.created_by})")
                raise AuthorizationError("このナレッジのステータスを変更する権限がありません")
            
            self.logger.debug(f"[UPDATE_STATUS] Authorization successful, updating status")
            db_obj.status = new_status
            
            # submitted状態になった時にsubmitted_atを設定
            if new_status == StatusEnum.submitted and current_status != StatusEnum.submitted:
                submitted_time = datetime.utcnow()
                db_obj.submitted_at = submitted_time
                self.logger.info(f"[UPDATE_STATUS] Set submitted_at to {submitted_time} for knowledge {db_obj.id}")
            
            # approved状態になった時にapproved_atとapproved_byを設定
            if new_status == StatusEnum.approved and current_status != StatusEnum.approved:
                approved_time = datetime.utcnow()
                db_obj.approved_at = approved_time
                db_obj.approved_by = user.id
                self.logger.info(f"[UPDATE_STATUS] Set approved_at to {approved_time} and approved_by to {user.id} for knowledge {db_obj.id}")
            
            # approved状態から他の状態に変更された時にapproved_atとapproved_byをクリア
            if current_status == StatusEnum.approved and new_status != StatusEnum.approved:
                db_obj.approved_at = None
                db_obj.approved_by = None
                self.logger.info(f"[UPDATE_STATUS] Cleared approved_at and approved_by for knowledge {db_obj.id}")
            
            self.logger.debug(f"[UPDATE_STATUS] Flushing database session")
            await db.flush()
            # commitはsessionのfinallyで行う
            
            execution_time = time.time() - start_time
            
            self.logger.info(f"[UPDATE_STATUS] Successfully updated knowledge status to {new_status} for knowledge {db_obj.id}")
            self.logger.debug(f"[UPDATE_STATUS] Status update completed, retrieving updated knowledge")
            
            # 関連データを含めて再取得
            result = await self.get(db, db_obj.id)
            
            total_time = time.time() - start_time
            self.logger.info(f"[UPDATE_STATUS] Status update completed in {total_time:.3f}s (flush: {execution_time:.3f}s)")
            
            return result
            
        except (AuthorizationError, ValidationError) as e:
            execution_time = time.time() - start_time
            self.logger.warning(f"[UPDATE_STATUS] Authorization/Validation error after {execution_time:.3f}s: {str(e)}")
            raise
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"[UPDATE_STATUS] Error updating knowledge status for {db_obj.id} after {execution_time:.3f}s: {str(e)}")
            self.logger.error(f"[UPDATE_STATUS] Exception type: {type(e).__name__}")
            
            raise DatabaseError(f"ナレッジステータスの更新中にエラーが発生しました: {str(e)}") from e
    
    async def delete(self, db: AsyncSession, id: UUID, user_id: UUID) -> bool:
        """ナレッジを削除（作成者のみ）"""
        start_time = time.time()
        try:
            self.logger.info(f"[DELETE] Starting knowledge deletion: id={id} by user={user_id}")
            self.logger.debug(f"[DELETE] Database session state: {db.is_active}")
            
            self.logger.debug(f"[DELETE] Building SQL query to find knowledge with creator check")
            result = await db.execute(
                select(Knowledge).where(
                    and_(Knowledge.id == id, Knowledge.created_by == user_id)
                )
            )
            
            db_obj = result.scalar_one_or_none()
            
            if not db_obj:
                execution_time = time.time() - start_time
                self.logger.warning(f"[DELETE] Knowledge {id} not found or user {user_id} is not the creator")
                self.logger.info(f"[DELETE] Delete operation completed (not found) in {execution_time:.3f}s")
                return False
            
            # 削除前の詳細ログ
            self.logger.info(f"[DELETE] Found knowledge to delete: title='{db_obj.title}', status={db_obj.status}, article_number={db_obj.article_number}")
            self.logger.debug(f"[DELETE] Knowledge details: created_at={db_obj.created_at}, updated_at={db_obj.updated_at}")
            
            self.logger.debug(f"[DELETE] Marking knowledge for deletion")
            await db.delete(db_obj)
            
            self.logger.debug(f"[DELETE] Flushing database session")
            await db.flush()
            
            execution_time = time.time() - start_time
            
            self.logger.info(f"[DELETE] Successfully deleted knowledge {id}")
            self.logger.info(f"[DELETE] Delete operation completed in {execution_time:.3f}s")
            return True
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"[DELETE] Error deleting knowledge {id} after {execution_time:.3f}s: {str(e)}")
            self.logger.error(f"[DELETE] Exception type: {type(e).__name__}")
            self.logger.error(f"[DELETE] Failed deletion: id={id}, user_id={user_id}")
            
            raise DatabaseError(f"ナレッジの削除中にエラーが発生しました: {str(e)}") from e


# シングルトンインスタンス
knowledge_crud = KnowledgeCRUD()
