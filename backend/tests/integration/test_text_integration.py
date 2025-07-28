"""TEXT文件功能集成测试"""

import pytest
from pathlib import Path
from httpx import AsyncClient
from fastapi import status
import asyncio
import json
from datetime import datetime


class TestTextIntegration:
    """TEXT文件功能集成测试"""
    
    @pytest.fixture
    async def sample_text_files(self, temp_dir: Path):
        """创建示例TEXT文件"""
        files = {}
        
        # 简单文本文件
        simple_file = temp_dir / "simple.txt"
        simple_content = "这是一个简单的文本文件。\n包含基本的文本内容。"
        simple_file.write_text(simple_content, encoding='utf-8')
        files['simple'] = (simple_file, simple_content)
        
        # Markdown文件
        md_file = temp_dir / "document.md"
        md_content = """# 文档标题

这是一个**Markdown**文档，用于测试。

## 功能列表

- [x] 支持标题
- [x] 支持**粗体**和*斜体*
- [ ] 待完成功能

## 代码示例

```python
def hello():
    print("Hello, World!")
```

## 链接

[GitHub](https://github.com)

---

最后一行。"""
        md_file.write_text(md_content, encoding='utf-8')
        files['markdown'] = (md_file, md_content)
        
        # 包含特殊字符的文件
        special_file = temp_dir / "special.txt"
        special_content = """特殊字符测试文件：

中文：你好世界
日文：こんにちは世界
韩文：안녕하세요 세계
Emoji：😀😃😄😁😆😅😂🤣
特殊符号：©®™€£¥§¶†‡•…‰‱
数学符号：∀∁∂∃∄∅∆∇∈∉∊∋∌∍∎∏

编程符号：
{"key": "value", "array": [1, 2, 3]}
<tag>content</tag>
/* comment */
// another comment

路径测试：
C:\\Windows\\System32
/usr/local/bin
~/Documents/file.txt

特殊字符串：
'single quotes'
"double quotes"
`backticks`
\"escaped quotes\"
\n\t\r\n
结束。"""
        special_file.write_text(special_content, encoding='utf-8')
        files['special'] = (special_file, special_content)
        
        return files
    
    @pytest.fixture
    async def replacement_rules_file(self, temp_dir: Path):
        """创建替换规则文件"""
        rules_file = temp_dir / "rules.txt"
        rules_content = """# 基本替换规则
文本->内容
测试->检验
简单->基础

# 特殊字符替换
你好->Hello
世界->World
😀->🌟

# 编程相关替换
print->console.log
def->function
Hello, World!->Hello, Universe!

# 标点符号替换
。->.
，->,
：->:"""
        rules_file.write_text(rules_content, encoding='utf-8')
        return rules_file
    
    @pytest.mark.asyncio
    async def test_complete_text_workflow(self, async_client: AsyncClient, sample_text_files, replacement_rules_file):
        """测试完整的TEXT文件工作流程"""
        simple_file, simple_content = sample_text_files['simple']
        
        # 1. 上传文件
        with open(simple_file, 'rb') as f:
            upload_response = await async_client.post(
                "/api/v1/upload",
                files={"file": ("simple.txt", f, "text/plain")}
            )
        
        assert upload_response.status_code == status.HTTP_200_OK
        upload_data = upload_response.json()
        session_id = upload_data["session_id"]
        assert upload_data["file_type"] == "TEXT"
        
        # 2. 获取会话信息
        session_response = await async_client.get(f"/api/v1/sessions/{session_id}")
        assert session_response.status_code == status.HTTP_200_OK
        session_data = session_response.json()
        assert session_data["session"]["file_type"] == "TEXT"
        assert session_data["session"]["original_filename"] == "simple.txt"
        
        # 3. 读取文件内容
        read_response = await async_client.get(f"/api/v1/files/{session_id}/content")
        assert read_response.status_code == status.HTTP_200_OK
        read_data = read_response.json()
        assert read_data["content"] == simple_content
        
        # 4. 搜索文本
        search_response = await async_client.post(
            f"/api/v1/search-replace/{session_id}/search",
            json={
                "query": "文本",
                "case_sensitive": False,
                "use_regex": False,
                "whole_word": False
            }
        )
        assert search_response.status_code == status.HTTP_200_OK
        search_data = search_response.json()
        assert search_data["success"] is True
        assert len(search_data["results"]) > 0
        
        # 5. 执行单次替换
        replace_response = await async_client.post(
            f"/api/v1/search-replace/{session_id}/replace",
            json={
                "query": "简单",
                "replacement": "基础",
                "case_sensitive": False,
                "use_regex": False,
                "whole_word": False
            }
        )
        assert replace_response.status_code == status.HTTP_200_OK
        replace_data = replace_response.json()
        assert replace_data["success"] is True
        assert replace_data["replacements_made"] > 0
        
        # 6. 验证替换结果
        read_response2 = await async_client.get(f"/api/v1/files/{session_id}/content")
        modified_content = read_response2.json()["content"]
        assert "基础" in modified_content
        assert "简单" not in modified_content
        
        # 7. 执行批量替换
        with open(replacement_rules_file, 'rb') as f:
            batch_response = await async_client.post(
                f"/api/v1/batch-replace/{session_id}",
                files={"rules_file": ("rules.txt", f, "text/plain")}
            )
        
        assert batch_response.status_code == status.HTTP_200_OK
        batch_data = batch_response.json()
        assert batch_data["success"] is True
        task_id = batch_data["task_id"]
        
        # 8. 监控批量替换进度
        max_attempts = 30
        for attempt in range(max_attempts):
            progress_response = await async_client.get(f"/api/v1/batch-replace/{session_id}/progress/{task_id}")
            if progress_response.status_code == status.HTTP_200_OK:
                progress_data = progress_response.json()
                if progress_data.get("status") == "completed":
                    break
            await asyncio.sleep(1)
        else:
            pytest.fail("批量替换未在预期时间内完成")
        
        # 9. 验证批量替换结果
        read_response3 = await async_client.get(f"/api/v1/files/{session_id}/content")
        final_content = read_response3.json()["content"]
        assert "内容" in final_content  # "文本" -> "内容"
        assert "检验" in final_content  # "测试" -> "检验"
        
        # 10. 导出文件
        export_response = await async_client.get(f"/api/v1/export/{session_id}")
        assert export_response.status_code == status.HTTP_200_OK
        exported_content = export_response.content.decode('utf-8')
        assert exported_content == final_content
        
        # 11. 删除会话
        delete_response = await async_client.delete(f"/api/v1/sessions/{session_id}")
        assert delete_response.status_code == status.HTTP_200_OK
        
        # 12. 验证会话已删除
        final_session_response = await async_client.get(f"/api/v1/sessions/{session_id}")
        assert final_session_response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_markdown_file_workflow(self, async_client: AsyncClient, sample_text_files, replacement_rules_file):
        """测试Markdown文件工作流程"""
        md_file, md_content = sample_text_files['markdown']
        
        # 上传Markdown文件
        with open(md_file, 'rb') as f:
            upload_response = await async_client.post(
                "/api/v1/upload",
                files={"file": ("document.md", f, "text/markdown")}
            )
        
        assert upload_response.status_code == status.HTTP_200_OK
        session_id = upload_response.json()["session_id"]
        
        # 验证Markdown内容
        read_response = await async_client.get(f"/api/v1/files/{session_id}/content")
        content = read_response.json()["content"]
        assert "# 文档标题" in content
        assert "**Markdown**" in content
        assert "```python" in content
        
        # 搜索Markdown特定内容
        search_response = await async_client.post(
            f"/api/v1/search-replace/{session_id}/search",
            json={
                "query": "def hello",
                "case_sensitive": False,
                "use_regex": False,
                "whole_word": False
            }
        )
        assert search_response.status_code == status.HTTP_200_OK
        assert len(search_response.json()["results"]) > 0
        
        # 执行批量替换
        with open(replacement_rules_file, 'rb') as f:
            batch_response = await async_client.post(
                f"/api/v1/batch-replace/{session_id}",
                files={"rules_file": ("rules.txt", f, "text/plain")}
            )
        
        assert batch_response.status_code == status.HTTP_200_OK
        task_id = batch_response.json()["task_id"]
        
        # 等待完成
        await asyncio.sleep(3)
        
        # 验证替换结果
        read_response2 = await async_client.get(f"/api/v1/files/{session_id}/content")
        modified_content = read_response2.json()["content"]
        assert "function hello" in modified_content  # "def" -> "function"
        assert "console.log" in modified_content  # "print" -> "console.log"
        assert "Hello, Universe!" in modified_content  # "Hello, World!" -> "Hello, Universe!"
        
        # 导出Markdown文件
        export_response = await async_client.get(f"/api/v1/export/{session_id}")
        assert export_response.status_code == status.HTTP_200_OK
        assert "document.md" in export_response.headers["content-disposition"]
    
    @pytest.mark.asyncio
    async def test_special_characters_workflow(self, async_client: AsyncClient, sample_text_files, replacement_rules_file):
        """测试特殊字符文件工作流程"""
        special_file, special_content = sample_text_files['special']
        
        # 上传包含特殊字符的文件
        with open(special_file, 'rb') as f:
            upload_response = await async_client.post(
                "/api/v1/upload",
                files={"file": ("special.txt", f, "text/plain")}
            )
        
        assert upload_response.status_code == status.HTTP_200_OK
        session_id = upload_response.json()["session_id"]
        
        # 验证特殊字符正确读取
        read_response = await async_client.get(f"/api/v1/files/{session_id}/content")
        content = read_response.json()["content"]
        assert "你好世界" in content
        assert "😀😃😄" in content
        assert "∀∁∂∃" in content
        assert "©®™€" in content
        
        # 搜索Unicode字符
        search_response = await async_client.post(
            f"/api/v1/search-replace/{session_id}/search",
            json={
                "query": "😀",
                "case_sensitive": False,
                "use_regex": False,
                "whole_word": False
            }
        )
        assert search_response.status_code == status.HTTP_200_OK
        assert len(search_response.json()["results"]) > 0
        
        # 执行包含Unicode的批量替换
        with open(replacement_rules_file, 'rb') as f:
            batch_response = await async_client.post(
                f"/api/v1/batch-replace/{session_id}",
                files={"rules_file": ("rules.txt", f, "text/plain")}
            )
        
        assert batch_response.status_code == status.HTTP_200_OK
        
        # 等待完成
        await asyncio.sleep(3)
        
        # 验证Unicode替换结果
        read_response2 = await async_client.get(f"/api/v1/files/{session_id}/content")
        modified_content = read_response2.json()["content"]
        assert "Hello" in modified_content  # "你好" -> "Hello"
        assert "World" in modified_content  # "世界" -> "World"
        assert "🌟" in modified_content  # "😀" -> "🌟"
        
        # 导出并验证特殊字符保持完整
        export_response = await async_client.get(f"/api/v1/export/{session_id}")
        assert export_response.status_code == status.HTTP_200_OK
        exported_content = export_response.content.decode('utf-8')
        assert "🌟" in exported_content
        assert "Hello" in exported_content
        assert "World" in exported_content
    
    @pytest.mark.asyncio
    async def test_multiple_files_concurrent_processing(self, async_client: AsyncClient, sample_text_files, replacement_rules_file):
        """测试多文件并发处理"""
        session_ids = []
        
        # 并发上传多个文件
        upload_tasks = []
        for file_type, (file_path, content) in sample_text_files.items():
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            async def upload_file(file_content, filename):
                return await async_client.post(
                    "/api/v1/upload",
                    files={"file": (filename, file_content, "text/plain")}
                )
            
            task = upload_file(file_content, file_path.name)
            upload_tasks.append(task)
        
        upload_responses = await asyncio.gather(*upload_tasks)
        
        # 验证所有上传成功
        for response in upload_responses:
            assert response.status_code == status.HTTP_200_OK
            session_ids.append(response.json()["session_id"])
        
        # 并发执行批量替换
        batch_tasks = []
        for session_id in session_ids:
            with open(replacement_rules_file, 'rb') as f:
                rules_content = f.read()
            
            async def batch_replace(session_id, rules_content):
                return await async_client.post(
                    f"/api/v1/batch-replace/{session_id}",
                    files={"rules_file": ("rules.txt", rules_content, "text/plain")}
                )
            
            task = batch_replace(session_id, rules_content)
            batch_tasks.append(task)
        
        batch_responses = await asyncio.gather(*batch_tasks)
        
        # 验证所有批量替换启动成功
        task_ids = []
        for response in batch_responses:
            assert response.status_code == status.HTTP_200_OK
            task_ids.append(response.json()["task_id"])
        
        # 等待所有任务完成
        await asyncio.sleep(5)
        
        # 并发验证所有文件的处理结果
        read_tasks = []
        for session_id in session_ids:
            task = async_client.get(f"/api/v1/files/{session_id}/content")
            read_tasks.append(task)
        
        read_responses = await asyncio.gather(*read_tasks)
        
        # 验证所有文件都被正确处理
        for response in read_responses:
            assert response.status_code == status.HTTP_200_OK
            content = response.json()["content"]
            # 验证至少有一些替换发生
            assert "内容" in content or "检验" in content or "Hello" in content
        
        # 并发导出所有文件
        export_tasks = []
        for session_id in session_ids:
            task = async_client.get(f"/api/v1/export/{session_id}")
            export_tasks.append(task)
        
        export_responses = await asyncio.gather(*export_tasks)
        
        # 验证所有导出成功
        for response in export_responses:
            assert response.status_code == status.HTTP_200_OK
            assert "content-disposition" in response.headers
        
        # 清理：删除所有会话
        delete_tasks = []
        for session_id in session_ids:
            task = async_client.delete(f"/api/v1/sessions/{session_id}")
            delete_tasks.append(task)
        
        delete_responses = await asyncio.gather(*delete_tasks)
        
        # 验证所有删除成功
        for response in delete_responses:
            assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.asyncio
    async def test_large_file_processing(self, async_client: AsyncClient, temp_dir: Path, replacement_rules_file):
        """测试大文件处理"""
        # 创建大文件（约1MB）
        large_file = temp_dir / "large.txt"
        base_content = "这是一行重复的内容，用于测试大文件处理功能。包含文本和测试关键词。\n"
        large_content = base_content * 20000  # 约1MB
        large_file.write_text(large_content, encoding='utf-8')
        
        # 上传大文件
        with open(large_file, 'rb') as f:
            upload_response = await async_client.post(
                "/api/v1/upload",
                files={"file": ("large.txt", f, "text/plain")}
            )
        
        assert upload_response.status_code == status.HTTP_200_OK
        session_id = upload_response.json()["session_id"]
        
        # 验证大文件内容正确读取
        read_response = await async_client.get(f"/api/v1/files/{session_id}/content")
        assert read_response.status_code == status.HTTP_200_OK
        content = read_response.json()["content"]
        assert len(content) == len(large_content)
        
        # 在大文件中搜索
        search_response = await async_client.post(
            f"/api/v1/search-replace/{session_id}/search",
            json={
                "query": "测试",
                "case_sensitive": False,
                "use_regex": False,
                "whole_word": False
            }
        )
        assert search_response.status_code == status.HTTP_200_OK
        search_results = search_response.json()["results"]
        assert len(search_results) > 10000  # 应该找到很多匹配
        
        # 执行大文件批量替换
        with open(replacement_rules_file, 'rb') as f:
            batch_response = await async_client.post(
                f"/api/v1/batch-replace/{session_id}",
                files={"rules_file": ("rules.txt", f, "text/plain")}
            )
        
        assert batch_response.status_code == status.HTTP_200_OK
        
        # 等待大文件处理完成（可能需要更长时间）
        await asyncio.sleep(10)
        
        # 验证大文件替换结果
        read_response2 = await async_client.get(f"/api/v1/files/{session_id}/content")
        modified_content = read_response2.json()["content"]
        assert "检验" in modified_content  # "测试" -> "检验"
        assert "内容" in modified_content  # "文本" -> "内容"
        
        # 导出大文件
        export_response = await async_client.get(f"/api/v1/export/{session_id}")
        assert export_response.status_code == status.HTTP_200_OK
        exported_content = export_response.content.decode('utf-8')
        assert len(exported_content) > 500000  # 确保导出的是完整文件
    
    @pytest.mark.asyncio
    async def test_regex_search_replace_integration(self, async_client: AsyncClient, temp_dir: Path):
        """测试正则表达式搜索替换集成"""
        # 创建包含各种模式的测试文件
        regex_file = temp_dir / "regex_test.txt"
        regex_content = """正则表达式测试文件：

电话号码：
138-1234-5678
139-8765-4321
186-9999-0000

邮箱地址：
user@example.com
test.email@domain.org
admin@company.co.uk

日期格式：
2024-01-15
2023-12-31
2022-06-30

时间格式：
14:30:25
09:15:00
23:59:59

IP地址：
192.168.1.1
10.0.0.1
172.16.0.100

数字序列：
ID001, ID002, ID003
NUM123, NUM456, NUM789

结束。"""
        regex_file.write_text(regex_content, encoding='utf-8')
        
        # 上传文件
        with open(regex_file, 'rb') as f:
            upload_response = await async_client.post(
                "/api/v1/upload",
                files={"file": ("regex_test.txt", f, "text/plain")}
            )
        
        session_id = upload_response.json()["session_id"]
        
        # 测试正则表达式搜索
        regex_tests = [
            (r"\d{3}-\d{4}-\d{4}", "电话号码模式"),
            (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "邮箱模式"),
            (r"\d{4}-\d{2}-\d{2}", "日期模式"),
            (r"\d{2}:\d{2}:\d{2}", "时间模式"),
            (r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", "IP地址模式"),
            (r"ID\d{3}", "ID序列模式")
        ]
        
        for pattern, description in regex_tests:
            search_response = await async_client.post(
                f"/api/v1/search-replace/{session_id}/search",
                json={
                    "query": pattern,
                    "case_sensitive": False,
                    "use_regex": True,
                    "whole_word": False
                }
            )
            
            assert search_response.status_code == status.HTTP_200_OK
            results = search_response.json()["results"]
            assert len(results) > 0, f"{description} 应该找到匹配项"
        
        # 测试正则表达式替换
        replace_response = await async_client.post(
            f"/api/v1/search-replace/{session_id}/replace",
            json={
                "query": r"(\d{3})-(\d{4})-(\d{4})",
                "replacement": r"(\1) \2-\3",
                "case_sensitive": False,
                "use_regex": True,
                "whole_word": False
            }
        )
        
        assert replace_response.status_code == status.HTTP_200_OK
        assert replace_response.json()["replacements_made"] > 0
        
        # 验证正则替换结果
        read_response = await async_client.get(f"/api/v1/files/{session_id}/content")
        modified_content = read_response.json()["content"]
        assert "(138) 1234-5678" in modified_content
        assert "(139) 8765-4321" in modified_content
        assert "138-1234-5678" not in modified_content
    
    @pytest.mark.asyncio
    async def test_error_recovery_and_rollback(self, async_client: AsyncClient, temp_dir: Path):
        """测试错误恢复和回滚机制"""
        # 创建测试文件
        test_file = temp_dir / "error_test.txt"
        original_content = "错误恢复测试文件\n包含原始内容\n用于测试错误处理"
        test_file.write_text(original_content, encoding='utf-8')
        
        # 上传文件
        with open(test_file, 'rb') as f:
            upload_response = await async_client.post(
                "/api/v1/upload",
                files={"file": ("error_test.txt", f, "text/plain")}
            )
        
        session_id = upload_response.json()["session_id"]
        
        # 验证原始内容
        read_response = await async_client.get(f"/api/v1/files/{session_id}/content")
        assert read_response.json()["content"] == original_content
        
        # 尝试无效的正则表达式搜索
        invalid_search_response = await async_client.post(
            f"/api/v1/search-replace/{session_id}/search",
            json={
                "query": "[invalid regex",  # 无效的正则表达式
                "case_sensitive": False,
                "use_regex": True,
                "whole_word": False
            }
        )
        
        # 应该返回错误但不影响文件内容
        assert invalid_search_response.status_code == status.HTTP_400_BAD_REQUEST
        
        # 验证文件内容未被破坏
        read_response2 = await async_client.get(f"/api/v1/files/{session_id}/content")
        assert read_response2.json()["content"] == original_content
        
        # 尝试无效的正则表达式替换
        invalid_replace_response = await async_client.post(
            f"/api/v1/search-replace/{session_id}/replace",
            json={
                "query": "[another invalid regex",
                "replacement": "replacement",
                "case_sensitive": False,
                "use_regex": True,
                "whole_word": False
            }
        )
        
        # 应该返回错误
        assert invalid_replace_response.status_code == status.HTTP_400_BAD_REQUEST
        
        # 验证文件内容仍然完整
        read_response3 = await async_client.get(f"/api/v1/files/{session_id}/content")
        assert read_response3.json()["content"] == original_content
        
        # 创建无效的批量替换规则文件
        invalid_rules_file = temp_dir / "invalid_rules.txt"
        invalid_rules_content = """# 包含无效正则表达式的规则
[invalid->valid
(unclosed->group
*invalid->pattern"""
        invalid_rules_file.write_text(invalid_rules_content, encoding='utf-8')
        
        # 尝试使用无效规则进行批量替换
        with open(invalid_rules_file, 'rb') as f:
            invalid_batch_response = await async_client.post(
                f"/api/v1/batch-replace/{session_id}",
                files={"rules_file": ("invalid_rules.txt", f, "text/plain")}
            )
        
        # 批量替换可能启动但应该失败
        if invalid_batch_response.status_code == status.HTTP_200_OK:
            # 等待处理完成
            await asyncio.sleep(3)
            
            # 验证文件内容未被破坏
            read_response4 = await async_client.get(f"/api/v1/files/{session_id}/content")
            final_content = read_response4.json()["content"]
            # 文件应该保持原样或只有部分有效规则被应用
            assert "错误恢复测试文件" in final_content
        
        # 最终验证会话仍然可用
        session_response = await async_client.get(f"/api/v1/sessions/{session_id}")
        assert session_response.status_code == status.HTTP_200_OK
    
    @pytest.mark.asyncio
    async def test_performance_monitoring(self, async_client: AsyncClient, temp_dir: Path):
        """测试性能监控"""
        # 创建中等大小的文件用于性能测试
        perf_file = temp_dir / "performance.txt"
        base_line = "性能测试行，包含测试关键词和文本内容，用于替换操作。\n"
        perf_content = base_line * 10000  # 约500KB
        perf_file.write_text(perf_content, encoding='utf-8')
        
        # 记录开始时间
        start_time = datetime.now()
        
        # 上传文件
        with open(perf_file, 'rb') as f:
            upload_response = await async_client.post(
                "/api/v1/upload",
                files={"file": ("performance.txt", f, "text/plain")}
            )
        
        upload_time = datetime.now()
        assert upload_response.status_code == status.HTTP_200_OK
        session_id = upload_response.json()["session_id"]
        
        # 读取文件（性能测试）
        read_response = await async_client.get(f"/api/v1/files/{session_id}/content")
        read_time = datetime.now()
        assert read_response.status_code == status.HTTP_200_OK
        
        # 搜索操作（性能测试）
        search_response = await async_client.post(
            f"/api/v1/search-replace/{session_id}/search",
            json={
                "query": "测试",
                "case_sensitive": False,
                "use_regex": False,
                "whole_word": False
            }
        )
        search_time = datetime.now()
        assert search_response.status_code == status.HTTP_200_OK
        
        # 替换操作（性能测试）
        replace_response = await async_client.post(
            f"/api/v1/search-replace/{session_id}/replace",
            json={
                "query": "测试",
                "replacement": "检验",
                "case_sensitive": False,
                "use_regex": False,
                "whole_word": False
            }
        )
        replace_time = datetime.now()
        assert replace_response.status_code == status.HTTP_200_OK
        
        # 导出操作（性能测试）
        export_response = await async_client.get(f"/api/v1/export/{session_id}")
        export_time = datetime.now()
        assert export_response.status_code == status.HTTP_200_OK
        
        # 计算各操作耗时
        upload_duration = (upload_time - start_time).total_seconds()
        read_duration = (read_time - upload_time).total_seconds()
        search_duration = (search_time - read_time).total_seconds()
        replace_duration = (replace_time - search_time).total_seconds()
        export_duration = (export_time - replace_time).total_seconds()
        total_duration = (export_time - start_time).total_seconds()
        
        # 性能断言（这些阈值可能需要根据实际环境调整）
        assert upload_duration < 10.0, f"上传耗时过长: {upload_duration}秒"
        assert read_duration < 5.0, f"读取耗时过长: {read_duration}秒"
        assert search_duration < 5.0, f"搜索耗时过长: {search_duration}秒"
        assert replace_duration < 10.0, f"替换耗时过长: {replace_duration}秒"
        assert export_duration < 5.0, f"导出耗时过长: {export_duration}秒"
        assert total_duration < 30.0, f"总耗时过长: {total_duration}秒"
        
        # 记录性能数据（用于监控）
        print(f"\n性能测试结果:")
        print(f"上传: {upload_duration:.2f}秒")
        print(f"读取: {read_duration:.2f}秒")
        print(f"搜索: {search_duration:.2f}秒")
        print(f"替换: {replace_duration:.2f}秒")
        print(f"导出: {export_duration:.2f}秒")
        print(f"总计: {total_duration:.2f}秒")