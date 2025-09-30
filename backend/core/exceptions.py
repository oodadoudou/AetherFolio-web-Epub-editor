"""自定义异常模块"""

from typing import Optional, Dict, Any


class AetherFolioException(Exception):
    """AetherFolio 基础异常类"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details
        }


class FileValidationError(AetherFolioException):
    """文件验证异常"""
    
    def __init__(self, message: str, filename: Optional[str] = None, validation_errors: Optional[list] = None):
        details = {}
        if filename:
            details["filename"] = filename
        if validation_errors:
            details["validation_errors"] = validation_errors
        
        super().__init__(message, "FILE_VALIDATION_ERROR", details)


class FileProcessingError(AetherFolioException):
    """文件处理异常"""
    
    def __init__(self, message: str, filename: Optional[str] = None, operation: Optional[str] = None):
        details = {}
        if filename:
            details["filename"] = filename
        if operation:
            details["operation"] = operation
        
        super().__init__(message, "FILE_PROCESSING_ERROR", details)


class SessionError(AetherFolioException):
    """会话异常"""
    
    def __init__(self, message: str, session_id: Optional[str] = None):
        details = {}
        if session_id:
            details["session_id"] = session_id
        
        super().__init__(message, "SESSION_ERROR", details)


class AuthenticationError(AetherFolioException):
    """认证异常"""
    
    def __init__(self, message: str, username: Optional[str] = None):
        details = {}
        if username:
            details["username"] = username
        
        super().__init__(message, "AUTHENTICATION_ERROR", details)


class AuthorizationError(AetherFolioException):
    """授权异常"""
    
    def __init__(self, message: str, user_id: Optional[str] = None, required_permission: Optional[str] = None):
        details = {}
        if user_id:
            details["user_id"] = user_id
        if required_permission:
            details["required_permission"] = required_permission
        
        super().__init__(message, "AUTHORIZATION_ERROR", details)


class DatabaseError(AetherFolioException):
    """数据库异常"""
    
    def __init__(self, message: str, operation: Optional[str] = None, table: Optional[str] = None):
        details = {}
        if operation:
            details["operation"] = operation
        if table:
            details["table"] = table
        
        super().__init__(message, "DATABASE_ERROR", details)


class ConfigurationError(AetherFolioException):
    """配置异常"""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        details = {}
        if config_key:
            details["config_key"] = config_key
        
        super().__init__(message, "CONFIGURATION_ERROR", details)


class ValidationError(AetherFolioException):
    """验证异常"""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        
        super().__init__(message, "VALIDATION_ERROR", details)


class BusinessLogicError(AetherFolioException):
    """业务逻辑异常"""
    
    def __init__(self, message: str, operation: Optional[str] = None):
        details = {}
        if operation:
            details["operation"] = operation
        
        super().__init__(message, "BUSINESS_LOGIC_ERROR", details)


class ExternalServiceError(AetherFolioException):
    """外部服务异常"""
    
    def __init__(self, message: str, service: Optional[str] = None, status_code: Optional[int] = None):
        details = {}
        if service:
            details["service"] = service
        if status_code:
            details["status_code"] = status_code
        
        super().__init__(message, "EXTERNAL_SERVICE_ERROR", details)


class RateLimitError(AetherFolioException):
    """速率限制异常"""
    
    def __init__(self, message: str, limit: Optional[int] = None, window: Optional[int] = None):
        details = {}
        if limit:
            details["limit"] = limit
        if window:
            details["window"] = window
        
        super().__init__(message, "RATE_LIMIT_ERROR", details)


class ResourceNotFoundError(AetherFolioException):
    """资源未找到异常"""
    
    def __init__(self, message: str, resource_type: Optional[str] = None, resource_id: Optional[str] = None):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        
        super().__init__(message, "RESOURCE_NOT_FOUND_ERROR", details)


class ConcurrencyError(AetherFolioException):
    """并发异常"""
    
    def __init__(self, message: str, resource: Optional[str] = None):
        details = {}
        if resource:
            details["resource"] = resource
        
        super().__init__(message, "CONCURRENCY_ERROR", details)


class SecurityError(AetherFolioException):
    """安全异常"""
    
    def __init__(self, message: str, violation_type: Optional[str] = None, ip_address: Optional[str] = None):
        details = {}
        if violation_type:
            details["violation_type"] = violation_type
        if ip_address:
            details["ip_address"] = ip_address
        
        super().__init__(message, "SECURITY_ERROR", details)