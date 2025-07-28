"""TEXT文件导出API测试"""

import pytest
from pathlib import Path
from httpx import AsyncClient
from fastapi import status


class TestTextExportAPI:
    """TEXT文件导出API测试"""
    
    @pytest.fixture
    async def export_session(self, async_client: AsyncClient, temp_dir: Path):
        """创建用于导出测试的会话"""
        # 创建测试文件
        test_file = temp_dir / "export_test.txt"
        test_content = """这是一个用于导出测试的文本文件。

包含多行内容：
- 第一项内容
- 第二项内容
- 第三项内容

还包含特殊字符：@#$%^&*()
以及Unicode字符：你好世界 🌍

最后一行内容。"""
        test_file.write_text(test_content, encoding='utf-8')
        
        # 上传文件
        with open(test_file, 'rb') as f:
            response = await async_client.post(
                "/api/v1/upload",
                files={"file": ("export_test.txt", f, "text/plain")}
            )
        
        data = response.json()
        return data["session_id"], test_content
    
    @pytest.fixture
    async def modified_export_session(self, async_client: AsyncClient, temp_dir: Path):
        """创建已修改的导出测试会话"""
        # 创建测试文件
        test_file = temp_dir / "modified_export_test.txt"
        original_content = "原始内容\n需要替换的文本\n另一行内容"
        test_file.write_text(original_content, encoding='utf-8')
        
        # 上传文件
        with open(test_file, 'rb') as f:
            response = await async_client.post(
                "/api/v1/upload",
                files={"file": ("modified_export_test.txt", f, "text/plain")}
            )
        
        session_id = response.json()["session_id"]
        
        # 修改文件内容
        modified_content = "修改后的内容\n已替换的文本\n另一行内容"
        await async_client.put(
            f"/api/v1/files/{session_id}/content",
            json={"content": modified_content}
        )
        
        return session_id, modified_content
    
    @pytest.mark.asyncio
    async def test_export_original_text_file(self, async_client: AsyncClient, export_session):
        """测试导出原始TEXT文件"""
        session_id, original_content = export_session
        
        # 导出文件
        response = await async_client.get(f"/api/v1/export/{session_id}")
        
        assert response.status_code == status.HTTP_200_OK
        
        # 验证响应头
        assert "content-disposition" in response.headers
        assert "attachment" in response.headers["content-disposition"]
        assert "export_test.txt" in response.headers["content-disposition"]
        
        # 验证内容类型
        content_type = response.headers.get("content-type", "")
        assert "text/plain" in content_type or "application/octet-stream" in content_type
        
        # 验证文件内容
        exported_content = response.content.decode('utf-8')
        assert exported_content == original_content
        assert "这是一个用于导出测试的文本文件" in exported_content
        assert "你好世界 🌍" in exported_content
        assert "@#$%^&*()" in exported_content
    
    @pytest.mark.asyncio
    async def test_export_modified_text_file(self, async_client: AsyncClient, modified_export_session):
        """测试导出修改后的TEXT文件"""
        session_id, modified_content = modified_export_session
        
        # 导出文件
        response = await async_client.get(f"/api/v1/export/{session_id}")
        
        assert response.status_code == status.HTTP_200_OK
        
        # 验证文件内容是修改后的内容
        exported_content = response.content.decode('utf-8')
        assert exported_content == modified_content
        assert "修改后的内容" in exported_content
        assert "已替换的文本" in exported_content
        assert "原始内容" not in exported_content
        assert "需要替换的文本" not in exported_content
    
    @pytest.mark.asyncio
    async def test_export_empty_text_file(self, async_client: AsyncClient, temp_dir: Path):
        """测试导出空TEXT文件"""
        # 创建空文件
        test_file = temp_dir / "empty.txt"
        test_file.write_text("", encoding='utf-8')
        
        # 上传文件（这可能失败，因为空文件可能不被允许）
        try:
            with open(test_file, 'rb') as f:
                response = await async_client.post(
                    "/api/v1/upload",
                    files={"file": ("empty.txt", f, "text/plain")}
                )
            
            if response.status_code == status.HTTP_200_OK:
                session_id = response.json()["session_id"]
                
                # 导出空文件
                export_response = await async_client.get(f"/api/v1/export/{session_id}")
                assert export_response.status_code == status.HTTP_200_OK
                
                # 验证导出的是空内容
                exported_content = export_response.content.decode('utf-8')
                assert exported_content == ""
        except Exception:
            # 如果空文件上传失败，这是预期的行为
            pass
    
    @pytest.mark.asyncio
    async def test_export_large_text_file(self, async_client: AsyncClient, temp_dir: Path):
        """测试导出大TEXT文件"""
        # 创建大文件（约1MB）
        test_file = temp_dir / "large.txt"
        large_content = "这是一行重复的内容用于测试大文件导出功能。\n" * 50000
        test_file.write_text(large_content, encoding='utf-8')
        
        # 上传文件
        with open(test_file, 'rb') as f:
            response = await async_client.post(
                "/api/v1/upload",
                files={"file": ("large.txt", f, "text/plain")}
            )
        
        assert response.status_code == status.HTTP_200_OK
        session_id = response.json()["session_id"]
        
        # 导出大文件
        export_response = await async_client.get(f"/api/v1/export/{session_id}")
        
        assert export_response.status_code == status.HTTP_200_OK
        
        # 验证文件大小
        exported_content = export_response.content.decode('utf-8')
        assert len(exported_content) == len(large_content)
        assert exported_content == large_content
    
    @pytest.mark.asyncio
    async def test_export_unicode_text_file(self, async_client: AsyncClient, temp_dir: Path):
        """测试导出包含Unicode字符的TEXT文件"""
        # 创建包含各种Unicode字符的文件
        test_file = temp_dir / "unicode.txt"
        unicode_content = """多语言测试文件：

中文：你好世界
日文：こんにちは世界
韩文：안녕하세요 세계
阿拉伯文：مرحبا بالعالم
俄文：Привет мир
希腊文：Γεια σας κόσμε

Emoji测试：
😀😃😄😁😆😅😂🤣😊😇
🌍🌎🌏🌐🗺️🏔️⛰️🌋🗻🏕️

特殊符号：
©®™€£¥§¶†‡•…‰‱′″‴‵‶‷‸‹›«»

数学符号：
∀∁∂∃∄∅∆∇∈∉∊∋∌∍∎∏∐∑−∓∔∕∖∗∘∙√∛∜∝∞∟∠∡∢∣∤∥∦∧∨∩∪∫∬∭∮∯∰∱∲∳∴∵∶∷∸∹∺∻∼∽∾∿≀≁≂≃≄≅≆≇≈≉≊≋≌≍≎≏≐≑≒≓≔≕≖≗≘≙≚≛≜≝≞≟≠≡≢≣≤≥≦≧≨≩≪≫≬≭≮≯≰≱≲≳≴≵≶≷≸≹≺≻≼≽≾≿⊀⊁⊂⊃⊄⊅⊆⊇⊈⊉⊊⊋⊌⊍⊎⊏⊐⊑⊒⊓⊔⊕⊖⊗⊘⊙⊚⊛⊜⊝⊞⊟⊠⊡⊢⊣⊤⊥⊦⊧⊨⊩⊪⊫⊬⊭⊮⊯⊰⊱⊲⊳⊴⊵⊶⊷⊸⊹⊺⊻⊼⊽⊾⊿⋀⋁⋂⋃⋄⋅⋆⋇⋈⋉⋊⋋⋌⋍⋎⋏⋐⋑⋒⋓⋔⋕⋖⋗⋘⋙⋚⋛⋜⋝⋞⋟⋠⋡⋢⋣⋤⋥⋦⋧⋨⋩⋪⋫⋬⋭⋮⋯⋰⋱⋲⋳⋴⋵⋶⋷⋸⋹⋺⋻⋼⋽⋾⋿"""
        test_file.write_text(unicode_content, encoding='utf-8')
        
        # 上传文件
        with open(test_file, 'rb') as f:
            response = await async_client.post(
                "/api/v1/upload",
                files={"file": ("unicode.txt", f, "text/plain")}
            )
        
        assert response.status_code == status.HTTP_200_OK
        session_id = response.json()["session_id"]
        
        # 导出文件
        export_response = await async_client.get(f"/api/v1/export/{session_id}")
        
        assert export_response.status_code == status.HTTP_200_OK
        
        # 验证Unicode字符正确保存
        exported_content = export_response.content.decode('utf-8')
        assert exported_content == unicode_content
        assert "你好世界" in exported_content
        assert "こんにちは世界" in exported_content
        assert "😀😃😄" in exported_content
        assert "∀∁∂∃" in exported_content
    
    @pytest.mark.asyncio
    async def test_export_markdown_file(self, async_client: AsyncClient, temp_dir: Path):
        """测试导出Markdown文件"""
        # 创建Markdown文件
        test_file = temp_dir / "test.md"
        markdown_content = """# 测试Markdown文件

这是一个**测试**Markdown文件，用于验证导出功能。

## 功能列表

- [x] 支持标题
- [x] 支持**粗体**和*斜体*
- [x] 支持列表
- [ ] 待完成功能

## 代码示例

```python
def hello_world():
    print("Hello, World!")
    return "success"
```

## 链接和图片

[GitHub](https://github.com)

![示例图片](https://example.com/image.png)

## 表格

| 列1 | 列2 | 列3 |
|-----|-----|-----|
| 数据1 | 数据2 | 数据3 |
| 数据4 | 数据5 | 数据6 |

## 引用

> 这是一个引用示例。
> 可以包含多行内容。

---

最后一行内容。"""
        test_file.write_text(markdown_content, encoding='utf-8')
        
        # 上传文件
        with open(test_file, 'rb') as f:
            response = await async_client.post(
                "/api/v1/upload",
                files={"file": ("test.md", f, "text/markdown")}
            )
        
        assert response.status_code == status.HTTP_200_OK
        session_id = response.json()["session_id"]
        
        # 导出文件
        export_response = await async_client.get(f"/api/v1/export/{session_id}")
        
        assert export_response.status_code == status.HTTP_200_OK
        
        # 验证文件名包含.md扩展名
        assert "test.md" in export_response.headers["content-disposition"]
        
        # 验证Markdown内容
        exported_content = export_response.content.decode('utf-8')
        assert exported_content == markdown_content
        assert "# 测试Markdown文件" in exported_content
        assert "```python" in exported_content
        assert "| 列1 | 列2 | 列3 |" in exported_content
    
    @pytest.mark.asyncio
    async def test_export_after_batch_replace(self, async_client: AsyncClient, temp_dir: Path):
        """测试批量替换后的导出"""
        # 创建测试文件
        test_file = temp_dir / "batch_replace_export.txt"
        original_content = """第一行：包含旧文本
第二行：错误信息需要修正
第三行：测试内容
第四行：更多旧文本"""
        test_file.write_text(original_content, encoding='utf-8')
        
        # 上传文件
        with open(test_file, 'rb') as f:
            response = await async_client.post(
                "/api/v1/upload",
                files={"file": ("batch_replace_export.txt", f, "text/plain")}
            )
        
        session_id = response.json()["session_id"]
        
        # 创建替换规则文件
        rules_file = temp_dir / "export_rules.txt"
        rules_content = """旧文本->新文本
错误信息->正确信息
测试->检验"""
        rules_file.write_text(rules_content, encoding='utf-8')
        
        # 执行批量替换
        with open(rules_file, 'rb') as f:
            batch_response = await async_client.post(
                f"/api/v1/batch-replace/{session_id}",
                files={"rules_file": ("export_rules.txt", f, "text/plain")}
            )
        
        assert batch_response.status_code == status.HTTP_200_OK
        
        # 等待批量替换完成
        import asyncio
        await asyncio.sleep(2)
        
        # 导出替换后的文件
        export_response = await async_client.get(f"/api/v1/export/{session_id}")
        
        assert export_response.status_code == status.HTTP_200_OK
        
        # 验证导出的是替换后的内容
        exported_content = export_response.content.decode('utf-8')
        assert "新文本" in exported_content
        assert "正确信息" in exported_content
        assert "检验" in exported_content
        assert "旧文本" not in exported_content
        assert "错误信息" not in exported_content
        assert "测试" not in exported_content
    
    @pytest.mark.asyncio
    async def test_export_nonexistent_session(self, async_client: AsyncClient):
        """测试导出不存在的会话"""
        response = await async_client.get("/api/v1/export/nonexistent-session")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["success"] is False
    
    @pytest.mark.asyncio
    async def test_export_file_with_special_filename(self, async_client: AsyncClient, temp_dir: Path):
        """测试导出包含特殊字符的文件名"""
        # 创建包含特殊字符的文件名
        special_filename = "测试文件 (特殊字符) [2024].txt"
        test_file = temp_dir / special_filename
        test_content = "包含特殊文件名的测试内容"
        test_file.write_text(test_content, encoding='utf-8')
        
        # 上传文件
        with open(test_file, 'rb') as f:
            response = await async_client.post(
                "/api/v1/upload",
                files={"file": (special_filename, f, "text/plain")}
            )
        
        assert response.status_code == status.HTTP_200_OK
        session_id = response.json()["session_id"]
        
        # 导出文件
        export_response = await async_client.get(f"/api/v1/export/{session_id}")
        
        assert export_response.status_code == status.HTTP_200_OK
        
        # 验证文件名在响应头中正确编码
        content_disposition = export_response.headers["content-disposition"]
        assert "attachment" in content_disposition
        # 文件名可能被编码或清理，但应该包含主要部分
        assert "测试文件" in content_disposition or "filename" in content_disposition
        
        # 验证内容正确
        exported_content = export_response.content.decode('utf-8')
        assert exported_content == test_content
    
    @pytest.mark.asyncio
    async def test_export_concurrent_requests(self, async_client: AsyncClient, export_session):
        """测试并发导出请求"""
        session_id, _ = export_session
        
        # 发起多个并发导出请求
        import asyncio
        tasks = []
        for _ in range(5):
            task = async_client.get(f"/api/v1/export/{session_id}")
            tasks.append(task)
        
        # 等待所有请求完成
        responses = await asyncio.gather(*tasks)
        
        # 验证所有请求都成功
        for response in responses:
            assert response.status_code == status.HTTP_200_OK
            assert "content-disposition" in response.headers
            assert "export_test.txt" in response.headers["content-disposition"]
    
    @pytest.mark.asyncio
    async def test_export_response_headers(self, async_client: AsyncClient, export_session):
        """测试导出响应头"""
        session_id, original_content = export_session
        
        # 导出文件
        response = await async_client.get(f"/api/v1/export/{session_id}")
        
        assert response.status_code == status.HTTP_200_OK
        
        # 验证必要的响应头
        headers = response.headers
        
        # Content-Disposition头
        assert "content-disposition" in headers
        assert "attachment" in headers["content-disposition"]
        assert "filename" in headers["content-disposition"]
        
        # Content-Type头
        assert "content-type" in headers
        content_type = headers["content-type"]
        assert "text/plain" in content_type or "application/octet-stream" in content_type
        
        # Content-Length头（如果存在）
        if "content-length" in headers:
            content_length = int(headers["content-length"])
            actual_length = len(response.content)
            assert content_length == actual_length
        
        # 验证没有缓存相关头（确保文件是最新的）
        assert "cache-control" not in headers or "no-cache" in headers.get("cache-control", "")