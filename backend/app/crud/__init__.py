# CRUD操作のインポート
from app.crud.user import user_crud
from app.crud.article import article_crud
from app.crud.knowledge import knowledge_crud

# すべてのCRUDをエクスポート
__all__ = [
    "user_crud",
    "article_crud", 
    "knowledge_crud"
]