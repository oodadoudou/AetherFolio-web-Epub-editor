"""配置单元测试"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from backend.core.config import Settings
from backend.core.exceptions import ConfigurationError


class TestSettings:
    """设置配置测试"""
    
    def setup_method(self):
        """测试方法设置"""
        # 保存原始环境变量
        self.original_env = os.environ.copy()
    
    def teardown_method(self):
        """测试方法清理"""
        # 恢复原始环境变量
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_default_settings(self):
        """测试默认设置"""
        # 清除可能影响测试的环境变量
        for key in ['DEBUG', 'TESTING', 'HOST', 'PORT', 'LOG_LEVEL']:
            if key in os.environ:
                del os.environ[key]
        
        settings = Settings()
        
        # 基本设置
        assert settings.app_name == "AetherFolio EPUB Editor"
        assert settings.version == "1.0.0"
        assert settings.debug is False
        assert settings.testing is False
        
        # API设置
        assert settings.api_v1_prefix == "/api/v1"
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        
        # CORS设置
        assert "http://localhost:3000" in settings.allowed_origins
        assert "http://127.0.0.1:3000" in settings.allowed_origins
        
        # 文件设置
        assert settings.upload_dir == "uploads"
        assert settings.temp_dir == "temp"
        assert settings.session_dir == "sessions"
        
        # 文件限制
        assert settings.max_file_size == 100 * 1024 * 1024  # 100MB
        assert settings.max_files_per_session == 10
        
        # 会话设置
        assert settings.session_timeout == 3600  # 1小时
        assert settings.max_sessions == 1000
        
        # 速率限制
        assert settings.rate_limit_requests == 100
        assert settings.rate_limit_window == 60
        
        # 日志设置
        assert settings.log_level == "INFO"
        assert settings.log_format == "json"
        
        # 安全设置
        assert len(settings.secret_key) > 0
        assert settings.allowed_file_types == ["application/epub+zip"]
        assert settings.allowed_rule_file_types == [".txt", ".csv"]
        
        # 性能设置
        assert settings.worker_processes == 1
        assert settings.max_concurrent_tasks == 10
        
        # EPUB处理设置
        assert settings.epub_extract_timeout == 300
        assert settings.epub_validation_enabled is True
        
        # 批量替换设置
        assert settings.batch_size == 100
        assert settings.max_replacement_rules == 1000
        
        # 预览设置
        assert settings.preview_cache_size == 50
        assert settings.preview_cache_ttl == 1800
    
    def test_environment_variable_override(self):
        """测试环境变量覆盖"""
        # 设置环境变量
        os.environ["DEBUG"] = "true"
        os.environ["HOST"] = "127.0.0.1"
        os.environ["PORT"] = "9000"
        os.environ["LOG_LEVEL"] = "DEBUG"
        os.environ["MAX_FILE_SIZE"] = "50000000"  # 50MB
        
        settings = Settings()
        
        assert settings.debug is True
        assert settings.host == "127.0.0.1"
        assert settings.port == 9000
        assert settings.log_level == "DEBUG"
        assert settings.max_file_size == 50000000
    
    def test_testing_environment(self):
        """测试测试环境设置"""
        os.environ["TESTING"] = "true"
        
        settings = Settings()
        
        assert settings.testing is True
        # 测试环境下的特殊设置
        assert settings.session_timeout > 0
    
    def test_database_url_sqlite(self):
        """测试SQLite数据库URL"""
        settings = Settings()
        
        db_url = settings.database_url_computed
        assert db_url.startswith("sqlite:///")
        assert "database.db" in db_url
    
    def test_database_url_postgresql(self):
        """测试PostgreSQL数据库URL"""
        os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost/dbname"
        
        settings = Settings()
        
        assert settings.database_url == "postgresql://user:pass@localhost/dbname"
    
    def test_redis_url_default(self):
        """测试默认Redis URL"""
        settings = Settings()
        
        assert settings.redis_url == "redis://localhost:6379/0"
    
    def test_redis_url_custom(self):
        """测试自定义Redis URL"""
        os.environ["REDIS_URL"] = "redis://custom-host:6380/1"
        
        settings = Settings()
        
        assert settings.redis_url == "redis://custom-host:6380/1"
    
    def test_ensure_directories(self):
        """测试目录创建"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 设置临时目录
            os.environ["UPLOAD_DIR"] = os.path.join(temp_dir, "uploads")
            os.environ["TEMP_DIR"] = os.path.join(temp_dir, "temp")
            os.environ["SESSION_DIR"] = os.path.join(temp_dir, "sessions")
            os.environ["REPORTS_DIR"] = os.path.join(temp_dir, "reports")
            
            settings = Settings()
            settings._ensure_directories()
            
            # 验证目录已创建
            assert os.path.exists(settings.upload_dir)
            assert os.path.exists(settings.temp_dir)
            assert os.path.exists(settings.session_dir)
            assert os.path.exists(settings.reports_dir)
            
            # 验证目录权限
            assert os.access(settings.upload_dir, os.W_OK)
            assert os.access(settings.temp_dir, os.W_OK)
            assert os.access(settings.session_dir, os.W_OK)
            assert os.access(settings.reports_dir, os.W_OK)
    
    def test_is_development(self):
        """测试开发环境检测"""
        # 清除DEBUG环境变量，确保默认情况下不是开发环境
        if "DEBUG" in os.environ:
            del os.environ["DEBUG"]
        settings = Settings()
        assert settings.is_development is False
        
        # 设置DEBUG为True
        os.environ["DEBUG"] = "true"
        settings = Settings()
        assert settings.is_development is True
    
    def test_is_production(self):
        """测试生产环境检测"""
        # 清除DEBUG环境变量，确保默认情况下是生产环境
        if "DEBUG" in os.environ:
            del os.environ["DEBUG"]
        settings = Settings()
        assert settings.is_production is True
        
        # 设置DEBUG为True
        os.environ["DEBUG"] = "true"
        settings = Settings()
        assert settings.is_production is False
    
    def test_cors_settings_development(self):
        """测试开发环境CORS设置"""
        os.environ["DEBUG"] = "true"
        
        settings = Settings()
        
        # 开发环境应该允许更多源
        assert "*" in settings.allowed_origins or len(settings.allowed_origins) > 2
    
    def test_cors_settings_production(self):
        """测试生产环境CORS设置"""
        os.environ["DEBUG"] = "false"
        os.environ["ALLOWED_ORIGINS"] = "https://example.com,https://app.example.com"
        
        settings = Settings()
        
        # 生产环境应该有限制的源
        assert "https://example.com" in settings.allowed_origins
        assert "https://app.example.com" in settings.allowed_origins
        assert "*" not in settings.allowed_origins
    
    def test_secret_key_generation(self):
        """测试密钥生成"""
        # 清除环境变量以确保使用默认生成
        if 'SECRET_KEY' in os.environ:
            del os.environ['SECRET_KEY']
            
        settings1 = Settings()
        settings2 = Settings()
        
        # 每次应该生成不同的密钥
        assert settings1.secret_key != settings2.secret_key
        assert len(settings1.secret_key) >= 32
    
    def test_secret_key_from_environment(self):
        """测试从环境变量获取密钥"""
        custom_key = "my-super-secret-key-for-testing"
        os.environ["SECRET_KEY"] = custom_key
        
        settings = Settings()
        
        assert settings.secret_key == custom_key
    
    def test_file_type_validation(self):
        """测试文件类型验证"""
        settings = Settings()
        
        # 默认允许的文件类型
        assert "application/epub+zip" in settings.allowed_file_types
        
        # 规则文件类型
        assert ".txt" in settings.allowed_rule_file_types
        assert ".csv" in settings.allowed_rule_file_types
    
    def test_custom_file_types(self):
        """测试自定义文件类型"""
        os.environ["ALLOWED_FILE_TYPES"] = ".epub,.zip"
        os.environ["ALLOWED_RULE_FILE_TYPES"] = ".txt,.json"
        
        settings = Settings()
        
        assert ".epub" in settings.allowed_file_types
        assert ".zip" in settings.allowed_file_types
        assert ".txt" in settings.allowed_rule_file_types
        assert ".json" in settings.allowed_rule_file_types
    
    def test_performance_settings(self):
        """测试性能设置"""
        os.environ["WORKER_PROCESSES"] = "4"
        os.environ["MAX_CONCURRENT_TASKS"] = "20"
        
        settings = Settings()
        
        assert settings.worker_processes == 4
        assert settings.max_concurrent_tasks == 20
    
    def test_cache_settings(self):
        """测试缓存设置"""
        os.environ["PREVIEW_CACHE_SIZE"] = "100"
        os.environ["PREVIEW_CACHE_TTL"] = "3600"
        
        settings = Settings()
        
        assert settings.preview_cache_size == 100
        assert settings.preview_cache_ttl == 3600
    
    def test_timeout_settings(self):
        """测试超时设置"""
        os.environ["SESSION_TIMEOUT"] = "7200"  # 2小时
        os.environ["EPUB_EXTRACT_TIMEOUT"] = "600"  # 10分钟
        
        settings = Settings()
        
        assert settings.session_timeout == 7200
        assert settings.epub_extract_timeout == 600
    
    def test_batch_processing_settings(self):
        """测试批处理设置"""
        os.environ["BATCH_SIZE"] = "200"
        os.environ["MAX_REPLACEMENT_RULES"] = "2000"
        
        settings = Settings()
        
        assert settings.batch_size == 200
        assert settings.max_replacement_rules == 2000
    
    def test_invalid_configuration(self):
        """测试无效配置处理"""
        # 设置无效的端口号
        os.environ["PORT"] = "invalid_port"
        
        with pytest.raises((ValueError, ConfigurationError)):
            Settings()
    
    def test_configuration_validation(self):
        """测试配置验证"""
        settings = Settings()
        
        # 验证关键配置项
        assert settings.max_file_size > 0
        assert settings.session_timeout > 0
        assert settings.rate_limit_requests > 0
        assert settings.rate_limit_window > 0
        assert settings.max_concurrent_tasks > 0
        assert settings.batch_size > 0
        assert len(settings.secret_key) > 0
    
    @patch('pathlib.Path.mkdir')
    def test_directory_creation_failure(self, mock_mkdir):
        """测试目录创建失败处理"""
        mock_mkdir.side_effect = PermissionError("Permission denied")
        
        settings = Settings()
        
        with pytest.raises(ConfigurationError):
            settings._ensure_directories()
    
    def test_settings_repr(self):
        """测试设置对象字符串表示"""
        # 设置固定的secret_key以便测试
        os.environ["SECRET_KEY"] = "test-secret-key-for-repr"
        settings = Settings()
        
        repr_str = repr(settings)
        assert "Settings" in repr_str
        # 确保敏感信息不在字符串表示中
        assert "test-secret-key-for-repr" not in repr_str
    
    def test_settings_dict_export(self):
        """测试设置导出为字典"""
        settings = Settings()
        
        # 如果有to_dict方法
        if hasattr(settings, 'to_dict'):
            settings_dict = settings.to_dict()
            assert isinstance(settings_dict, dict)
            assert 'app_name' in settings_dict
            # 确保敏感信息不在导出中
            assert 'secret_key' not in settings_dict or settings_dict['secret_key'] == '[HIDDEN]'