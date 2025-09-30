"""应用程序配置模块"""

import os
from pathlib import Path
from typing import Optional
try:
    from pydantic_settings import BaseSettings
    from pydantic import Field
except ImportError:
    from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """应用程序设置"""
    
    # 应用基础配置
    app_name: str = "AetherFolio EPUB Editor"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    
    # 服务器配置
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    allowed_origins: list = Field(default=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"], env="ALLOWED_ORIGINS")  # CORS允许的源
    
    # 数据库配置 - 确保路径指向backend/db/data
    database_url: str = Field(
        default="sqlite:///./db/data/aetherfolio.db",
        env="DATABASE_URL"
    )
    auth_database_url: str = Field(
        default="sqlite:///./db/data/auth.db",
        env="AUTH_DATABASE_URL"
    )
    # Session数据库配置已移除 - 现在使用内存存储
    
    # 文件存储配置
    data_dir: str = Field(default="./data", env="DATA_DIR")
    backup_dir: str = Field(default="./backups", env="BACKUP_DIR")
    
    # 文件大小限制
    max_file_size: int = Field(default=100 * 1024 * 1024, env="MAX_FILE_SIZE")  # 文件大小限制
    max_epub_file_size: int = Field(default=50 * 1024 * 1024, env="MAX_EPUB_FILE_SIZE")  # 50MB
    max_text_file_size: int = Field(default=10 * 1024 * 1024, env="MAX_TEXT_FILE_SIZE")   # 10MB
    max_request_size: int = Field(default=100 * 1024 * 1024, env="MAX_REQUEST_SIZE")  # 100MB
    epub_max_files: int = Field(default=1000, env="EPUB_MAX_FILES")  # EPUB文件最大包含文件数量
    preview_max_size: int = Field(default=20 * 1024 * 1024, env="PREVIEW_MAX_SIZE")  # 预览文件最大大小 5MB
    
    # 性能配置
    worker_processes: int = Field(default=4, env="WORKER_PROCESSES")  # 工作进程数
    
    # 安全配置
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        env="SECRET_KEY"
    )
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30,
        env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    

    
    # 日志配置
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    
    # 性能配置
    enable_performance_monitoring: bool = Field(
        default=True,
        env="ENABLE_PERFORMANCE_MONITORING"
    )
    slow_request_threshold: float = Field(
        default=1.0,
        env="SLOW_REQUEST_THRESHOLD"
    )
    
    # 缓存配置
    cache_ttl: int = Field(default=300, env="CACHE_TTL")  # 5分钟
    preview_cache_timeout: int = Field(default=300, env="PREVIEW_CACHE_TIMEOUT")  # 预览缓存超时
    
    # 会话配置
    session_timeout: int = Field(default=3600, env="SESSION_TIMEOUT")  # 1小时
    max_sessions: int = Field(default=100, env="MAX_SESSIONS")  # 最大会话数
    cleanup_interval: int = Field(default=300, env="CLEANUP_INTERVAL")  # 清理间隔，5分钟
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def get_database_path(self) -> Path:
        """获取数据库文件路径"""
        if self.database_url.startswith("sqlite:///"):
            db_path = self.database_url.replace("sqlite:///", "")
            if db_path.startswith("./"):
                return Path(db_path)
            return Path(db_path)
        return Path("./db/data/aetherfolio.db")
    
    def get_auth_database_path(self) -> Path:
        """获取认证数据库文件路径"""
        if self.auth_database_url.startswith("sqlite:///"):
            db_path = self.auth_database_url.replace("sqlite:///", "")
            if db_path.startswith("./"):
                return Path(db_path)
            return Path(db_path)
        return Path("./db/data/auth.db")
    
    # get_session_database_path方法已移除 - Session现在使用内存存储
    
    def ensure_directories(self):
        """确保必要的目录存在"""
        directories = [
            Path(self.data_dir),
            Path(self.backup_dir),
            self.get_database_path().parent,
            self.get_auth_database_path().parent,
            # Session数据库路径已移除 - 现在使用内存存储
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


# 创建全局设置实例
settings = Settings()

# 确保目录存在
settings.ensure_directories()