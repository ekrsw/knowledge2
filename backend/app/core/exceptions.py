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

class DatabaseQueryError(DatabaseError):
    """データベースクエリ実行エラー"""
    def __init__(self, message: str = "Database query execution error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, details=details, error_code="DATABASE_QUERY_ERROR")


class DatabaseConnectionError(DatabaseError):
    """データベース接続エラー"""
    def __init__(self, message: str = "Database connection error"):
        super().__init__(message=message, error_code="DATABASE_CONNECTION_ERROR")


class DatabaseIntegrityError(DatabaseError):
    """データベース整合性エラー"""
    def __init__(self, message: str, constraint: Optional[str] = None):
        details = {"constraint": constraint} if constraint else {}
        super().__init__(message=message, details=details, error_code="DATABASE_INTEGRITY_ERROR")


class TokenNotFoundError(NotFoundError):
    """トークンが見つからないエラー"""
    def __init__(self, token_type: str = "token"):
        message = f"{token_type}が見つかりません"
        details = {"token_type": token_type}
        super().__init__(message=message, details=details, error_code="TOKEN_NOT_FOUND")


class ExpiredTokenError(AuthenticationError):
    """期限切れトークンエラー"""
    def __init__(self, token_type: str = "token"):
        message = f"{token_type}の有効期限が切れています"
        details = {"token_type": token_type}
        super().__init__(message=message, details=details, error_code="EXPIRED_TOKEN")


class InvalidParameterError(ValidationError):
    """無効なパラメータエラー"""
    def __init__(self, parameter: str, value: Any, reason: str):
        message = f"パラメータ '{parameter}' の値 '{value}' が無効です: {reason}"
        details = {"parameter": parameter, "value": value, "reason": reason}
        super().__init__(message=message, details=details, error_code="INVALID_PARAMETER")


class CsvProcessingError(KnowledgeBaseException):
    """CSV処理エラー"""
    def __init__(self, row_number: Optional[int] = None, reason: str = "CSV processing failed"):
        if row_number:
            message = f"CSV行 {row_number} の処理中にエラーが発生しました: {reason}"
            details = {"row_number": row_number, "reason": reason}
        else:
            message = f"CSV処理中にエラーが発生しました: {reason}"
            details = {"reason": reason}
        super().__init__(message=message, details=details, error_code="CSV_PROCESSING_ERROR")


class ResourceLockError(KnowledgeBaseException):
    """リソースロックエラー"""
    def __init__(self, resource_type: str, resource_id: str):
        message = f"{resource_type} '{resource_id}' は他のプロセスによってロックされています"
        details = {"resource_type": resource_type, "resource_id": resource_id}
        super().__init__(message=message, details=details, error_code="RESOURCE_LOCK_ERROR")


# テストで使用する追加の例外クラス
class PermissionDeniedError(AuthorizationError):
    """権限拒否エラー"""
    def __init__(self, message: str = "権限が拒否されました"):
        super().__init__(message=message, error_code="PERMISSION_DENIED")


class InvalidStatusTransitionError(ValidationError):
    """無効なステータス遷移エラー"""
    def __init__(self, current_status: str, target_status: str):
        message = f"ステータス '{current_status}' から '{target_status}' への遷移は無効です"
        details = {"current_status": current_status, "target_status": target_status}
        super().__init__(message=message, details=details, error_code="INVALID_STATUS_TRANSITION")


class RefreshTokenNotFoundError(NotFoundError):
    """リフレッシュトークンが見つからないエラー"""
    def __init__(self, token: Optional[str] = None):
        if token:
            message = f"リフレッシュトークン '{token}' が見つかりません"
            details = {"token": token}
        else:
            message = "リフレッシュトークンが見つかりません"
            details = {}
        super().__init__(message=message, details=details, error_code="REFRESH_TOKEN_NOT_FOUND")


class TokenBlacklistNotFoundError(NotFoundError):
    """トークンブラックリストエントリが見つからないエラー"""
    def __init__(self, jti: Optional[str] = None):
        if jti:
            message = f"JTI '{jti}' のブラックリストエントリが見つかりません"
            details = {"jti": jti}
        else:
            message = "ブラックリストエントリが見つかりません"
            details = {}
        super().__init__(message=message, details=details, error_code="TOKEN_BLACKLIST_NOT_FOUND")
