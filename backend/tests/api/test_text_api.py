"""TEXT文件API测试"""

import pytest
import tempfile
import os
from pathlib import Path
from httpx import AsyncClient
from fastapi import status


class TestTextUploadAPI:
    """TEXT文件上传API测试"""
    
    @pytest.mark.asyncio
    async def test_upload_txt_file(self, async_client: AsyncClient, temp_dir: Path):
        """测试上传TXT文件"""
        # 创建测试TXT文件
        test_file = temp_dir / "test.txt"
        test_content = "这是一个测试文本文件\n包含中文和英文内容\nTest content with special chars: @#$%"
        test_file.write_text(test_content, encoding='utf-8')
        
        # 上传文件
        with open(test_file, 'rb') as f:
            response = await async_client.post(
                "/api/v1/upload",
                files={"file": ("test.txt", f, "text/plain")}
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "session_id" in data
        assert data["success"] is True
        
        # 验证会话信息
        session_id = data["session_id"]
        session_response = await async_client.get(f"/api/v1/sessions/{session_id}")
        assert session_response.status_code == status.HTTP_200_OK
        session_data = session_response.json()
        assert session_data["file_type"] == "text"
        assert session_data["original_filename"] == "test.txt"
    
    @pytest.mark.asyncio
    async def test_upload_markdown_file(self, async_client: AsyncClient, temp_dir: Path):
        """测试上传Markdown文件"""
        # 创建测试Markdown文件
        test_file = temp_dir / "test.md"
        test_content = """# 测试标题

这是一个**测试**Markdown文件。

## 子标题

- 列表项1
- 列表项2

```python
print("Hello, World!")
```
"""
        test_file.write_text(test_content, encoding='utf-8')
        
        # 上传文件
        with open(test_file, 'rb') as f:
            response = await async_client.post(
                "/api/v1/upload",
                files={"file": ("test.md", f, "text/markdown")}
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "session_id" in data
        assert data["success"] is True
    
    @pytest.mark.asyncio
    async def test_upload_large_text_file(self, async_client: AsyncClient, temp_dir: Path):
        """测试上传大文件"""
        # 创建大文本文件（约1MB）
        test_file = temp_dir / "large.txt"
        large_content = "这是一行测试内容。\n" * 50000  # 约1MB
        test_file.write_text(large_content, encoding='utf-8')
        
        # 上传文件
        with open(test_file, 'rb') as f:
            response = await async_client.post(
                "/api/v1/upload",
                files={"file": ("large.txt", f, "text/plain")}
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "session_id" in data
    
    @pytest.mark.asyncio
    async def test_upload_empty_file(self, async_client: AsyncClient, temp_dir: Path):
        """测试上传空文件"""
        # 创建空文件
        test_file = temp_dir / "empty.txt"
        test_file.write_text("", encoding='utf-8')
        
        # 上传文件
        with open(test_file, 'rb') as f:
            response = await async_client.post(
                "/api/v1/upload",
                files={"file": ("empty.txt", f, "text/plain")}
            )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["success"] is False
    
    @pytest.mark.asyncio
    async def test_upload_unsupported_file_type(self, async_client: AsyncClient, temp_dir: Path):
        """测试上传不支持的文件类型"""
        # 创建PDF文件（模拟）
        test_file = temp_dir / "test.pdf"
        test_file.write_bytes(b"PDF content")
        
        # 上传文件
        with open(test_file, 'rb') as f:
            response = await async_client.post(
                "/api/v1/upload",
                files={"file": ("test.pdf", f, "application/pdf")}
            )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["success"] is False


class TestTextFileOperationsAPI:
    """TEXT文件操作API测试"""
    
    @pytest.fixture
    async def text_session(self, async_client: AsyncClient, temp_dir: Path):
        """创建TEXT文件会话"""
        # 创建测试文件
        test_file = temp_dir / "test.txt"
        test_content = "原始内容\n第二行内容\n第三行包含特殊字符：@#$%^&*()"
        test_file.write_text(test_content, encoding='utf-8')
        
        # 上传文件
        with open(test_file, 'rb') as f:
            response = await async_client.post(
                "/api/v1/upload",
                files={"file": ("test.txt", f, "text/plain")}
            )
        
        data = response.json()
        return data["session_id"]
    
    @pytest.mark.asyncio
    async def test_read_text_file_content(self, async_client: AsyncClient, text_session: str):
        """测试读取TEXT文件内容"""
        response = await async_client.get(f"/api/v1/files/{text_session}/content")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "content" in data
        assert "原始内容" in data["content"]
        assert "第二行内容" in data["content"]
        assert "特殊字符" in data["content"]
    
    @pytest.mark.asyncio
    async def test_update_text_file_content(self, async_client: AsyncClient, text_session: str):
        """测试更新TEXT文件内容"""
        new_content = "更新后的内容\n新的第二行\n包含emoji: 😀🎉"
        
        response = await async_client.put(
            f"/api/v1/files/{text_session}/content",
            json={"content": new_content}
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # 验证内容已更新
        read_response = await async_client.get(f"/api/v1/files/{text_session}/content")
        read_data = read_response.json()
        assert read_data["content"] == new_content
    
    @pytest.mark.asyncio
    async def test_update_to_empty_content(self, async_client: AsyncClient, text_session: str):
        """测试更新为空内容"""
        response = await async_client.put(
            f"/api/v1/files/{text_session}/content",
            json={"content": ""}
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # 验证内容已清空
        read_response = await async_client.get(f"/api/v1/files/{text_session}/content")
        read_data = read_response.json()
        assert read_data["content"] == ""
    
    @pytest.mark.asyncio
    async def test_read_nonexistent_session(self, async_client: AsyncClient):
        """测试读取不存在的会话"""
        response = await async_client.get("/api/v1/files/nonexistent-session/content")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["success"] is False


class TestTextSearchAPI:
    """TEXT文件搜索API测试"""
    
    @pytest.fixture
    async def search_session(self, async_client: AsyncClient, temp_dir: Path):
        """创建用于搜索测试的会话"""
        # 创建包含多种内容的测试文件
        test_file = temp_dir / "search_test.txt"
        test_content = """第一行：包含测试内容
第二行：Test Content in English
第三行：包含TEST大写内容
第四行：email@example.com
第五行：电话号码 123-456-7890
第六行：包含test小写内容
第七行：这是一个完整的单词test，不是testing
第八行：包含特殊字符 @#$%^&*()
第九行：重复的测试内容
第十行：最后一行内容"""
        test_file.write_text(test_content, encoding='utf-8')
        
        # 上传文件
        with open(test_file, 'rb') as f:
            response = await async_client.post(
                "/api/v1/upload",
                files={"file": ("search_test.txt", f, "text/plain")}
            )
        
        data = response.json()
        return data["session_id"]
    
    @pytest.mark.asyncio
    async def test_basic_text_search(self, async_client: AsyncClient, search_session: str):
        """测试基本文本搜索"""
        search_request = {
            "query": "测试",
            "case_sensitive": False,
            "use_regex": False,
            "whole_word": False
        }
        
        response = await async_client.post(
            f"/api/v1/search-replace/{search_session}/search",
            json=search_request
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "results" in data
        assert len(data["results"]) > 0
        
        # 验证搜索结果包含正确信息
        result = data["results"][0]
        assert "file_path" in result
        assert "line_number" in result
        assert "column_start" in result
        assert "column_end" in result
        assert "matched_text" in result
        assert "context" in result
        assert result["matched_text"] == "测试"
    
    @pytest.mark.asyncio
    async def test_case_sensitive_search(self, async_client: AsyncClient, search_session: str):
        """测试大小写敏感搜索"""
        # 搜索大写TEST
        search_request = {
            "query": "TEST",
            "case_sensitive": True,
            "use_regex": False,
            "whole_word": False
        }
        
        response = await async_client.post(
            f"/api/v1/search-replace/{search_session}/search",
            json=search_request
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # 应该只找到大写的TEST，不包括小写的test
        test_results = [r for r in data["results"] if r["matched_text"] == "TEST"]
        assert len(test_results) > 0
        
        # 验证没有小写的test
        lowercase_results = [r for r in data["results"] if r["matched_text"] == "test"]
        assert len(lowercase_results) == 0
    
    @pytest.mark.asyncio
    async def test_case_insensitive_search(self, async_client: AsyncClient, search_session: str):
        """测试大小写不敏感搜索"""
        search_request = {
            "query": "test",
            "case_sensitive": False,
            "use_regex": False,
            "whole_word": False
        }
        
        response = await async_client.post(
            f"/api/v1/search-replace/{search_session}/search",
            json=search_request
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # 应该找到所有大小写变体
        matched_texts = [r["matched_text"] for r in data["results"]]
        assert "test" in matched_texts or "Test" in matched_texts or "TEST" in matched_texts
    
    @pytest.mark.asyncio
    async def test_regex_search(self, async_client: AsyncClient, search_session: str):
        """测试正则表达式搜索"""
        # 搜索邮箱地址
        search_request = {
            "query": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "case_sensitive": False,
            "use_regex": True,
            "whole_word": False
        }
        
        response = await async_client.post(
            f"/api/v1/search-replace/{search_session}/search",
            json=search_request
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["results"]) > 0
        
        # 验证找到的是邮箱地址
        result = data["results"][0]
        assert "@" in result["matched_text"]
        assert ".com" in result["matched_text"]
    
    @pytest.mark.asyncio
    async def test_whole_word_search(self, async_client: AsyncClient, search_session: str):
        """测试整词匹配搜索"""
        search_request = {
            "query": "test",
            "case_sensitive": False,
            "use_regex": False,
            "whole_word": True
        }
        
        response = await async_client.post(
            f"/api/v1/search-replace/{search_session}/search",
            json=search_request
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # 验证只匹配完整单词，不包含testing等部分匹配
        for result in data["results"]:
            matched_text = result["matched_text"].lower()
            assert matched_text == "test"
    
    @pytest.mark.asyncio
    async def test_search_no_results(self, async_client: AsyncClient, search_session: str):
        """测试搜索无结果"""
        search_request = {
            "query": "不存在的内容xyz123",
            "case_sensitive": False,
            "use_regex": False,
            "whole_word": False
        }
        
        response = await async_client.post(
            f"/api/v1/search-replace/{search_session}/search",
            json=search_request
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 0
    
    @pytest.mark.asyncio
    async def test_search_invalid_regex(self, async_client: AsyncClient, search_session: str):
        """测试无效正则表达式"""
        search_request = {
            "query": "[invalid regex",
            "case_sensitive": False,
            "use_regex": True,
            "whole_word": False
        }
        
        response = await async_client.post(
            f"/api/v1/search-replace/{search_session}/search",
            json=search_request
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["success"] is False


class TestTextReplaceAPI:
    """TEXT文件替换API测试"""
    
    @pytest.fixture
    async def replace_session(self, async_client: AsyncClient, temp_dir: Path):
        """创建用于替换测试的会话"""
        # 创建包含待替换内容的测试文件
        test_file = temp_dir / "replace_test.txt"
        test_content = """第一行：包含旧文本内容
第二行：Old Content in English
第三行：包含OLD大写内容
第四行：old小写内容
第五行：这是一个完整的单词old，不是older
第六行：重复的旧文本内容
第七行：最后一行"""
        test_file.write_text(test_content, encoding='utf-8')
        
        # 上传文件
        with open(test_file, 'rb') as f:
            response = await async_client.post(
                "/api/v1/upload",
                files={"file": ("replace_test.txt", f, "text/plain")}
            )
        
        data = response.json()
        return data["session_id"]
    
    @pytest.mark.asyncio
    async def test_basic_text_replace(self, async_client: AsyncClient, replace_session: str):
        """测试基本文本替换"""
        replace_request = {
            "query": "旧文本",
            "replacement": "新文本",
            "case_sensitive": False,
            "use_regex": False,
            "whole_word": False
        }
        
        response = await async_client.post(
            f"/api/v1/search-replace/{replace_session}/replace",
            json=replace_request
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "replacements_made" in data
        assert data["replacements_made"] > 0
        
        # 验证内容已被替换
        content_response = await async_client.get(f"/api/v1/files/{replace_session}/content")
        content_data = content_response.json()
        assert "新文本" in content_data["content"]
        assert "旧文本" not in content_data["content"]
    
    @pytest.mark.asyncio
    async def test_replace_to_empty_string(self, async_client: AsyncClient, replace_session: str):
        """测试替换为空字符串（删除）"""
        replace_request = {
            "query": "Old Content",
            "replacement": "",
            "case_sensitive": False,
            "use_regex": False,
            "whole_word": False
        }
        
        response = await async_client.post(
            f"/api/v1/search-replace/{replace_session}/replace",
            json=replace_request
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["replacements_made"] > 0
        
        # 验证内容已被删除
        content_response = await async_client.get(f"/api/v1/files/{replace_session}/content")
        content_data = content_response.json()
        assert "Old Content" not in content_data["content"]
    
    @pytest.mark.asyncio
    async def test_case_sensitive_replace(self, async_client: AsyncClient, replace_session: str):
        """测试大小写敏感替换"""
        replace_request = {
            "query": "OLD",
            "replacement": "NEW",
            "case_sensitive": True,
            "use_regex": False,
            "whole_word": False
        }
        
        response = await async_client.post(
            f"/api/v1/search-replace/{replace_session}/replace",
            json=replace_request
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["replacements_made"] > 0
        
        # 验证只有大写的OLD被替换
        content_response = await async_client.get(f"/api/v1/files/{replace_session}/content")
        content_data = content_response.json()
        assert "NEW" in content_data["content"]
        assert "old" in content_data["content"]  # 小写的old应该保留
    
    @pytest.mark.asyncio
    async def test_regex_replace(self, async_client: AsyncClient, replace_session: str):
        """测试正则表达式替换"""
        replace_request = {
            "query": r"第(\d+)行",
            "replacement": r"Line \1",
            "case_sensitive": False,
            "use_regex": True,
            "whole_word": False
        }
        
        response = await async_client.post(
            f"/api/v1/search-replace/{replace_session}/replace",
            json=replace_request
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["replacements_made"] > 0
        
        # 验证正则表达式替换生效
        content_response = await async_client.get(f"/api/v1/files/{replace_session}/content")
        content_data = content_response.json()
        assert "Line 1" in content_data["content"]
        assert "Line 2" in content_data["content"]
    
    @pytest.mark.asyncio
    async def test_whole_word_replace(self, async_client: AsyncClient, replace_session: str):
        """测试整词替换"""
        replace_request = {
            "query": "old",
            "replacement": "new",
            "case_sensitive": False,
            "use_regex": False,
            "whole_word": True
        }
        
        response = await async_client.post(
            f"/api/v1/search-replace/{replace_session}/replace",
            json=replace_request
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["replacements_made"] > 0
        
        # 验证只有完整单词被替换
        content_response = await async_client.get(f"/api/v1/files/{replace_session}/content")
        content_data = content_response.json()
        assert "new" in content_data["content"]
        # older等包含old的词不应该被替换
    
    @pytest.mark.asyncio
    async def test_replace_no_matches(self, async_client: AsyncClient, replace_session: str):
        """测试替换无匹配项"""
        replace_request = {
            "query": "不存在的内容xyz123",
            "replacement": "新内容",
            "case_sensitive": False,
            "use_regex": False,
            "whole_word": False
        }
        
        response = await async_client.post(
            f"/api/v1/search-replace/{replace_session}/replace",
            json=replace_request
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["replacements_made"] == 0
    
    @pytest.mark.asyncio
    async def test_replace_invalid_session(self, async_client: AsyncClient):
        """测试替换不存在的会话"""
        replace_request = {
            "query": "test",
            "replacement": "new",
            "case_sensitive": False,
            "use_regex": False,
            "whole_word": False
        }
        
        response = await async_client.post(
            "/api/v1/search-replace/nonexistent-session/replace",
            json=replace_request
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["success"] is False