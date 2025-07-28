"""应用配置设置"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """应用配置类"""
    
    # 应用基础配置
    app_name: str = Field(default="AetherFolio EPUB Editor", description="应用名称")
    version: str = Field(default="1.0.0", description="应用版本")
    app_version: str = Field(default="1.0.0", description="应用版本")
    debug: bool = Field(default=False, description="调试模式")
    testing: bool = Field(default=False, description="测试模式")
    host: str = Field(default="0.0.0.0", description="服务器主机")
    port: int = Field(default=8000, description="服务器端口")
    
    # API配置
    api_v1_prefix: str = Field(default="/api/v1", description="API v1前缀")
    docs_url: str = Field(default="/docs", description="文档URL")
    redoc_url: str = Field(default="/redoc", description="ReDoc URL")
    openapi_url: str = Field(default="/openapi.json", description="OpenAPI规范URL")
    
    # CORS配置
    allowed_origins: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:5175",
            "http://localhost:5176"
        ],
        description="允许的跨域源"
    )
    allowed_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="允许的HTTP方法"
    )
    allowed_headers: List[str] = Field(
        default=["*"],
        description="允许的请求头"
    )
    
    # 文件存储配置
    upload_dir: str = Field(default="uploads", description="上传目录")
    session_dir: str = Field(default="sessions", description="会话目录")
    temp_dir: str = Field(default="temp", description="临时目录")
    reports_dir: str = Field(default="reports", description="报告目录")
    
    # 文件限制配置
    max_file_size: int = Field(default=100 * 1024 * 1024, description="最大文件大小（字节）")
    max_files_per_session: int = Field(default=10, description="每个会话最大文件数")
    max_rules_file_size: int = Field(default=1024 * 1024, description="最大规则文件大小（字节）")
    allowed_file_types: List[str] = Field(
        default=["application/epub+zip"],
        description="允许的文件MIME类型"
    )
    allowed_rule_file_types: List[str] = Field(
        default=[".txt", ".csv"],
        description="允许的规则文件类型"
    )
    
    # 会话管理配置
    session_timeout: int = Field(default=3600, description="会话超时时间（秒）")
    cleanup_interval: int = Field(default=300, description="清理间隔（秒）")
    max_sessions: int = Field(default=1000, description="最大会话数")
    
    # 数据库配置
    database_url: str = Field(default="", description="数据库连接URL")
    
    # Redis配置
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis连接URL")
    redis_db: int = Field(default=0, description="Redis数据库")
    redis_password: Optional[str] = Field(default=None, description="Redis密码")
    
    # 速率限制配置
    rate_limit_enabled: bool = Field(default=True, description="是否启用速率限制")
    rate_limit_requests: int = Field(default=100, description="速率限制请求数")
    rate_limit_window: int = Field(default=60, description="速率限制时间窗口（秒）")
    upload_rate_limit: str = Field(default="10/minute", description="上传速率限制")
    api_rate_limit: str = Field(default="100/minute", description="API速率限制")
    
    # 日志配置
    log_level: str = Field(default="INFO", description="日志级别")
    log_format: str = Field(default="json", description="日志格式")
    log_file: Optional[str] = Field(default=None, description="日志文件路径")
    
    # 安全配置
    secret_key: str = Field(default_factory=lambda: __import__('secrets').token_urlsafe(32), description="密钥")
    access_token_expire_minutes: int = Field(default=30, description="访问令牌过期时间（分钟）")
    
    # 性能配置
    worker_processes: int = Field(default=1, description="工作进程数")
    max_concurrent_tasks: int = Field(default=10, description="最大并发任务数")
    max_connections: int = Field(default=1000, description="最大连接数")
    keepalive_timeout: int = Field(default=5, description="保持连接超时时间")
    slow_request_threshold: float = Field(default=1.0, description="慢请求阈值（秒）")
    max_request_size: int = Field(default=100 * 1024 * 1024, description="最大请求大小（字节）")
    
    # EPUB处理配置
    epub_extract_timeout: int = Field(default=300, description="EPUB解压超时时间（秒）")
    epub_validation_enabled: bool = Field(default=True, description="是否启用EPUB验证")
    epub_max_files: int = Field(default=1000, description="EPUB最大文件数")
    epub_max_size: int = Field(default=500 * 1024 * 1024, description="EPUB最大大小（字节）")
    
    # 批量替换配置
    batch_size: int = Field(default=100, description="批处理大小")
    max_replacement_rules: int = Field(default=1000, description="最大替换规则数")
    batch_replace_timeout: int = Field(default=300, description="批量替换超时时间（秒）")
    batch_replace_max_rules: int = Field(default=1000, description="批量替换最大规则数")
    batch_replace_chunk_size: int = Field(default=100, description="批量替换块大小")
    
    # 预览配置
    preview_cache_size: int = Field(default=50, description="预览缓存大小")
    preview_cache_ttl: int = Field(default=1800, description="预览缓存TTL（秒）")
    preview_cache_timeout: int = Field(default=300, description="预览缓存超时时间（秒）")
    preview_max_size: int = Field(default=10 * 1024 * 1024, description="预览最大大小（字节）")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保目录存在
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        directories = [
            self.upload_dir,
            self.session_dir,
            self.temp_dir,
            self.reports_dir
        ]
        
        try:
            for directory in directories:
                os.makedirs(directory, exist_ok=True)
        except PermissionError as e:
            from backend.core.exceptions import ConfigurationError
            raise ConfigurationError(f"无法创建目录: {str(e)}")
    
    def __repr__(self) -> str:
        """字符串表示，隐藏敏感信息"""
        return f"Settings(app_name='{self.app_name}', version='{self.version}', debug={self.debug}, host='{self.host}', port={self.port}, max_file_size={self.max_file_size})"
    
    def to_dict(self, hide_sensitive: bool = True) -> dict:
        """导出为字典"""
        data = self.dict()
        if hide_sensitive:
            data['secret_key'] = '[HIDDEN]'
        return data
    
    @property
    def database_url_computed(self) -> str:
        """获取计算的数据库URL"""
        if self.database_url:
            return self.database_url
        return f"sqlite:///{self.session_dir}/database.db"
    
    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.debug
    
    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return not self.debug


# 创建全局设置实例
settings = Settings()


# 导出常用配置
__all__ = ["settings", "Settings"]