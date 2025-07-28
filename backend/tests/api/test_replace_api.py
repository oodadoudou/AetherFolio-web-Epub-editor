"""批量替换API测试"""

import pytest
import io
import time
from fastapi.testclient import TestClient
from httpx import AsyncClient


class TestReplaceAPI:
    """批量替换API测试类"""
    
    def _upload_test_epub(self, client: TestClient, sample_epub_data: bytes) -> str:
        """上传测试EPUB文件并返回session_id"""
        files = {
            "file": ("test.epub", io.BytesIO(sample_epub_data), "application/epub+zip")
        }
        response = client.post("/api/v1/upload/epub", files=files)
        assert response.status_code == 200
        data = response.json()
        return data["data"]["session_id"]
    
    def _upload_test_rules(self, client: TestClient, rules_data: str) -> list:
        """上传测试规则并返回规则列表"""
        files = {
            "file": ("rules.txt", io.BytesIO(rules_data.encode()), "text/plain")
        }
        response = client.post("/api/v1/upload/validate-rules", files=files)
        assert response.status_code == 200
        data = response.json()
        return data["data"]["rules"]
    
    def test_execute_batch_replace(self, client: TestClient, sample_epub_data: bytes, sample_rules_data: str):
        """测试执行批量替换"""
        session_id = self._upload_test_epub(client, sample_epub_data)
        rules = self._upload_test_rules(client, sample_rules_data)
        
        replace_data = {
            "session_id": session_id,
            "rules": rules,
            "case_sensitive": True,
            "use_regex": False
        }
        
        response = client.post("/api/v1/batch-replace/", json=replace_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "task_id" in data["data"]
        assert "session_id" in data["data"]
        
        task_id = data["data"]["task_id"]
        assert task_id is not None
    
    def test_execute_batch_replace_invalid_session(self, client: TestClient, sample_rules_data: str):
        """测试在无效会话上执行批量替换"""
        rules = self._upload_test_rules(client, sample_rules_data)
        
        replace_data = {
            "session_id": "invalid-session",
            "rules": rules,
            "case_sensitive": True,
            "use_regex": False
        }
        
        response = client.post("/api/v1/batch-replace/", json=replace_data)
        
        assert response.status_code == 404
        data = response.json()
        assert data["status"] == "error"
    
    def test_execute_batch_replace_empty_rules(self, client: TestClient, sample_epub_data: bytes):
        """测试使用空规则执行批量替换"""
        session_id = self._upload_test_epub(client, sample_epub_data)
        
        replace_data = {
            "session_id": session_id,
            "rules": [],
            "case_sensitive": True,
            "use_regex": False
        }
        
        response = client.post("/api/v1/batch-replace/", json=replace_data)
        
        assert response.status_code == 400
        data = response.json()
        assert data["status"] == "error"
    
    def test_get_replace_progress(self, client: TestClient, sample_epub_data: bytes, sample_rules_data: str):
        """测试获取替换进度"""
        session_id = self._upload_test_epub(client, sample_epub_data)
        rules = self._upload_test_rules(client, sample_rules_data)
        
        # 启动批量替换
        replace_data = {
            "session_id": session_id,
            "rules": rules,
            "case_sensitive": True,
            "use_regex": False
        }
        
        execute_response = client.post("/api/v1/batch-replace/", json=replace_data)
        assert execute_response.status_code == 200
        
        # 获取进度（使用JSON格式端点）
        response = client.get(f"/api/v1/batch-replace/progress/{session_id}/json")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "progress" in data["data"]
        
        progress = data["data"]["progress"]
        assert "status" in progress
        assert "percentage" in progress
        assert "current_file" in progress
        assert "total_files" in progress
        assert "processed_files" in progress
        
        # 验证进度值
        assert progress["status"] in ["pending", "running", "completed", "failed", "cancelled"]
        assert 0 <= progress["percentage"] <= 100
        assert progress["processed_files"] <= progress["total_files"]
    
    def test_get_progress_invalid_session(self, client: TestClient):
        """测试获取无效会话的进度"""
        response = client.get("/api/v1/batch-replace/progress/invalid-session/json")
        
        assert response.status_code == 404
        data = response.json()
        assert data["status"] == "error"
    
    def test_get_replace_report(self, client: TestClient, sample_epub_data: bytes, sample_rules_data: str):
        """测试获取替换报告"""
        session_id = self._upload_test_epub(client, sample_epub_data)
        rules = self._upload_test_rules(client, sample_rules_data)
        
        # 启动批量替换
        replace_data = {
            "session_id": session_id,
            "rules": rules,
            "case_sensitive": True,
            "use_regex": False
        }
        
        execute_response = client.post("/api/v1/batch-replace/", json=replace_data)
        assert execute_response.status_code == 200
        
        # 等待任务完成（简单等待，实际应该轮询进度）
        time.sleep(2)
        
        # 获取报告
        response = client.get(f"/api/v1/batch-replace/report/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "report" in data["data"]
        
        report = data["data"]["report"]
        assert "summary" in report
        assert "details" in report
        assert "statistics" in report
        
        # 验证摘要信息
        summary = report["summary"]
        assert "total_files" in summary
        assert "processed_files" in summary
        assert "total_replacements" in summary
        assert "start_time" in summary
        assert "end_time" in summary
        assert "duration" in summary
        assert "status" in summary
    
    def test_get_report_invalid_session(self, client: TestClient):
        """测试获取无效会话的报告"""
        response = client.get("/api/v1/batch-replace/report/invalid-session")
        
        assert response.status_code == 404
        data = response.json()
        assert data["status"] == "error"
    
    def test_cancel_batch_replace(self, client: TestClient, sample_epub_data: bytes, sample_rules_data: str):
        """测试取消批量替换"""
        session_id = self._upload_test_epub(client, sample_epub_data)
        rules = self._upload_test_rules(client, sample_rules_data)
        
        # 启动批量替换
        replace_data = {
            "session_id": session_id,
            "rules": rules,
            "case_sensitive": True,
            "use_regex": False
        }
        
        execute_response = client.post("/api/v1/batch-replace/", json=replace_data)
        assert execute_response.status_code == 200
        
        # 取消任务
        response = client.delete(f"/api/v1/batch-replace/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "session_id" in data["data"]
        
        # 验证任务状态已更新
        progress_response = client.get(f"/api/v1/batch-replace/progress/{session_id}/json")
        if progress_response.status_code == 200:
            progress_data = progress_response.json()
            if "progress" in progress_data["data"]:
                status = progress_data["data"]["progress"]["status"]
                assert status in ["cancelled", "completed", "failed"]
    
    def test_cancel_invalid_session(self, client: TestClient):
        """测试取消无效会话的批量替换"""
        response = client.delete("/api/v1/batch-replace/invalid-session")
        
        assert response.status_code == 404
        data = response.json()
        assert data["status"] == "error"
    
    def test_batch_replace_with_regex(self, client: TestClient, sample_epub_data: bytes):
        """测试使用正则表达式的批量替换"""
        session_id = self._upload_test_epub(client, sample_epub_data)
        
        # 创建正则表达式规则
        regex_rules = [
            {
                "original": r"\btest\b",
                "replacement": "TEST",
                "is_regex": True
            },
            {
                "original": r"\d+",
                "replacement": "[NUMBER]",
                "is_regex": True
            }
        ]
        
        replace_data = {
            "session_id": session_id,
            "rules": regex_rules,
            "case_sensitive": False,
            "use_regex": True
        }
        
        response = client.post("/api/v1/batch-replace/", json=replace_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "task_id" in data["data"]
    
    def test_batch_replace_case_insensitive(self, client: TestClient, sample_epub_data: bytes):
        """测试不区分大小写的批量替换"""
        session_id = self._upload_test_epub(client, sample_epub_data)
        
        rules = [
            {
                "original": "TEST",
                "replacement": "exam",
                "is_regex": False
            }
        ]
        
        replace_data = {
            "session_id": session_id,
            "rules": rules,
            "case_sensitive": False,
            "use_regex": False
        }
        
        response = client.post("/api/v1/batch-replace/", json=replace_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_batch_replace_whole_word(self, client: TestClient, sample_epub_data: bytes):
        """测试全词匹配的批量替换"""
        session_id = self._upload_test_epub(client, sample_epub_data)
        
        rules = [
            {
                "original": "test",
                "replacement": "exam",
                "is_regex": False
            }
        ]
        
        replace_data = {
            "session_id": session_id,
            "rules": rules,
            "case_sensitive": True,
            "use_regex": False
        }
        
        response = client.post("/api/v1/batch-replace/", json=replace_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_download_template(self, client: TestClient):
        """测试下载批量替换规则模板"""
        response = client.get("/api/v1/batch-replace/template")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        assert "batch_replace_template_" in response.headers["content-disposition"]
        assert ".txt" in response.headers["content-disposition"]
        
        # 验证模板内容
        content = response.content.decode('utf-8')
        assert "# AetherFolio 批量替换规则模板" in content
        assert "# 使用说明:" in content
        assert "# 1. 每行一个替换规则" in content
        assert "# 2. 格式: 原文本 -> 新文本" in content
        assert "# 3. 支持正则表达式" in content
        assert "# 4. 支持大小写敏感" in content
        assert "旧文本 -> 新文本" in content
        assert "REGEX:" in content
        assert "CASE:" in content
        assert "Hello World -> 你好世界" in content
        
        # 验证时间戳格式
        import re
        timestamp_pattern = r"# 生成时间: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
        assert re.search(timestamp_pattern, content) is not None
    
    def test_download_template_filename_format(self, client: TestClient):
        """测试模板文件名格式"""
        response = client.get("/api/v1/batch-replace/template")
        
        assert response.status_code == 200
        
        # 验证文件名格式：batch_replace_template_YYYYMMDD.txt
        content_disposition = response.headers["content-disposition"]
        import re
        filename_pattern = r"filename=batch_replace_template_\d{8}\.txt"
        assert re.search(filename_pattern, content_disposition) is not None
    
    def test_download_template_content_structure(self, client: TestClient):
        """测试模板内容结构"""
        response = client.get("/api/v1/batch-replace/template")
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # 验证各个示例区域是否存在
        assert "# ========== 基本替换示例 ==========" in content
        assert "# ========== 正则表达式替换示例 ==========" in content
        assert "# ========== 大小写敏感替换示例 ==========" in content
        assert "# ========== 组合模式示例 ==========" in content
        assert "# ========== 特殊字符处理示例 ==========" in content
        assert "# ========== 多语言支持示例 ==========" in content
        assert "# ========== 格式化示例 ==========" in content
        assert "# ========== 自定义规则区域 ==========" in content
        
        # 验证具体示例
        assert "错误的词汇 -> 正确的词汇" in content
        assert "REGEX: \\d{4}-\\d{2}-\\d{2} -> [日期已隐藏]" in content
        assert "CASE: HTML -> html" in content
        assert "CASE:REGEX: Chapter\\s+(\\d+) -> 第$1章" in content
        assert "\"引号内容\" -> '引号内容'" in content
        assert "数据库 -> Database" in content
    
    def test_download_template_cache_headers(self, client: TestClient):
        """测试模板下载的缓存头"""
        response = client.get("/api/v1/batch-replace/template")
        
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-cache"
    
    def test_download_template_multiple_requests(self, client: TestClient):
        """测试多次下载模板请求"""
        # 第一次请求
        response1 = client.get("/api/v1/batch-replace/template")
        assert response1.status_code == 200
        content1 = response1.content.decode('utf-8')
        
        # 第二次请求
        response2 = client.get("/api/v1/batch-replace/template")
        assert response2.status_code == 200
        content2 = response2.content.decode('utf-8')
        
        # 内容结构应该相同（除了时间戳）
        lines1 = [line for line in content1.split('\n') if not line.startswith('# 生成时间:')]
        lines2 = [line for line in content2.split('\n') if not line.startswith('# 生成时间:')]
        assert lines1 == lines2
    
    def test_download_template_encoding_utf8(self, client: TestClient):
        """测试模板文件编码格式正确（UTF-8）"""
        response = client.get("/api/v1/batch-replace/template")
        
        assert response.status_code == 200
        assert "charset=utf-8" in response.headers["content-type"]
        
        # 验证中文字符能正确编码
        content = response.content.decode('utf-8')
        assert "AetherFolio 批量替换规则模板" in content
        assert "错误的词汇 -> 正确的词汇" in content
        assert "你好世界" in content
        assert "数据库" in content
        
        # 验证特殊字符能正确编码
        assert "\"引号内容\" -> '引号内容'" in content
        assert "<标签> -> [标签]" in content
    
    def test_download_template_file_corruption_simulation(self, client: TestClient, monkeypatch):
        """测试模拟模板文件损坏情况"""
        from backend.api import replace
        
        # 模拟模板生成函数抛出异常
        def mock_generate_template_content():
            raise IOError("模板文件损坏")
        
        monkeypatch.setattr(replace, "_generate_template_content", mock_generate_template_content)
        
        response = client.get("/api/v1/batch-replace/template")
        
        assert response.status_code == 500
        data = response.json()
        assert "模板下载失败" in data["message"]
    
    def test_download_template_memory_limit_simulation(self, client: TestClient, monkeypatch):
        """测试模拟内存限制情况"""
        from backend.api import replace
        
        # 模拟内存不足
        def mock_generate_template_content():
            raise MemoryError("内存不足")
        
        monkeypatch.setattr(replace, "_generate_template_content", mock_generate_template_content)
        
        response = client.get("/api/v1/batch-replace/template")
        
        assert response.status_code == 500
        data = response.json()
        assert "模板下载失败" in data["message"]
    
    def test_download_template_permission_error_simulation(self, client: TestClient, monkeypatch):
        """测试模拟权限错误情况"""
        from backend.api import replace
        
        # 模拟权限错误
        def mock_generate_template_content():
            raise PermissionError("权限不足")
        
        monkeypatch.setattr(replace, "_generate_template_content", mock_generate_template_content)
        
        response = client.get("/api/v1/batch-replace/template")
        
        assert response.status_code == 500
        data = response.json()
        assert "模板下载失败" in data["message"]


@pytest.mark.asyncio
class TestReplaceAPIAsync:
    """异步批量替换API测试类"""
    
    async def _upload_test_epub_async(self, async_client: AsyncClient, sample_epub_data: bytes) -> str:
        """异步上传测试EPUB文件并返回session_id"""
        files = {
            "file": ("test.epub", io.BytesIO(sample_epub_data), "application/epub+zip")
        }
        response = await async_client.post("/api/v1/upload/epub", files=files)
        assert response.status_code == 200
        data = response.json()
        return data["data"]["session_id"]
    
    async def test_execute_batch_replace_async(self, async_client: AsyncClient, sample_epub_data: bytes, sample_rules_data: str):
        """测试异步执行批量替换"""
        session_id = await self._upload_test_epub_async(async_client, sample_epub_data)
        
        # 上传规则
        files = {
            "file": ("rules.txt", io.BytesIO(sample_rules_data.encode()), "text/plain")
        }
        rules_response = await async_client.post("/api/v1/upload/validate-rules", files=files)
        rules = rules_response.json()["data"]["rules"]
        
        replace_data = {
            "session_id": session_id,
            "rules": rules,
            "case_sensitive": True,
            "use_regex": False
        }
        
        response = await async_client.post("/api/v1/batch-replace/", json=replace_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "task_id" in data["data"]
    
    async def test_get_progress_async(self, async_client: AsyncClient, sample_epub_data: bytes, sample_rules_data: str):
        """测试异步获取替换进度"""
        session_id = await self._upload_test_epub_async(async_client, sample_epub_data)
        
        # 上传规则并启动替换
        files = {
            "file": ("rules.txt", io.BytesIO(sample_rules_data.encode()), "text/plain")
        }
        rules_response = await async_client.post("/api/v1/upload/validate-rules", files=files)
        rules = rules_response.json()["data"]["rules"]
        
        replace_data = {
            "session_id": session_id,
            "rules": rules,
            "case_sensitive": True,
            "use_regex": False
        }
        
        await async_client.post("/api/v1/batch-replace/", json=replace_data)
        
        # 获取进度（使用JSON格式端点）
        response = await async_client.get(f"/api/v1/batch-replace/progress/{session_id}/json")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "progress" in data["data"]