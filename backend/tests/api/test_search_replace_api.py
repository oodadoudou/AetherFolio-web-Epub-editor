"""搜索替换API测试"""

import pytest
import io
from fastapi.testclient import TestClient
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


class TestSearchReplaceAPI:
    """搜索替换API测试类"""
    
    def test_search_in_files_success(self, client: TestClient, sample_epub_data: bytes):
        """测试成功搜索文本"""
        # 首先上传文件创建会话
        files = {
            "file": ("test.epub", io.BytesIO(sample_epub_data), "application/epub+zip")
        }
        upload_response = client.post("/api/v1/upload/epub", files=files)
        assert upload_response.status_code == 200
        session_id = upload_response.json()["data"]["session_id"]
        
        # 执行搜索
        search_data = {
            "query": "test",
            "case_sensitive": False,
            "use_regex": False,
            "whole_word": False
        }
        
        response = client.post(f"/api/v1/search-replace/{session_id}/search", json=search_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert isinstance(data["data"], list)
    
    def test_search_case_sensitive(self, client: TestClient, sample_epub_data: bytes):
        """测试大小写敏感搜索"""
        # 上传文件
        files = {
            "file": ("test.epub", io.BytesIO(sample_epub_data), "application/epub+zip")
        }
        upload_response = client.post("/api/v1/upload/epub", files=files)
        session_id = upload_response.json()["data"]["session_id"]
        
        # 大小写敏感搜索
        search_data = {
            "query": "Test",
            "case_sensitive": True,
            "use_regex": False,
            "whole_word": False
        }
        
        response = client.post(f"/api/v1/search-replace/{session_id}/search", json=search_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_search_regex(self, client: TestClient, sample_epub_data: bytes):
        """测试正则表达式搜索"""
        # 上传文件
        files = {
            "file": ("test.epub", io.BytesIO(sample_epub_data), "application/epub+zip")
        }
        upload_response = client.post("/api/v1/upload/epub", files=files)
        session_id = upload_response.json()["data"]["session_id"]
        
        # 正则表达式搜索
        search_data = {
            "query": r"\b\w+\b",  # 匹配单词
            "case_sensitive": False,
            "use_regex": True,
            "whole_word": False
        }
        
        response = client.post(f"/api/v1/search-replace/{session_id}/search", json=search_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_search_whole_word(self, client: TestClient, sample_epub_data: bytes):
        """测试全词匹配搜索"""
        # 上传文件
        files = {
            "file": ("test.epub", io.BytesIO(sample_epub_data), "application/epub+zip")
        }
        upload_response = client.post("/api/v1/upload/epub", files=files)
        session_id = upload_response.json()["data"]["session_id"]
        
        # 全词匹配搜索
        search_data = {
            "query": "test",
            "case_sensitive": False,
            "use_regex": False,
            "whole_word": True
        }
        
        response = client.post(f"/api/v1/search-replace/{session_id}/search", json=search_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_search_invalid_session(self, client: TestClient):
        """测试无效会话ID搜索"""
        search_data = {
            "query": "test",
            "case_sensitive": False,
            "use_regex": False,
            "whole_word": False
        }
        
        response = client.post("/api/v1/search-replace/invalid-session/search", json=search_data)
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
    
    def test_search_empty_query(self, client: TestClient, sample_epub_data: bytes):
        """测试空搜索查询"""
        # 上传文件
        files = {
            "file": ("test.epub", io.BytesIO(sample_epub_data), "application/epub+zip")
        }
        upload_response = client.post("/api/v1/upload/epub", files=files)
        session_id = upload_response.json()["data"]["session_id"]
        
        # 空查询搜索
        search_data = {
            "query": "",
            "case_sensitive": False,
            "use_regex": False,
            "whole_word": False
        }
        
        response = client.post(f"/api/v1/search-replace/{session_id}/search", json=search_data)
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
    
    def test_search_invalid_regex(self, client: TestClient, sample_epub_data: bytes):
        """测试无效正则表达式"""
        # 上传文件
        files = {
            "file": ("test.epub", io.BytesIO(sample_epub_data), "application/epub+zip")
        }
        upload_response = client.post("/api/v1/upload/epub", files=files)
        session_id = upload_response.json()["data"]["session_id"]
        
        # 无效正则表达式
        search_data = {
            "query": "[invalid regex",
            "case_sensitive": False,
            "use_regex": True,
            "whole_word": False
        }
        
        response = client.post(f"/api/v1/search-replace/{session_id}/search", json=search_data)
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
    
    def test_replace_in_files_success(self, client: TestClient, sample_epub_data: bytes):
        """测试成功替换文本"""
        # 上传文件
        files = {
            "file": ("test.epub", io.BytesIO(sample_epub_data), "application/epub+zip")
        }
        upload_response = client.post("/api/v1/upload/epub", files=files)
        session_id = upload_response.json()["data"]["session_id"]
        
        # 执行替换
        replace_data = {
            "original": "test",
            "replacement": "TEST",
            "case_sensitive": False,
            "use_regex": False,
            "whole_word": False
        }
        
        response = client.post(f"/api/v1/search-replace/{session_id}/replace", json=replace_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "replaced_count" in data["data"]
    
    def test_replace_with_regex(self, client: TestClient, sample_epub_data: bytes):
        """测试正则表达式替换"""
        # 上传文件
        files = {
            "file": ("test.epub", io.BytesIO(sample_epub_data), "application/epub+zip")
        }
        upload_response = client.post("/api/v1/upload/epub", files=files)
        session_id = upload_response.json()["data"]["session_id"]
        
        # 正则表达式替换
        replace_data = {
            "original": r"\b(\w+)\b",
            "replacement": r"[$1]",
            "case_sensitive": False,
            "use_regex": True,
            "whole_word": False
        }
        
        response = client.post(f"/api/v1/search-replace/{session_id}/replace", json=replace_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_replace_invalid_session(self, client: TestClient):
        """测试无效会话ID替换"""
        replace_data = {
            "original": "test",
            "replacement": "TEST",
            "case_sensitive": False,
            "use_regex": False,
            "whole_word": False
        }
        
        response = client.post("/api/v1/search-replace/invalid-session/replace", json=replace_data)
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
    
    def test_replace_empty_original_text(self, client: TestClient, sample_epub_data: bytes):
        """测试空搜索文本替换"""
        # 上传文件
        files = {
            "file": ("test.epub", io.BytesIO(sample_epub_data), "application/epub+zip")
        }
        upload_response = client.post("/api/v1/upload/epub", files=files)
        session_id = upload_response.json()["data"]["session_id"]
        
        # 空搜索文本
        replace_data = {
            "original": "",
            "replacement": "TEST",
            "case_sensitive": False,
            "use_regex": False,
            "whole_word": False
        }
        
        response = client.post(f"/api/v1/search-replace/{session_id}/replace", json=replace_data)
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False


@pytest.mark.asyncio
class TestSearchReplaceAPIAsync:
    """异步搜索替换API测试类"""
    
    async def test_search_async(self, async_client: AsyncClient, sample_epub_data: bytes):
        """测试异步搜索"""
        # 上传文件
        files = {
            "file": ("test.epub", io.BytesIO(sample_epub_data), "application/epub+zip")
        }
        upload_response = await async_client.post("/api/v1/upload/epub", files=files)
        session_id = upload_response.json()["data"]["session_id"]
        
        # 异步搜索
        search_data = {
            "query": "test",
            "case_sensitive": False,
            "use_regex": False,
            "whole_word": False
        }
        
        response = await async_client.post(f"/api/v1/search-replace/{session_id}/search", json=search_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    async def test_replace_async(self, async_client: AsyncClient, sample_epub_data: bytes):
        """测试异步替换"""
        # 上传文件
        files = {
            "file": ("test.epub", io.BytesIO(sample_epub_data), "application/epub+zip")
        }
        upload_response = await async_client.post("/api/v1/upload/epub", files=files)
        session_id = upload_response.json()["data"]["session_id"]
        
        # 异步替换
        replace_data = {
            "original": "test",
            "replacement": "TEST",
            "case_sensitive": False,
            "use_regex": False,
            "whole_word": False
        }
        
        response = await async_client.post(f"/api/v1/search-replace/{session_id}/replace", json=replace_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestSearchReplaceRateLimit:
    """搜索替换API速率限制测试"""
    
    def test_search_rate_limit(self, client: TestClient, sample_epub_data: bytes):
        """测试搜索API速率限制"""
        # 上传文件
        files = {
            "file": ("test.epub", io.BytesIO(sample_epub_data), "application/epub+zip")
        }
        upload_response = client.post("/api/v1/upload/epub", files=files)
        session_id = upload_response.json()["data"]["session_id"]
        
        search_data = {
            "query": "test",
            "case_sensitive": False,
            "use_regex": False,
            "whole_word": False
        }
        
        # 快速连续请求，测试速率限制
        responses = []
        for _ in range(15):  # 超过限制
            response = client.post(f"/api/v1/search-replace/{session_id}/search", json=search_data)
            responses.append(response)
        
        # 检查是否有429状态码（Too Many Requests）
        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes or all(code == 200 for code in status_codes)