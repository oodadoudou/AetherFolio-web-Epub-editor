"""日志配置模块"""

import logging
import logging.config
import sys
import time
from typing import Dict, Any
from pathlib import Path
from pythonjsonlogger import jsonlogger
from backend.core.config import settings


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """自定义JSON格式化器"""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]):
        """添加自定义字段"""
        super().add_fields(log_record, record, message_dict)
        
        # 添加时间戳
        log_record['timestamp'] = time.time()
        
        # 添加应用信息
        log_record['app_name'] = settings.app_name
        log_record['app_version'] = settings.app_version
        
        # 添加环境信息
        log_record['environment'] = 'development' if settings.debug else 'production'
        
        # 添加进程信息
        import os
        log_record['process_id'] = os.getpid()
        
        # 格式化级别名称
        log_record['level'] = record.levelname
        
        # 添加模块信息
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line_number'] = record.lineno


class PerformanceLogger:
    """性能日志记录器"""
    
    def __init__(self, logger_name: str = "performance"):
        self.logger = logging.getLogger(logger_name)
    
    def log_request_time(self, method: str, path: str, duration: float, status_code: int):
        """记录请求处理时间"""
        self.logger.info(
            "Request processed",
            extra={
                "request_method": method,
                "request_path": path,
                "duration_ms": round(duration * 1000, 2),
                "status_code": status_code,
                "event_type": "request_performance"
            }
        )
    
    def log_slow_request(self, method: str, path: str, duration: float, threshold: float = 1.0):
        """记录慢请求"""
        if duration > threshold:
            self.logger.warning(
                "Slow request detected",
                extra={
                    "request_method": method,
                    "request_path": path,
                    "duration_ms": round(duration * 1000, 2),
                    "threshold_ms": round(threshold * 1000, 2),
                    "event_type": "slow_request"
                }
            )
    
    def log_operation_time(self, operation: str, duration: float, **kwargs):
        """记录操作处理时间"""
        self.logger.info(
            f"Operation '{operation}' completed",
            extra={
                "operation": operation,
                "duration_ms": round(duration * 1000, 2),
                "event_type": "operation_performance",
                **kwargs
            }
        )
    
    def async_timer(self, operation: str):
        """异步计时器上下文管理器"""
        from contextlib import asynccontextmanager
        import time
        
        @asynccontextmanager
        async def timer():
            start_time = time.time()
            try:
                yield
            finally:
                duration = time.time() - start_time
                self.log_operation_time(operation, duration)
        
        return timer()
    
    def get_current_time(self):
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()


class SecurityLogger:
    """安全日志记录器"""
    
    def __init__(self, logger_name: str = "security"):
        self.logger = logging.getLogger(logger_name)
    
    def log_file_upload(self, filename: str, file_size: int, client_ip: str, success: bool = True):
        """记录文件上传事件"""
        level = logging.INFO if success else logging.WARNING
        self.logger.log(
            level,
            "File upload attempt",
            extra={
                "file_name": filename,
                "file_size": file_size,
                "client_ip": client_ip,
                "success": success,
                "event_type": "file_upload"
            }
        )
    
    def log_security_violation(self, violation_type: str, details: str, client_ip: str):
        """记录安全违规事件"""
        self.logger.error(
            "Security violation detected",
            extra={
                "violation_type": violation_type,
                "details": details,
                "client_ip": client_ip,
                "event_type": "security_violation"
            }
        )
    
    def log_rate_limit_exceeded(self, client_ip: str, endpoint: str, limit: str):
        """记录速率限制超出事件"""
        self.logger.warning(
            "Rate limit exceeded",
            extra={
                "client_ip": client_ip,
                "endpoint": endpoint,
                "limit": limit,
                "event_type": "rate_limit_exceeded"
            }
        )
    
    def log_info(self, message: str, **kwargs):
        """记录信息级别日志"""
        self.logger.info(
            message,
            extra={
                "event_type": "info",
                **kwargs
            }
        )
    
    def log_error(self, message: str, error: Exception = None, **kwargs):
        """记录错误级别日志"""
        extra_data = {
            "event_type": "error",
            **kwargs
        }
        if error:
            extra_data["error_type"] = type(error).__name__
            extra_data["error_message"] = str(error)
        
        self.logger.error(
            message,
            extra=extra_data
        )
    
    def log_warning(self, message: str, **kwargs):
        """记录警告级别日志"""
        self.logger.warning(
            message,
            extra={
                "event_type": "warning",
                **kwargs
            }
        )


def setup_logging():
    """设置日志配置"""
    
    # 创建日志目录
    if settings.log_file:
        log_dir = Path(settings.log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
    
    # 日志配置
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": CustomJsonFormatter,
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
            },
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "detailed": {
                "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(funcName)s(): %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.log_level,
                "formatter": "json" if settings.log_format == "json" else "standard",
                "stream": sys.stdout
            }
        },
        "loggers": {
            # 应用日志
            "aetherfolio": {
                "level": settings.log_level,
                "handlers": ["console"],
                "propagate": False
            },
            # 性能日志
            "performance": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            # 安全日志
            "security": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            # FastAPI日志
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "uvicorn.error": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            # 根日志
            "root": {
                "level": settings.log_level,
                "handlers": ["console"]
            }
        }
    }
    
    # 如果指定了日志文件，添加文件处理器
    if settings.log_file:
        logging_config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": settings.log_level,
            "formatter": "json" if settings.log_format == "json" else "detailed",
            "filename": settings.log_file,
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8"
        }
        
        # 为所有日志器添加文件处理器
        for logger_name in logging_config["loggers"]:
            if "handlers" in logging_config["loggers"][logger_name]:
                logging_config["loggers"][logger_name]["handlers"].append("file")
    
    # 应用配置
    logging.config.dictConfig(logging_config)
    
    # 设置第三方库的日志级别
    logging.getLogger("multipart").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # 如果是开发环境，显示更详细的日志
    if settings.debug:
        logging.getLogger("aetherfolio").setLevel(logging.DEBUG)


def get_logger(name: str) -> logging.Logger:
    """获取日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        logging.Logger: 日志记录器实例
    """
    return logging.getLogger(f"aetherfolio.{name}")


# 创建全局日志记录器实例
performance_logger = PerformanceLogger()
security_logger = SecurityLogger()


# 导出
__all__ = [
    "setup_logging",
    "get_logger",
    "PerformanceLogger",
    "SecurityLogger",
    "performance_logger",
    "security_logger"
]