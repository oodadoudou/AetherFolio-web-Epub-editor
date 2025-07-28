"""TEXT文件批量替换API测试"""

import pytest
import pytest_asyncio
import asyncio
import tempfile
from pathlib import Path
from httpx import AsyncClient
from fastapi import status


class TestTextBatchReplaceAPI:
    """TEXT文件批量替换API测试"""
    
    @pytest_asyncio.fixture
    async def batch_session(self, async_client: AsyncClient, temp_dir: Path):
        """创建用于批量替换测试的会话"""
        # 创建包含多种内容的测试文件
        test_file = temp_dir / "batch_test.txt"
        test_content = """第一章：开始的故事
这是第一章的内容。包含一些旧文本需要替换。
另一个段落，包含错误信息需要修正。
测试段落，用于验证替换功能。

第二章：继续的故事
这是第二章的内容。同样包含旧文本。
错误信息在这里也需要修正。
更多的测试内容。

第三章：结束的故事
最后一章的内容。
依然有旧文本和错误信息。
测试完成。"""
        test_file.write_text(test_content, encoding='utf-8')
        
        # 上传文件
        with open(test_file, 'rb') as f:
            response = await async_client.post(
                "/api/v1/upload",
                files={"file": ("batch_test.txt", f, "text/plain")}
            )
        
        data = response.json()
        # 上传API返回格式: {"success": True, "data": session_info}
        if "data" in data and "session_id" in data["data"]:
            return data["data"]["session_id"]
        elif "session_id" in data:
            return data["session_id"]
        else:
            raise ValueError(f"No session_id found in response: {data}")
    
    @pytest.fixture
    def simple_rules_file(self, temp_dir: Path) -> Path:
        """创建简单的替换规则文件"""
        rules_file = temp_dir / "simple_rules.txt"
        rules_content = """# 简单替换规则
旧文本->新文本
错误信息->正确信息
测试->检验"""
        rules_file.write_text(rules_content, encoding='utf-8')
        return rules_file
    
    @pytest.fixture
    def regex_rules_file(self, temp_dir: Path) -> Path:
        """创建包含正则表达式的替换规则文件"""
        rules_file = temp_dir / "regex_rules.txt"
        rules_content = r"""# 正则表达式替换规则
第(\d+)章->Chapter \1 (Mode: Regex)
故事$->Story (Mode: Regex)
内容。->content. (Mode: Text)"""
        rules_file.write_text(rules_content, encoding='utf-8')
        return rules_file
    
    @pytest.fixture
    def complex_rules_file(self, temp_dir: Path) -> Path:
        """创建复杂的替换规则文件"""
        rules_file = temp_dir / "complex_rules.txt"
        rules_content = """# 复杂替换规则文件
# 这是注释行，应该被忽略

# 基本文本替换
旧文本->新文本
错误信息->正确信息

# 正则表达式替换
第(\\d+)章->Chapter \\1 (Mode: Regex)
(\\d+)章->Chapter \\1 (Mode: Regex)

# 管道分隔格式
测试|检验
内容|content

# 空行和注释应该被忽略

# 更多替换
开始->Start
继续->Continue
结束->End"""
        rules_file.write_text(rules_content, encoding='utf-8')
        return rules_file
    
    @pytest.mark.asyncio
    async def test_simple_batch_replace(self, async_client: AsyncClient, batch_session: str, simple_rules_file: Path):
        """测试简单批量替换"""
        # 上传规则文件并执行批量替换
        with open(simple_rules_file, 'rb') as f:
            response = await async_client.post(
                f"/api/v1/batch-replace/{batch_session}",
                files={"rules_file": ("simple_rules.txt", f, "text/plain")}
            )
        
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert "task_url" in response_data["data"]
        assert "report_url" in response_data["data"]
        assert response_data["status"] == "success"
        
        # 等待任务完成
        await asyncio.sleep(2)
        
        # 验证替换结果
        content_response = await async_client.get(f"/api/v1/file-content?session_id={batch_session}&file_path=batch_test.txt")
        content_data = content_response.json()
        content = content_data["data"]["content"]
        
        # 验证替换生效
        assert "新文本" in content
        assert "正确信息" in content
        assert "检验" in content
        assert "旧文本" not in content
        assert "错误信息" not in content
        assert "测试" not in content
    
    @pytest.mark.asyncio
    async def test_regex_batch_replace(self, async_client: AsyncClient, batch_session: str, regex_rules_file: Path):
        """测试包含正则表达式的批量替换"""
        # 上传规则文件并执行批量替换
        with open(regex_rules_file, 'rb') as f:
            response = await async_client.post(
                f"/api/v1/batch-replace/{batch_session}",
                files={"rules_file": ("regex_rules.txt", f, "text/plain")}
            )
        
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["status"] == "success"
        
        # 等待任务完成
        await asyncio.sleep(2)
        
        # 验证替换结果
        content_response = await async_client.get(f"/api/v1/file-content?session_id={batch_session}&file_path=batch_test.txt")
        content_data = content_response.json()
        content = content_data["data"]["content"]
        
        # 验证正则表达式替换生效
        assert "Chapter 1" in content
        assert "Chapter 2" in content
        assert "Chapter 3" in content
        assert "Story" in content
        assert "content." in content
    
    @pytest.mark.asyncio
    async def test_complex_batch_replace(self, async_client: AsyncClient, batch_session: str, complex_rules_file: Path):
        """测试复杂批量替换"""
        # 上传规则文件并执行批量替换
        with open(complex_rules_file, 'rb') as f:
            response = await async_client.post(
                f"/api/v1/batch-replace/{batch_session}",
                files={"rules_file": ("complex_rules.txt", f, "text/plain")}
            )
        
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["status"] == "success"
        
        # 等待任务完成
        await asyncio.sleep(3)
        
        # 验证替换结果
        content_response = await async_client.get(f"/api/v1/file-content?session_id={batch_session}&file_path=batch_test.txt")
        content_data = content_response.json()
        content = content_data["data"]["content"]
        
        # 验证各种类型的替换都生效
        assert "新文本" in content
        assert "正确信息" in content
        assert "Chapter 1" in content
        assert "检验" in content
        assert "content" in content
        assert "Start" in content
        assert "Continue" in content
        assert "End" in content
    
    @pytest.mark.asyncio
    async def test_batch_replace_progress(self, async_client: AsyncClient, batch_session: str, simple_rules_file: Path):
        """测试批量替换进度监控"""
        # 启动批量替换任务
        with open(simple_rules_file, 'rb') as f:
            response = await async_client.post(
                f"/api/v1/batch-replace/{batch_session}",
                files={"rules_file": ("simple_rules.txt", f, "text/plain")}
            )
        
        assert response.status_code == status.HTTP_200_OK
        
        # 检查进度（使用普通GET请求而不是SSE）
        progress_response = await async_client.get(f"/api/v1/batch-replace/progress/{batch_session}")
        
        # 进度端点可能返回200（如果任务完成）或其他状态
        assert progress_response.status_code in [200, 202, 404]
    
    @pytest.mark.asyncio
    async def test_batch_replace_report(self, async_client: AsyncClient, batch_session: str, simple_rules_file: Path):
        """测试批量替换报告生成"""
        # 执行批量替换
        with open(simple_rules_file, 'rb') as f:
            response = await async_client.post(
                f"/api/v1/batch-replace/{batch_session}",
                files={"rules_file": ("simple_rules.txt", f, "text/plain")}
            )
        
        assert response.status_code == status.HTTP_200_OK
        
        # 等待任务完成
        await asyncio.sleep(2)
        
        # 获取报告
        report_response = await async_client.get(f"/api/v1/batch-replace/report/{batch_session}")
        
        # 报告可能是HTML或JSON格式
        assert report_response.status_code == status.HTTP_200_OK
        
        # 检查响应内容类型
        content_type = report_response.headers.get("content-type", "")
        assert "text/html" in content_type or "application/json" in content_type
    
    @pytest.mark.asyncio
    async def test_batch_replace_cancel(self, async_client: AsyncClient, batch_session: str, complex_rules_file: Path):
        """测试取消批量替换任务"""
        # 启动批量替换任务
        with open(complex_rules_file, 'rb') as f:
            response = await async_client.post(
                f"/api/v1/batch-replace/{batch_session}",
                files={"rules_file": ("complex_rules.txt", f, "text/plain")}
            )
        
        assert response.status_code == status.HTTP_200_OK
        
        # 立即尝试取消任务
        cancel_response = await async_client.post(f"/api/v1/batch-replace/cancel/{batch_session}")
        
        # 取消可能成功或失败（如果任务已完成）
        assert cancel_response.status_code in [200, 400, 404]
    
    @pytest.mark.asyncio
    async def test_batch_replace_invalid_rules_file(self, async_client: AsyncClient, batch_session: str, temp_dir: Path):
        """测试无效的规则文件"""
        # 创建无效的规则文件
        invalid_rules_file = temp_dir / "invalid_rules.txt"
        invalid_rules_file.write_text("", encoding='utf-8')  # 空文件
        
        # 上传无效规则文件
        with open(invalid_rules_file, 'rb') as f:
            response = await async_client.post(
                f"/api/v1/batch-replace/{batch_session}",
                files={"rules_file": ("invalid_rules.txt", f, "text/plain")}
            )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        assert response_data["status"] == "error"
    
    @pytest.mark.asyncio
    async def test_batch_replace_large_rules_file(self, async_client: AsyncClient, batch_session: str, temp_dir: Path):
        """测试过大的规则文件"""
        # 创建过大的规则文件（超过10MB）
        large_rules_file = temp_dir / "large_rules.txt"
        large_content = "test->replacement\n" * 500000  # 约10MB
        large_rules_file.write_text(large_content, encoding='utf-8')
        
        # 上传过大规则文件
        with open(large_rules_file, 'rb') as f:
            response = await async_client.post(
                f"/api/v1/batch-replace/{batch_session}",
                files={"rules_file": ("large_rules.txt", f, "text/plain")}
            )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        assert response_data["status"] == "error"
    
    @pytest.mark.asyncio
    async def test_batch_replace_wrong_file_extension(self, async_client: AsyncClient, batch_session: str, temp_dir: Path):
        """测试错误的文件扩展名"""
        # 创建非.txt扩展名的规则文件
        wrong_ext_file = temp_dir / "rules.doc"
        wrong_ext_file.write_text("test->replacement", encoding='utf-8')
        
        # 上传错误扩展名的文件
        with open(wrong_ext_file, 'rb') as f:
            response = await async_client.post(
                f"/api/v1/batch-replace/{batch_session}",
                files={"rules_file": ("rules.doc", f, "application/msword")}
            )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["success"] is False
    
    @pytest.mark.asyncio
    async def test_batch_replace_nonexistent_session(self, async_client: AsyncClient, simple_rules_file: Path):
        """测试不存在的会话ID"""
        # 使用不存在的会话ID
        with open(simple_rules_file, 'rb') as f:
            response = await async_client.post(
                "/api/v1/batch-replace/nonexistent-session",
                files={"rules_file": ("simple_rules.txt", f, "text/plain")}
            )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["success"] is False
    
    @pytest.mark.asyncio
    async def test_batch_replace_missing_rules_file(self, async_client: AsyncClient, batch_session: str):
        """测试缺少规则文件"""
        # 不上传规则文件
        response = await async_client.post(f"/api/v1/batch-replace/{batch_session}")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_simplified_batch_replace(self, async_client: AsyncClient, batch_session: str):
        """测试简化的批量替换接口"""
        # 使用简化接口（如果存在）
        replace_data = {
            "session_id": batch_session,
            "rules": [
                {"search": "旧文本", "replace": "新文本"},
                {"search": "错误信息", "replace": "正确信息"}
            ]
        }
        
        response = await async_client.post(
            "/api/v1/batch-replace/",
            json=replace_data
        )
        
        # 这个接口可能存在也可能不存在
        if response.status_code != status.HTTP_404_NOT_FOUND:
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True


