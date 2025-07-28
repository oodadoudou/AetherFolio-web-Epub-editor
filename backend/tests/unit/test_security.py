"""安全功能单元测试"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException, UploadFile
import io

from backend.core.security import (
    SecurityValidator,
    FileValidator
)
from backend.core.exceptions import (
    SecurityError,
    FileValidationError
)


class TestSecurityValidator:
    """安全验证器测试"""
    
    def setup_method(self):
        """测试方法设置"""
        self.validator = SecurityValidator()
    
    def test_validate_session_id_valid(self):
        """测试有效会话ID验证"""
        valid_session_id = "session_123456789abcdef"
        
        # 应该不抛出异常
        SecurityValidator.validate_session_id(valid_session_id)
    
    def test_validate_session_id_invalid_format(self):
        """测试无效格式的会话ID"""
        invalid_session_ids = [
            "short",  # 太短
            "session_with_invalid_chars!",  # 包含无效字符
            "a" * 100,  # 太长
            "",  # 空字符串
            None  # None值
        ]
        
        for invalid_id in invalid_session_ids:
            with pytest.raises(SecurityError):
                SecurityValidator.validate_session_id(invalid_id)
    
    def test_validate_file_path_valid(self):
        """测试有效文件路径验证"""
        valid_paths = [
            "chapter1.html",
            "images/cover.jpg",
            "styles/main.css",
            "text/chapter01.xhtml"
        ]
        
        for path in valid_paths:
            # 应该不抛出异常
            SecurityValidator.validate_file_path(path)
    
    def test_validate_file_path_invalid(self):
        """测试无效文件路径"""
        invalid_paths = [
            "../../../etc/passwd",  # 路径遍历
            "/absolute/path",  # 绝对路径
            "path/with/../traversal",  # 路径遍历
            "file<script>alert(1)</script>.html",  # XSS尝试
            "file\x00.txt",  # 空字节注入
            "con.txt",  # Windows保留名称
            "file" + "a" * 300 + ".txt"  # 路径太长
        ]
        
        for path in invalid_paths:
            with pytest.raises(SecurityError):
                SecurityValidator.validate_file_path(path)
    
    def test_sanitize_filename(self):
        """测试文件名清理"""
        test_cases = [
            ("normal_file.txt", "normal_file.txt"),
            ("file with spaces.txt", "file_with_spaces.txt"),
            ("file<>:\"|?*.txt", "file.txt"),
            ("../../../dangerous.txt", "dangerous.txt"),
            ("file\x00.txt", "file.txt")
        ]
        
        for input_name, expected in test_cases:
            result = self.validator.sanitize_filename(input_name)
            assert result == expected
    
    def test_validate_content_length(self):
        """测试内容长度验证"""
        # 有效长度
        valid_content = "a" * 1000
        self.validator.validate_content_length(valid_content, max_length=2000)
        
        # 无效长度
        invalid_content = "a" * 3000
        with pytest.raises(SecurityError):
            self.validator.validate_content_length(invalid_content, max_length=2000)


class TestFileValidator:
    """文件验证器测试"""
    
    def setup_method(self):
        """测试方法设置"""
        self.validator = FileValidator()
    
    def test_validate_epub_file_valid(self):
        """测试有效EPUB文件验证"""
        # 创建模拟的EPUB文件
        epub_content = b"PK\x03\x04" + b"\x00" * 100  # ZIP文件头
        epub_file = UploadFile(
            filename="test.epub",
            file=io.BytesIO(epub_content),
            headers={"content-type": "application/epub+zip"}
        )
        
        # 应该不抛出异常
        self.validator.validate_epub_file(epub_file)
    
    def test_validate_epub_file_invalid_extension(self):
        """测试无效扩展名的文件"""
        invalid_file = UploadFile(
            filename="test.txt",
            file=io.BytesIO(b"content"),
            headers={"content-type": "text/plain"}
        )
        
        with pytest.raises(FileValidationError):
            self.validator.validate_epub_file(invalid_file)
    
    def test_validate_epub_file_invalid_content_type(self):
        """测试无效内容类型的文件"""
        invalid_file = UploadFile(
            filename="test.epub",
            file=io.BytesIO(b"content"),
            headers={"content-type": "text/plain"}
        )
        
        with pytest.raises(FileValidationError):
            self.validator.validate_epub_file(invalid_file)
    
    def test_validate_file_size_valid(self):
        """测试有效文件大小"""
        content = b"a" * 1000  # 1KB
        file_obj = UploadFile(
            filename="test.epub",
            file=io.BytesIO(content)
        )
        
        # 应该不抛出异常
        self.validator.validate_file_size(file_obj, max_size=2000)
    
    def test_validate_file_size_invalid(self):
        """测试无效文件大小"""
        content = b"a" * 3000  # 3KB
        file_obj = UploadFile(
            filename="test.epub",
            file=io.BytesIO(content)
        )
        
        with pytest.raises(FileValidationError):
            self.validator.validate_file_size(file_obj, max_size=2000)
    
    def test_validate_rules_file_valid(self):
        """测试有效规则文件验证"""
        rules_content = "old_text\tnew_text\nother_old\tother_new"
        rules_file = UploadFile(
            filename="rules.txt",
            file=io.BytesIO(rules_content.encode()),
            headers={"content-type": "text/plain"}
        )
        
        # 应该不抛出异常
        self.validator.validate_rules_file(rules_file)
    
    def test_validate_rules_file_invalid_extension(self):
        """测试无效扩展名的规则文件"""
        invalid_file = UploadFile(
            filename="rules.exe",
            file=io.BytesIO(b"content"),
            headers={"content-type": "application/octet-stream"}
        )
        
        with pytest.raises(FileValidationError):
            self.validator.validate_rules_file(invalid_file)
    
    def test_scan_for_malware_clean(self):
        """测试恶意软件扫描 - 干净文件"""
        clean_content = b"This is a clean file content"
        
        # 应该返回True（干净）
        result = self.validator.scan_for_malware(clean_content)
        assert result is True
    
    def test_scan_for_malware_suspicious(self):
        """测试恶意软件扫描 - 可疑内容"""
        suspicious_patterns = [
            b"<script>alert('xss')</script>",
            b"javascript:void(0)",
            b"eval(atob(",
            b"document.write("
        ]
        
        for pattern in suspicious_patterns:
            result = self.validator.scan_for_malware(pattern)
            assert result is False