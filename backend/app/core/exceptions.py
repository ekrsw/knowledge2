from typing import Any, Dict, Optional


class KnowledgeBaseException(Exception):
    """ナレッジベースアプリケーションの基底例外クラス"""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        self.message = message
        self.details = details or {}
        self.error_code = error_code
        super().__init__(self.message)


class ValidationError(KnowledgeBaseException):
    """バリデーションエラー"""
    pass


class NotFoundError(KnowledgeBaseException):
    """リソースが見つからないエラー"""
    pass


class DuplicateError(KnowledgeBaseException):
    """重複エラー"""
    pass


class AuthenticationError(KnowledgeBaseException):
    """認証エラー"""
    pass


class AuthorizationError(KnowledgeBaseException):
    """認可エラー"""
    pass


class DatabaseError(KnowledgeBaseException):
    """データベースエラー"""
    pass


class ExternalServiceError(KnowledgeBaseException):
    """外部サービスエラー"""
    pass


# 具体的な例外クラス
class UserNotFoundError(NotFoundError):
    """ユーザーが見つからないエラー"""
    
    def __init__(self, user_id: Optional[str] = None, username: Optional[str] = None):
        if user_id:
            message = f"ユーザーID '{user_id}' が見つかりません"
            details = {"user_id": user_id}
        elif username:
            message = f"ユーザー名 '{username}' が見つかりません"
            details = {"username": username}
        else:
            message = "ユーザーが見つかりません"
            details = {}
        
        super().__init__(message=message, details=details, error_code="USER_NOT_FOUND")


class ArticleNotFoundError(NotFoundError):
    """記事が見つからないエラー"""
    
    def __init__(self, article_number: Optional[str] = None, article_uuid: Optional[str] = None):
        if article_number:
            message = f"記事番号 '{article_number}' が見つかりません"
            details = {"article_number": article_number}
        elif article_uuid:
            message = f"記事UUID '{article_uuid}' が見つかりません"
            details = {"article_uuid": article_uuid}
        else:
            message = "記事が見つかりません"
            details = {}
        
        super().__init__(message=message, details=details, error_code="ARTICLE_NOT_FOUND")


class KnowledgeNotFoundError(NotFoundError):
    """ナレッジが見つからないエラー"""
    
    def __init__(self, knowledge_id: Optional[int] = None):
        if knowledge_id:
            message = f"ナレッジID '{knowledge_id}' が見つかりません"
            details = {"knowledge_id": knowledge_id}
        else:
            message = "ナレッジが見つかりません"
            details = {}
        
        super().__init__(message=message, details=details, error_code="KNOWLEDGE_NOT_FOUND")


class DuplicateUsernameError(DuplicateError):
    """ユーザー名重複エラー"""
    
    def __init__(self, username: str):
        message = f"ユーザー名 '{username}' は既に使用されています"
        details = {"username": username}
        super().__init__(message=message, details=details, error_code="DUPLICATE_USERNAME")


class DuplicateArticleError(DuplicateError):
    """記事重複エラー"""
    
    def __init__(self, article_number: str):
        message = f"記事番号 '{article_number}' は既に存在します"
        details = {"article_number": article_number}
        super().__init__(message=message, details=details, error_code="DUPLICATE_ARTICLE")


class InvalidCredentialsError(AuthenticationError):
    """認証情報が無効なエラー"""
    
    def __init__(self):
        message = "ユーザー名またはパスワードが正しくありません"
        super().__init__(message=message, error_code="INVALID_CREDENTIALS")


class InvalidTokenError(AuthenticationError):
    """無効なトークンエラー"""
    
    def __init__(self, token_type: str = "access"):
        message = f"無効な{token_type}トークンです"
        details = {"token_type": token_type}
        super().__init__(message=message, details=details, error_code="INVALID_TOKEN")


class InsufficientPermissionsError(AuthorizationError):
    """権限不足エラー"""
    
    def __init__(self, required_permission: Optional[str] = None):
        if required_permission:
            message = f"'{required_permission}' 権限が必要です"
            details = {"required_permission": required_permission}
        else:
            message = "権限が不足しています"
            details = {}
        
        super().__init__(message=message, details=details, error_code="INSUFFICIENT_PERMISSIONS")


class FileProcessingError(KnowledgeBaseException):
    """ファイル処理エラー"""
    
    def __init__(self, filename: str, reason: str):
        message = f"ファイル '{filename}' の処理中にエラーが発生しました: {reason}"
        details = {"filename": filename, "reason": reason}
        super().__init__(message=message, details=details, error_code="FILE_PROCESSING_ERROR")


class InvalidKnowledgeStatusError(ValidationError):
    """ナレッジのステータスが無効なエラー"""
    
    def __init__(self, knowledge_id: int, current_status: str, required_status: str):
        message = f"ナレッジID '{knowledge_id}' のステータスが '{current_status}' です。'{required_status}' である必要があります"
        details = {
            "knowledge_id": knowledge_id,
            "current_status": current_status,
            "required_status": required_status
        }
        super().__init__(message=message, details=details, error_code="INVALID_KNOWLEDGE_STATUS")

class DatabaseQueryError(Exception):
    """データベースクエリ実行エラー"""
    def __init__(self, message: str = "Database query execution error"):
        self.message = message
        super().__init__(self.message)