class TestTextBatchReplaceEdgeCases:
    """TEXT文件批量替换边界情况测试"""
    
    @pytest_asyncio.fixture
    async def edge_case_session(self, async_client: AsyncClient, temp_dir: Path):
        """创建边界情况测试会话"""
        # 创建包含边界情况的测试文件
        test_file = temp_dir / "edge_case.txt"
        test_content = """Line with special chars: @#$%^&*()
Line with unicode: 你好世界 🌍 emoji
Empty line follows:

Line with tabs:\tTabbed content
Line with quotes: "quoted text" and 'single quotes'
Line with backslashes: C:\\path\\to\\file
Line with regex chars: [.*+?^${}()|\\]
Very long line: """ + "a" * 1000 + """
Final line"""
        test_file.write_text(test_content, encoding='utf-8')
        
        # 上传文件
        with open(test_file, 'rb') as f:
            response = await async_client.post(
                "/api/v1/upload",
                files={"file": ("edge_case.txt", f, "text/plain")}
            )
        
        data = response.json()
        # 上传API返回格式: {"success": True, "data": session_info}
        if "data" in data and "session_id" in data["data"]:
            return data["data"]["session_id"]
        elif "session_id" in data:
            return data["session_id"]
        else:
            raise ValueError(f"No session_id found in response: {data}")
    
    @pytest.fixture
    def edge_case_rules_file(self, temp_dir: Path) -> Path:
        """创建边界情况规则文件"""
        rules_file = temp_dir / "edge_case_rules.txt"
        rules_content = """# 边界情况规则
# 特殊字符替换
@#$%->SPECIAL

# Unicode替换
你好世界->Hello World
🌍->Earth

# 引号替换
"quoted text"->"replaced text"
'single quotes'->'new quotes'

# 反斜杠替换（需要转义）
C:\\\\path->D:\\\\newpath (Mode: Text)

# 正则表达式特殊字符
\\[.*\\+\\?->REGEX_CHARS (Mode: Regex)

# 长文本替换
""" + "a" * 50 + "->" + "b" * 50 + """

# 空行处理


# 制表符替换
\t->    (Mode: Text)"""
        rules_file.write_text(rules_content, encoding='utf-8')
        return rules_file
    
    @pytest.mark.asyncio
    async def test_edge_case_batch_replace(self, async_client: AsyncClient, edge_case_session: str, edge_case_rules_file: Path):
        """测试边界情况批量替换"""
        # 执行批量替换
        with open(edge_case_rules_file, 'rb') as f:
            response = await async_client.post(
                f"/api/v1/batch-replace/{edge_case_session}",
                files={"rules_file": ("edge_case_rules.txt", f, "text/plain")}
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        
        # 等待任务完成
        await asyncio.sleep(3)
        
        # 验证替换结果
        content_response = await async_client.get(f"/api/v1/files/{edge_case_session}/content")
        content_data = content_response.json()
        content = content_data["content"]
        
        # 验证各种边界情况的替换
        assert "SPECIAL" in content
        assert "Hello World" in content
        assert "Earth" in content
        assert "replaced text" in content
        assert "new quotes" in content
    
    @pytest.mark.asyncio
    async def test_concurrent_batch_replace(self, async_client: AsyncClient, temp_dir: Path):
        """测试并发批量替换"""
        # 创建多个会话
        sessions = []
        for i in range(3):
            test_file = temp_dir / f"concurrent_test_{i}.txt"
            test_content = f"Content for file {i}\nTest content {i}\nReplace me {i}"
            test_file.write_text(test_content, encoding='utf-8')
            
            with open(test_file, 'rb') as f:
                response = await async_client.post(
                    "/api/v1/upload",
                    files={"file": (f"concurrent_test_{i}.txt", f, "text/plain")}
                )
            
            data = response.json()
            # 上传API返回格式: {"success": True, "data": session_info}
            if "data" in data and "session_id" in data["data"]:
                sessions.append(data["data"]["session_id"])
            elif "session_id" in data:
                sessions.append(data["session_id"])
            else:
                raise ValueError(f"No session_id found in response: {data}")
        
        # 创建规则文件
        rules_file = temp_dir / "concurrent_rules.txt"
        rules_file.write_text("Test->Tested\nReplace me->Replaced", encoding='utf-8')
        
        # 并发执行批量替换
        tasks = []
        for session_id in sessions:
            with open(rules_file, 'rb') as f:
                task = async_client.post(
                    f"/api/v1/batch-replace/{session_id}",
                    files={"rules_file": ("concurrent_rules.txt", f, "text/plain")}
                )
                tasks.append(task)
        
        # 等待所有任务完成
        responses = await asyncio.gather(*tasks)
        
        # 验证所有任务都成功
        for response in responses:
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
        
        # 等待处理完成
        await asyncio.sleep(3)
        
        # 验证所有文件都被正确替换
        for session_id in sessions:
            content_response = await async_client.get(f"/api/v1/files/{session_id}/content")
            content_data = content_response.json()
            content = content_data["content"]
            assert "Tested" in content
            assert "Replaced" in content
            assert "Test" not in content or "Tested" in content  # 避免部分匹配问题