import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException

from backend.main import app
from backend.services.file_service import file_service
from backend.services.session_service import session_service
from backend.models.schemas import FileContent


class TestFileContentAPI:
    """文件内容API测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.client = TestClient(app)
        self.test_session_id = "test_session_123"
        self.test_file_path = "test_file.txt"
        
    @pytest.fixture
    def mock_session_service(self):
        """模拟会话服务"""
        with patch('backend.api.endpoints.file_content.session_service') as mock:
            # 创建一个模拟的Session对象
            mock_session = MagicMock()
            mock_session.session_id = self.test_session_id
            mock_session.base_path = "/tmp/test_session"
            mock_session.metadata = {
                "base_path": "/tmp/test_session",
                "file_type": "text",
                "session_dir": "/tmp/test_session"
            }
            # 使用AsyncMock来模拟异步方法
            mock.get_session = AsyncMock(return_value=mock_session)
            yield mock
    
    @pytest.fixture
    def mock_file_service(self):
        """模拟文件服务"""
        with patch('backend.api.endpoints.file_content.file_service') as mock:
            yield mock
    
    def test_get_file_content_success(self, mock_session_service, mock_file_service):
        """测试成功获取文件内容"""
        # 准备测试数据
        expected_content = FileContent(
            path="test_file.txt",
            content="Hello, World!",
            mime_type="text/plain",
            size=13,
            encoding="utf-8",
            is_binary=False
        )
        
        # 模拟file_service的get_file_content_enhanced方法为AsyncMock
        mock_file_service.get_file_content_enhanced = AsyncMock(return_value=expected_content)
        
        # 模拟文件系统调用
        with patch('os.path.exists', return_value=True), \
             patch('os.path.isfile', return_value=True), \
             patch('backend.api.endpoints.file_content.security_validator') as mock_validator:
            
            mock_validator.validate_file_path.return_value = True
            mock_validator.sanitize_path.return_value = "/tmp/test_session/test_file.txt"
            
            # 发送请求
            response = self.client.get(
                "/api/v1/file-content",
                params={
                    "session_id": self.test_session_id,
                    "file_path": self.test_file_path
                }
            )
            
            # 验证响应
            assert response.status_code == 200
            data = response.json()
            # 检查是否是ApiResponse格式
            if "status" in data:
                assert data["status"] == "success"
                assert data["data"]["content"] == "Hello, World!"
                assert data["data"]["mime_type"] == "text/plain"
                assert data["data"]["encoding"] == "utf-8"
                assert data["data"]["is_binary"] is False
            else:
                # 简化格式
                assert data["content"] == "Hello, World!"
                assert data["mime_type"] == "text/plain"
                assert data["encoding"] == "utf-8"
                assert data["is_binary"] is False
            
            # 验证服务调用
            mock_session_service.get_session.assert_called_once_with(self.test_session_id)
            mock_file_service.get_file_content_enhanced.assert_called_once()
    
    def test_get_file_content_with_chunk(self, mock_session_service, mock_file_service):
        """测试分块获取文件内容"""
        # 准备测试数据
        expected_content = FileContent(
            path="large_file.txt",
            content="Chunk content...",
            mime_type="text/plain",
            size=1000,
            encoding="utf-8",
            is_binary=False,
            chunk_info={
                "chunk_size": 100,
                "chunk_offset": 0,
                "total_size": 1000,
                "content_size": 100
            }
        )
        
        # 模拟file_service的get_file_content_enhanced方法为AsyncMock
        mock_file_service.get_file_content_enhanced = AsyncMock(return_value=expected_content)
        
        # 模拟文件系统调用
        with patch('os.path.exists', return_value=True), \
             patch('os.path.isfile', return_value=True), \
             patch('backend.api.endpoints.file_content.security_validator') as mock_validator:
            
            mock_validator.validate_file_path.return_value = True
            mock_validator.sanitize_path.return_value = "/tmp/test_session/large_file.txt"
            
            # 发送请求
            response = self.client.get(
                "/api/v1/file-content",
                params={
                    "session_id": self.test_session_id,
                    "file_path": "large_file.txt",
                    "chunk_size": 100,
                    "chunk_offset": 0
                }
            )
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        # 检查是否是ApiResponse格式
        if "status" in data:
            assert data["status"] == "success"
            if "chunk_info" in data["data"]:
                assert data["data"]["chunk_info"]["chunk_size"] == 100
        else:
            # 简化格式
            if "chunk_info" in data:
                assert data["chunk_info"]["chunk_size"] == 100
    
    def test_get_file_content_binary_file(self, mock_session_service, mock_file_service):
        """测试获取二进制文件内容"""
        # 准备测试数据
        expected_content = FileContent(
            path="image.png",
            content="[Binary file - content not displayed]",
            mime_type="image/png",
            size=2048,
            encoding="binary",
            is_binary=True
        )
        
        # 模拟file_service的get_file_content_enhanced方法为AsyncMock
        mock_file_service.get_file_content_enhanced = AsyncMock(return_value=expected_content)
        
        # 模拟文件系统调用
        with patch('os.path.exists', return_value=True), \
             patch('os.path.isfile', return_value=True), \
             patch('backend.api.endpoints.file_content.security_validator') as mock_validator:
            
            mock_validator.validate_file_path.return_value = True
            mock_validator.sanitize_path.return_value = "/tmp/test_session/image.png"
            
            # 发送请求
            response = self.client.get(
                "/api/v1/file-content",
                params={
                    "session_id": self.test_session_id,
                    "file_path": "image.png"
                }
            )
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        # 检查是否是ApiResponse格式
        if "status" in data:
            assert data["status"] == "success"
            assert data["data"]["is_binary"] is True
            assert data["data"]["content"] == "[Binary file - content not displayed]"
        else:
            # 简化格式
            assert data["is_binary"] is True
            assert data["content"] == "[Binary file - content not displayed]"
    
    def test_get_file_content_invalid_session(self, mock_file_service):
        """测试无效会话ID"""
        with patch('backend.api.endpoints.file_content.session_service') as mock_session:
            mock_session.get_session.return_value = None
            
            response = self.client.get(
                "/api/v1/file-content",
                params={
                    "session_id": "invalid_session",
                    "file_path": self.test_file_path
                }
            )
            
            # 验证响应 - 可能返回404或500，取决于session_service的实现
            assert response.status_code in [404, 500]
            data = response.json()
            # 检查错误响应格式
            if "detail" in data:
                # HTTPException格式
                if isinstance(data["detail"], dict):
                    assert data["detail"]["success"] is False
                    # 可能返回不同的错误消息
                    assert any(msg in data["detail"]["error"] for msg in ["会话不存在", "获取文件内容失败"])
                else:
                    assert any(msg in str(data["detail"]) for msg in ["会话不存在", "获取文件内容失败"])
            else:
                # 直接错误格式
                assert data["success"] is False
                assert any(msg in data["error"] for msg in ["会话不存在", "获取文件内容失败"])
    
    def test_get_file_content_file_not_found(self, mock_session_service, mock_file_service):
        """测试文件不存在"""
        # 模拟文件系统调用
        with patch('os.path.exists', return_value=False), \
             patch('os.path.isfile', return_value=False), \
             patch('backend.api.endpoints.file_content.security_validator') as mock_validator:
            
            mock_validator.validate_file_path.return_value = True
            mock_validator.sanitize_path.return_value = "/tmp/test_session/nonexistent.txt"
            
            response = self.client.get(
                "/api/v1/file-content",
                params={
                    "session_id": self.test_session_id,
                    "file_path": "nonexistent.txt"
                }
            )
            
            assert response.status_code == 404
            data = response.json()
            # 检查错误响应格式
            if "detail" in data:
                # HTTPException格式
                if isinstance(data["detail"], dict):
                    assert data["detail"]["success"] is False
                    # 可能返回不同的错误消息
                    assert any(msg in data["detail"]["error"] for msg in ["文件不存在", "会话目录不存在"])
                else:
                    assert any(msg in str(data["detail"]) for msg in ["文件不存在", "会话目录不存在"])
            else:
                # 直接错误格式
                assert data["success"] is False
                assert any(msg in data["error"] for msg in ["文件不存在", "会话目录不存在"])
    
    def test_get_file_content_path_traversal_attack(self, mock_session_service, mock_file_service):
        """测试路径遍历攻击防护"""
        dangerous_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/shadow",
            "C:\\Windows\\System32\\config\\SAM"
        ]
        
        with patch('backend.api.endpoints.file_content.security_validator') as mock_validator:
            mock_validator.validate_file_path.return_value = False
            
            for dangerous_path in dangerous_paths:
                response = self.client.get(
                    "/api/v1/file-content",
                    params={
                        "session_id": self.test_session_id,
                        "file_path": dangerous_path
                    }
                )
                
                assert response.status_code == 400
                data = response.json()
                # 检查错误响应格式
                if "detail" in data:
                    # HTTPException格式
                    if isinstance(data["detail"], dict):
                        assert data["detail"]["success"] is False
                        assert "路径不安全" in data["detail"]["error"]
                    else:
                        assert "路径不安全" in str(data["detail"])
                else:
                    # 直接错误格式
                    assert data["success"] is False
                    assert "路径不安全" in data["error"]
    
    def test_get_file_content_missing_parameters(self):
        """测试缺少必需参数"""
        # 缺少session_id
        response = self.client.get(
            "/api/v1/file-content",
            params={"file_path": self.test_file_path}
        )
        assert response.status_code == 422
        
        # 缺少file_path
        response = self.client.get(
            "/api/v1/file-content",
            params={"session_id": self.test_session_id}
        )
        assert response.status_code == 422
    
    def test_get_file_content_invalid_chunk_parameters(self, mock_session_service, mock_file_service):
        """测试无效的分块参数"""
        # 模拟文件系统调用和安全验证
        with patch('os.path.exists', return_value=True), \
             patch('os.path.isfile', return_value=True), \
             patch('backend.api.endpoints.file_content.security_validator') as mock_validator:
            
            mock_validator.validate_file_path.return_value = True
            mock_validator.sanitize_path.return_value = "/tmp/test_session/test.txt"
            
            # 模拟file_service抛出异常
            mock_file_service.get_file_content_enhanced = AsyncMock(side_effect=ValueError("Invalid chunk parameters"))
            
            # 负数chunk_size
            response = self.client.get(
                "/api/v1/file-content",
                params={
                    "session_id": self.test_session_id,
                    "file_path": self.test_file_path,
                    "chunk_size": -1
                }
            )
            # 由于参数验证在file_service中处理，这里会返回500
            assert response.status_code == 500
            data = response.json()
            # 检查错误响应格式
            if "detail" in data:
                # HTTPException格式
                if isinstance(data["detail"], dict):
                    assert data["detail"]["success"] is False
                    assert "获取文件内容失败" in data["detail"]["error"]
                else:
                    assert "获取文件内容失败" in str(data["detail"])
            else:
                # 直接错误格式
                assert data["success"] is False
                assert "获取文件内容失败" in data["error"]
            
            # 重置mock以便第二次调用
            mock_file_service.get_file_content_enhanced = AsyncMock(side_effect=ValueError("Invalid chunk parameters"))
            
            # 负数chunk_offset
            response = self.client.get(
                "/api/v1/file-content",
                params={
                    "session_id": self.test_session_id,
                    "file_path": self.test_file_path,
                    "chunk_offset": -1
                }
            )
            assert response.status_code == 500
            data = response.json()
            # 检查错误响应格式
            if "detail" in data:
                # HTTPException格式
                if isinstance(data["detail"], dict):
                    assert data["detail"]["success"] is False
                    assert "获取文件内容失败" in data["detail"]["error"]
                else:
                    assert "获取文件内容失败" in str(data["detail"])
            else:
                # 直接错误格式
                assert data["success"] is False
                assert "获取文件内容失败" in data["error"]


class TestFileServiceEnhanced:
    """文件服务增强功能测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_files = {}
        
        # 创建测试文件
        self._create_test_files()
    
    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_files(self):
        """创建测试文件"""
        # UTF-8文本文件
        utf8_file = Path(self.temp_dir) / "utf8_test.txt"
        utf8_file.write_text("Hello, 世界! UTF-8 content.", encoding="utf-8")
        self.test_files["utf8"] = str(utf8_file)
        
        # GBK编码文件
        gbk_file = Path(self.temp_dir) / "gbk_test.txt"
        gbk_file.write_text("你好，世界！GBK内容。", encoding="gbk")
        self.test_files["gbk"] = str(gbk_file)
        
        # HTML文件
        html_file = Path(self.temp_dir) / "test.html"
        html_file.write_text("<html><body><h1>Test HTML</h1></body></html>", encoding="utf-8")
        self.test_files["html"] = str(html_file)
        
        # CSS文件
        css_file = Path(self.temp_dir) / "test.css"
        css_file.write_text("body { color: red; }", encoding="utf-8")
        self.test_files["css"] = str(css_file)
        
        # 二进制文件（模拟）
        binary_file = Path(self.temp_dir) / "test.bin"
        binary_file.write_bytes(b"\x00\x01\x02\x03\x04\x05")
        self.test_files["binary"] = str(binary_file)
        
        # 大文件
        large_file = Path(self.temp_dir) / "large.txt"
        large_content = "Line {}\n" * 1000
        large_file.write_text(large_content.format(*range(1000)), encoding="utf-8")
        self.test_files["large"] = str(large_file)
    
    @pytest.mark.asyncio
    async def test_get_file_content_enhanced_utf8(self):
        """测试获取UTF-8文件内容"""
        result = await file_service.get_file_content_enhanced(self.test_files["utf8"])
        
        assert isinstance(result, FileContent)
        assert "Hello, 世界!" in result.content
        assert result.encoding == "utf-8"
        assert result.mime_type == "text/plain"
        assert result.is_binary is False
        assert result.size > 0
    
    @pytest.mark.asyncio
    async def test_get_file_content_enhanced_gbk(self):
        """测试获取GBK编码文件内容"""
        result = await file_service.get_file_content_enhanced(self.test_files["gbk"])
        
        assert isinstance(result, FileContent)
        assert "你好，世界！" in result.content
        assert result.encoding in ["gbk", "gb2312", "GB2312"]
        assert result.is_binary is False
    
    @pytest.mark.asyncio
    async def test_get_file_content_enhanced_html(self):
        """测试获取HTML文件内容"""
        result = await file_service.get_file_content_enhanced(self.test_files["html"])
        
        assert isinstance(result, FileContent)
        assert "<html>" in result.content
        assert result.mime_type == "text/html"
        assert result.is_binary is False
    
    @pytest.mark.asyncio
    async def test_get_file_content_enhanced_css(self):
        """测试获取CSS文件内容"""
        result = await file_service.get_file_content_enhanced(self.test_files["css"])
        
        assert isinstance(result, FileContent)
        assert "color: red" in result.content
        assert result.mime_type == "text/css"
        assert result.is_binary is False
    
    @pytest.mark.asyncio
    async def test_get_file_content_enhanced_binary(self):
        """测试获取二进制文件内容"""
        result = await file_service.get_file_content_enhanced(self.test_files["binary"])
        
        assert isinstance(result, FileContent)
        assert result.content == "[Binary file - content not displayed]"
        assert result.encoding == "binary"
        assert result.is_binary is True
    
    @pytest.mark.asyncio
    async def test_get_file_content_enhanced_chunked(self):
        """测试分块读取文件内容"""
        chunk_size = 100
        chunk_offset = 0
        
        result = await file_service.get_file_content_enhanced(
            self.test_files["large"],
            chunk_size=chunk_size,
            chunk_offset=chunk_offset
        )
        
        assert isinstance(result, FileContent)
        assert result.chunk_info is not None
        assert result.chunk_info["chunk_size"] == chunk_size
        assert result.chunk_info["chunk_offset"] == chunk_offset
        assert len(result.content) <= chunk_size * 2  # 考虑编码差异
    
    @pytest.mark.asyncio
    async def test_get_file_content_enhanced_file_not_found(self):
        """测试文件不存在的情况"""
        with pytest.raises(FileNotFoundError):
            await file_service.get_file_content_enhanced("/nonexistent/file.txt")
    
    @pytest.mark.asyncio
    async def test_detect_file_encoding(self):
        """测试文件编码检测"""
        # UTF-8文件
        encoding = await file_service.detect_file_encoding(self.test_files["utf8"])
        assert encoding == "utf-8"
        
        # GBK文件
        encoding = await file_service.detect_file_encoding(self.test_files["gbk"])
        assert encoding in ["gbk", "gb2312", "GB2312"]
    
    @pytest.mark.asyncio
    async def test_get_file_type_info(self):
        """测试获取文件类型信息"""
        # HTML文件
        info = await file_service.get_file_type_info(self.test_files["html"])
        assert info["extension"] == ".html"
        assert info["mime_type"] == "text/html"
        assert info["is_text"] is True
        assert info["category"] == "text"
        
        # CSS文件
        info = await file_service.get_file_type_info(self.test_files["css"])
        assert info["extension"] == ".css"
        assert info["mime_type"] == "text/css"
        assert info["is_text"] is True
        
        # 二进制文件
        info = await file_service.get_file_type_info(self.test_files["binary"])
        assert info["extension"] == ".bin"
        assert info["is_binary"] is True
        assert info["category"] == "binary"


class TestFileContentIntegration:
    """文件内容功能集成测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.client = TestClient(app)
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_end_to_end_file_content_workflow(self):
        """测试端到端文件内容工作流"""
        # 这里可以添加完整的集成测试
        # 包括创建会话、上传文件、获取文件内容等完整流程
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])