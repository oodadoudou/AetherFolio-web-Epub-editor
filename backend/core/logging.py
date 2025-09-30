"""日志系统模块"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 绿色
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\033[35m',  # 紫色
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logger(
    name: str,
    level: str = "INFO",
    log_file: Optional[str] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """设置日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        log_file: 日志文件路径
        format_string: 日志格式字符串
    
    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, level.upper()))
    
    # 默认格式
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_formatter = ColoredFormatter(format_string)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, level.upper()))
        file_formatter = logging.Formatter(format_string)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """获取日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
    
    Returns:
        日志记录器实例
    """
    return setup_logger(name, level)


# 创建专用的日志记录器
performance_logger = setup_logger(
    "performance",
    level="INFO",
    format_string="%(asctime)s - PERF - %(message)s"
)

security_logger = setup_logger(
    "security",
    level="WARNING",
    format_string="%(asctime)s - SEC - %(levelname)s - %(message)s"
)

# 应用主日志记录器
app_logger = setup_logger(
    "aetherfolio",
    level="INFO"
)


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, logger: logging.Logger = performance_logger):
        self.logger = logger
        self.start_time = None
    
    def start(self, operation: str):
        """开始监控操作"""
        self.start_time = datetime.now()
        self.operation = operation
        self.logger.info(f"开始操作: {operation}")
    
    def end(self, details: str = ""):
        """结束监控操作"""
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            message = f"操作完成: {self.operation}, 耗时: {duration:.3f}s"
            if details:
                message += f", 详情: {details}"
            self.logger.info(message)
            self.start_time = None
    
    def log_slow_operation(self, operation: str, duration: float, threshold: float = 1.0):
        """记录慢操作"""
        if duration > threshold:
            self.logger.warning(
                f"慢操作检测: {operation}, 耗时: {duration:.3f}s (阈值: {threshold}s)"
            )


class SecurityMonitor:
    """安全监控器"""
    
    def __init__(self, logger: logging.Logger = security_logger):
        self.logger = logger
    
    def log_auth_attempt(self, username: str, success: bool, ip: str = "unknown"):
        """记录认证尝试"""
        status = "成功" if success else "失败"
        self.logger.info(f"认证尝试 - 用户: {username}, 状态: {status}, IP: {ip}")
    
    def log_security_violation(self, violation_type: str, details: str, ip: str = "unknown"):
        """记录安全违规"""
        self.logger.warning(f"安全违规 - 类型: {violation_type}, IP: {ip}, 详情: {details}")
    
    def log_file_access(self, file_path: str, user: str, action: str):
        """记录文件访问"""
        self.logger.info(f"文件访问 - 用户: {user}, 动作: {action}, 文件: {file_path}")


# 创建监控器实例
performance_monitor = PerformanceMonitor()
security_monitor = SecurityMonitor()