"""自定义异常类"""

from typing import Optional, Dict, Any


class BaseAppException(Exception):
    """应用基础异常类"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details
        }


class ConfigurationError(BaseAppException):
    """配置错误"""
    pass


class SecurityError(BaseAppException):
    """安全相关错误"""
    pass


class FileValidationError(BaseAppException):
    """文件验证错误"""
    pass


class ContentValidationError(BaseAppException):
    """内容验证错误"""
    pass


class RateLimitError(BaseAppException):
    """速率限制错误"""
    pass


class SessionError(BaseAppException):
    """会话相关错误"""
    pass


class EpubError(BaseAppException):
    """EPUB处理错误"""
    pass


class RateLimitError(BaseAppException):
    """速率限制错误"""
    pass


class ReplaceError(BaseAppException):
    """替换操作错误"""
    pass


class FileOperationError(BaseAppException):
    """文件操作错误"""
    pass


class ValidationError(BaseAppException):
    """验证错误"""
    pass


class ProcessingError(BaseAppException):
    """处理错误"""
    pass


class ExportError(BaseAppException):
    """导出错误"""
    pass


class ImportError(BaseAppException):
    """导入错误"""
    pass


class DatabaseError(BaseAppException):
    """数据库错误"""
    pass


class CacheError(BaseAppException):
    """缓存错误"""
    pass


class NetworkError(BaseAppException):
    """网络错误"""
    pass


class TimeoutError(BaseAppException):
    """超时错误"""
    pass


class PermissionError(BaseAppException):
    """权限错误"""
    pass


class ResourceNotFoundError(BaseAppException):
    """资源未找到错误"""
    pass


class ResourceExistsError(BaseAppException):
    """资源已存在错误"""
    pass


class QuotaExceededError(BaseAppException):
    """配额超出错误"""
    pass


class ServiceUnavailableError(BaseAppException):
    """服务不可用错误"""
    pass


class MaintenanceError(BaseAppException):
    """维护模式错误"""
    pass