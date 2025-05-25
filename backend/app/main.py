from app.crud.user import user_crud
from app.crud.knowledge import knowledge_crud
from app.models.user import User
from app.models.knowledge import ChangeTypeEnum, StatusEnum
from app.schemas.user import UserCreate, UserUpdate
from app.schemas.knowledge import Knowledge, KnowledgeCreate, KnowledgeUpdate
from app.db.session import get_async_session
from app.db.init import Database
from app.core.exceptions import UserNotFoundError, KnowledgeNotFoundError
import asyncio
from datetime import date

async def main():
    # データベースの初期化
    db_manager = Database()
    await db_manager.init()
    
    # ユーザー作成
    async for db in get_async_session():
        user_obj_in = UserCreate(
            username="test_user",
            full_name="テストユーザー",
            password="password123"
        )
        new_user = await user_crud.create(db, user_obj_in)
        user_id = new_user.id  # IDを保存
        print(f"Created user: {new_user.username}")
        break

    # ユーザー更新
    async for db in get_async_session():
        db_obj = await user_crud.get(db, user_id)
        obj_in = UserUpdate(
            username="new_username"
        )
        updated_user = await user_crud.update(db, db_obj, obj_in)
        print(f"Updated user: {updated_user.username}")
        updated_user_from_db = await user_crud.get(db, user_id)
        print(f"User from DB: {updated_user_from_db.username}")
        break

    print("\n=== Knowledge CRUD Operations ===")
    
    # Knowledge作成
    async for db in get_async_session():
        knowledge_obj_in = KnowledgeCreate(
            article_number="KBA-00001-TEST",
            change_type=ChangeTypeEnum.modify,
            title="テストナレッジ",
            info_category="技術情報",
            keywords="Python, FastAPI, SQLAlchemy",
            importance=True,
            target="開発者",
            open_publish_start=date(2024, 1, 1),
            open_publish_end=date(2024, 12, 31),
            question="FastAPIでの非同期処理について",
            answer="async/awaitを使用して非同期処理を実装します。",
            add_comments="追加のコメント",
            remarks="備考欄"
        )
        new_knowledge = await knowledge_crud.create(db, knowledge_obj_in, user_id)
        knowledge_id = new_knowledge.id  # IDを保存
        print(f"Created knowledge: {new_knowledge.title}")
        print(f"Knowledge ID: {knowledge_id}")
        print(f"Status: {new_knowledge.status}")
        break

    # Knowledge取得
    async for db in get_async_session():
        retrieved_knowledge = await knowledge_crud.get(db, knowledge_id)
        print(f"Retrieved knowledge: {retrieved_knowledge.title}")
        print(f"Author: {retrieved_knowledge.author.username}")
        print(f"Article Number: {retrieved_knowledge.article_number}")
        break

    # Knowledge更新
    async for db in get_async_session():
        knowledge_db_obj = await knowledge_crud.get(db, knowledge_id)
        knowledge_update_obj = KnowledgeUpdate(
            title="更新されたテストナレッジ",
            info_category="更新された技術情報",
            importance=False
        )
        updated_knowledge = await knowledge_crud.update(db, knowledge_db_obj, knowledge_update_obj)
        print(f"Updated knowledge: {updated_knowledge.title}")
        print(f"Updated importance: {updated_knowledge.importance}")
        break

    # Knowledgeステータス更新
    async for db in get_async_session():
        knowledge_db_obj = await knowledge_crud.get(db, knowledge_id)
        user_obj = await user_crud.get(db, user_id)
        status_updated_knowledge = await knowledge_crud.update_status(
            db, knowledge_db_obj, StatusEnum.submitted, user_obj
        )
        print(f"Status updated to: {status_updated_knowledge.status}")
        print(f"Submitted at: {status_updated_knowledge.submitted_at}")
        break

    # Knowledge一覧取得
    async for db in get_async_session():
        knowledge_list = await knowledge_crud.get_multi(db, skip=0, limit=10)
        print(f"Total knowledge items: {len(knowledge_list)}")
        for knowledge in knowledge_list:
            print(f"- {knowledge.title} (Status: {knowledge.status})")
        break

    # ユーザー削除
    async for db in get_async_session():
        await user_crud.delete(db, user_id)
        print("User deleted")
        break

    # Knowledge削除
    async for db in get_async_session():
        # 注意: ユーザーが削除されているため、この操作は失敗する可能性があります
        # 実際のアプリケーションでは、外部キー制約を適切に設定する必要があります
        try:
            deleted = await knowledge_crud.delete(db, knowledge_id, user_id)
            if deleted:
                print("Knowledge deleted successfully")
            else:
                print("Knowledge deletion failed")
        except Exception as e:
            print(f"Knowledge deletion error: {e}")
        break

    # 削除確認
    async for db in get_async_session():
        try:
            existing_user = await user_crud.get(db, user_id)
            print(existing_user.username)
        except UserNotFoundError:
            print("OK - User not found after deletion")
        
        try:
            existing_knowledge = await knowledge_crud.get(db, knowledge_id)
            print(f"Knowledge still exists: {existing_knowledge.title}")
        except KnowledgeNotFoundError:
            print("OK - Knowledge not found after deletion")
        except Exception as e:
            print(f"Knowledge check error: {e}")
        break


if __name__ == "__main__":
    asyncio.run(main())
