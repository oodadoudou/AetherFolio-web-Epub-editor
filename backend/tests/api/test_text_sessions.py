"""TEXT文件会话管理API测试"""

import pytest
from pathlib import Path
from httpx import AsyncClient
from fastapi import status
import asyncio


class TestTextSessionsAPI:
    """TEXT文件会话管理API测试"""
    
    @pytest.fixture
    async def text_session(self, async_client: AsyncClient, temp_dir: Path):
        """创建TEXT文件会话"""
        test_file = temp_dir / "session_test.txt"
        test_content = "这是一个用于会话测试的文本文件。\n包含多行内容。"
        test_file.write_text(test_content, encoding='utf-8')
        
        with open(test_file, 'rb') as f:
            response = await async_client.post(
                "/api/v1/upload",
                files={"file": ("session_test.txt", f, "text/plain")}
            )
        
        data = response.json()
        return data["session_id"], test_content
    
    @pytest.fixture
    async def multiple_text_sessions(self, async_client: AsyncClient, temp_dir: Path):
        """创建多个TEXT文件会话"""
        sessions = []
        
        for i in range(3):
            test_file = temp_dir / f"session_test_{i}.txt"
            test_content = f"这是第{i+1}个测试文件的内容。\n用于多会话测试。"
            test_file.write_text(test_content, encoding='utf-8')
            
            with open(test_file, 'rb') as f:
                response = await async_client.post(
                    "/api/v1/upload",
                    files={"file": (f"session_test_{i}.txt", f, "text/plain")}
                )
            
            data = response.json()
            sessions.append((data["session_id"], test_content))
        
        return sessions
    
    @pytest.mark.asyncio
    async def test_get_all_sessions(self, async_client: AsyncClient, multiple_text_sessions):
        """测试获取所有会话列表"""
        sessions = multiple_text_sessions
        session_ids = [session[0] for session in sessions]
        
        # 获取所有会话
        response = await async_client.get("/api/v1/sessions")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "sessions" in data
        
        # 验证返回的会话包含我们创建的会话
        returned_session_ids = [session["session_id"] for session in data["sessions"]]
        for session_id in session_ids:
            assert session_id in returned_session_ids
        
        # 验证会话信息完整性
        for session in data["sessions"]:
            if session["session_id"] in session_ids:
                assert "file_type" in session
                assert session["file_type"] == "TEXT"
                assert "original_filename" in session
                assert "created_at" in session
                assert "file_size" in session
                assert session["original_filename"].endswith(".txt")
    
    @pytest.mark.asyncio
    async def test_get_session_info(self, async_client: AsyncClient, text_session):
        """测试获取单个会话信息"""
        session_id, _ = text_session
        
        # 获取会话信息
        response = await async_client.get(f"/api/v1/sessions/{session_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "session" in data
        
        session_info = data["session"]
        assert session_info["session_id"] == session_id
        assert session_info["file_type"] == "TEXT"
        assert session_info["original_filename"] == "session_test.txt"
        assert "created_at" in session_info
        assert "file_size" in session_info
        assert session_info["file_size"] > 0
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_session_info(self, async_client: AsyncClient):
        """测试获取不存在的会话信息"""
        response = await async_client.get("/api/v1/sessions/nonexistent-session")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["success"] is False
        assert "error" in data or "detail" in data
    
    @pytest.mark.asyncio
    async def test_delete_session(self, async_client: AsyncClient, text_session):
        """测试删除会话"""
        session_id, _ = text_session
        
        # 确认会话存在
        response = await async_client.get(f"/api/v1/sessions/{session_id}")
        assert response.status_code == status.HTTP_200_OK
        
        # 删除会话
        delete_response = await async_client.delete(f"/api/v1/sessions/{session_id}")
        
        assert delete_response.status_code == status.HTTP_200_OK
        data = delete_response.json()
        assert data["success"] is True
        
        # 确认会话已被删除
        get_response = await async_client.get(f"/api/v1/sessions/{session_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(self, async_client: AsyncClient):
        """测试删除不存在的会话"""
        response = await async_client.delete("/api/v1/sessions/nonexistent-session")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["success"] is False
    
    @pytest.mark.asyncio
    async def test_session_file_operations_after_creation(self, async_client: AsyncClient, text_session):
        """测试会话创建后的文件操作"""
        session_id, original_content = text_session
        
        # 读取文件内容
        read_response = await async_client.get(f"/api/v1/files/{session_id}/content")
        assert read_response.status_code == status.HTTP_200_OK
        read_data = read_response.json()
        assert read_data["content"] == original_content
        
        # 修改文件内容
        new_content = "修改后的文件内容\n新增的一行"
        update_response = await async_client.put(
            f"/api/v1/files/{session_id}/content",
            json={"content": new_content}
        )
        assert update_response.status_code == status.HTTP_200_OK
        
        # 再次读取验证修改
        read_response2 = await async_client.get(f"/api/v1/files/{session_id}/content")
        assert read_response2.status_code == status.HTTP_200_OK
        read_data2 = read_response2.json()
        assert read_data2["content"] == new_content
    
    @pytest.mark.asyncio
    async def test_session_search_operations(self, async_client: AsyncClient, text_session):
        """测试会话的搜索操作"""
        session_id, _ = text_session
        
        # 执行搜索
        search_request = {
            "query": "测试",
            "case_sensitive": False,
            "use_regex": False,
            "whole_word": False
        }
        
        search_response = await async_client.post(
            f"/api/v1/search-replace/{session_id}/search",
            json=search_request
        )
        
        assert search_response.status_code == status.HTTP_200_OK
        search_data = search_response.json()
        assert search_data["success"] is True
        assert "results" in search_data
        assert len(search_data["results"]) > 0
        
        # 验证搜索结果
        result = search_data["results"][0]
        assert "file_path" in result
        assert "line_number" in result
        assert "match_text" in result
        assert "测试" in result["match_text"]
    
    @pytest.mark.asyncio
    async def test_session_replace_operations(self, async_client: AsyncClient, text_session):
        """测试会话的替换操作"""
        session_id, _ = text_session
        
        # 执行替换
        replace_request = {
            "query": "测试",
            "replacement": "检验",
            "case_sensitive": False,
            "use_regex": False,
            "whole_word": False
        }
        
        replace_response = await async_client.post(
            f"/api/v1/search-replace/{session_id}/replace",
            json=replace_request
        )
        
        assert replace_response.status_code == status.HTTP_200_OK
        replace_data = replace_response.json()
        assert replace_data["success"] is True
        assert "replacements_made" in replace_data
        assert replace_data["replacements_made"] > 0
        
        # 验证替换结果
        read_response = await async_client.get(f"/api/v1/files/{session_id}/content")
        read_data = read_response.json()
        assert "检验" in read_data["content"]
        assert "测试" not in read_data["content"]
    
    @pytest.mark.asyncio
    async def test_session_batch_replace_operations(self, async_client: AsyncClient, text_session, temp_dir: Path):
        """测试会话的批量替换操作"""
        session_id, _ = text_session
        
        # 创建替换规则文件
        rules_file = temp_dir / "session_rules.txt"
        rules_content = "测试->检验\n文本->内容"
        rules_file.write_text(rules_content, encoding='utf-8')
        
        # 执行批量替换
        with open(rules_file, 'rb') as f:
            batch_response = await async_client.post(
                f"/api/v1/batch-replace/{session_id}",
                files={"rules_file": ("session_rules.txt", f, "text/plain")}
            )
        
        assert batch_response.status_code == status.HTTP_200_OK
        batch_data = batch_response.json()
        assert batch_data["success"] is True
        assert "task_id" in batch_data
        
        # 等待批量替换完成
        await asyncio.sleep(2)
        
        # 验证替换结果
        read_response = await async_client.get(f"/api/v1/files/{session_id}/content")
        read_data = read_response.json()
        content = read_data["content"]
        assert "检验" in content
        assert "内容" in content
        assert "测试" not in content
        assert "文本" not in content
    
    @pytest.mark.asyncio
    async def test_session_export_operations(self, async_client: AsyncClient, text_session):
        """测试会话的导出操作"""
        session_id, original_content = text_session
        
        # 导出文件
        export_response = await async_client.get(f"/api/v1/export/{session_id}")
        
        assert export_response.status_code == status.HTTP_200_OK
        
        # 验证导出内容
        exported_content = export_response.content.decode('utf-8')
        assert exported_content == original_content
        
        # 验证响应头
        assert "content-disposition" in export_response.headers
        assert "session_test.txt" in export_response.headers["content-disposition"]
    
    @pytest.mark.asyncio
    async def test_concurrent_session_operations(self, async_client: AsyncClient, multiple_text_sessions):
        """测试并发会话操作"""
        sessions = multiple_text_sessions
        
        # 并发读取所有会话的内容
        read_tasks = []
        for session_id, _ in sessions:
            task = async_client.get(f"/api/v1/files/{session_id}/content")
            read_tasks.append(task)
        
        read_responses = await asyncio.gather(*read_tasks)
        
        # 验证所有读取操作都成功
        for i, response in enumerate(read_responses):
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            expected_content = sessions[i][1]
            assert data["content"] == expected_content
        
        # 并发搜索操作
        search_tasks = []
        search_request = {
            "query": "测试",
            "case_sensitive": False,
            "use_regex": False,
            "whole_word": False
        }
        
        for session_id, _ in sessions:
            task = async_client.post(
                f"/api/v1/search-replace/{session_id}/search",
                json=search_request
            )
            search_tasks.append(task)
        
        search_responses = await asyncio.gather(*search_tasks)
        
        # 验证所有搜索操作都成功
        for response in search_responses:
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert len(data["results"]) > 0
    
    @pytest.mark.asyncio
    async def test_session_lifecycle(self, async_client: AsyncClient, temp_dir: Path):
        """测试完整的会话生命周期"""
        # 1. 创建会话（上传文件）
        test_file = temp_dir / "lifecycle_test.txt"
        original_content = "生命周期测试文件\n包含原始内容"
        test_file.write_text(original_content, encoding='utf-8')
        
        with open(test_file, 'rb') as f:
            upload_response = await async_client.post(
                "/api/v1/upload",
                files={"file": ("lifecycle_test.txt", f, "text/plain")}
            )
        
        assert upload_response.status_code == status.HTTP_200_OK
        session_id = upload_response.json()["session_id"]
        
        # 2. 获取会话信息
        info_response = await async_client.get(f"/api/v1/sessions/{session_id}")
        assert info_response.status_code == status.HTTP_200_OK
        
        # 3. 读取文件内容
        read_response = await async_client.get(f"/api/v1/files/{session_id}/content")
        assert read_response.status_code == status.HTTP_200_OK
        assert read_response.json()["content"] == original_content
        
        # 4. 搜索内容
        search_response = await async_client.post(
            f"/api/v1/search-replace/{session_id}/search",
            json={"query": "测试", "case_sensitive": False, "use_regex": False, "whole_word": False}
        )
        assert search_response.status_code == status.HTTP_200_OK
        assert len(search_response.json()["results"]) > 0
        
        # 5. 执行替换
        replace_response = await async_client.post(
            f"/api/v1/search-replace/{session_id}/replace",
            json={"query": "测试", "replacement": "检验", "case_sensitive": False, "use_regex": False, "whole_word": False}
        )
        assert replace_response.status_code == status.HTTP_200_OK
        
        # 6. 验证替换结果
        read_response2 = await async_client.get(f"/api/v1/files/{session_id}/content")
        modified_content = read_response2.json()["content"]
        assert "检验" in modified_content
        assert "测试" not in modified_content
        
        # 7. 导出文件
        export_response = await async_client.get(f"/api/v1/export/{session_id}")
        assert export_response.status_code == status.HTTP_200_OK
        exported_content = export_response.content.decode('utf-8')
        assert exported_content == modified_content
        
        # 8. 删除会话
        delete_response = await async_client.delete(f"/api/v1/sessions/{session_id}")
        assert delete_response.status_code == status.HTTP_200_OK
        
        # 9. 验证会话已删除
        final_info_response = await async_client.get(f"/api/v1/sessions/{session_id}")
        assert final_info_response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_session_data_persistence(self, async_client: AsyncClient, text_session):
        """测试会话数据持久性"""
        session_id, original_content = text_session
        
        # 修改文件内容
        new_content = "持久性测试内容\n修改后的数据"
        update_response = await async_client.put(
            f"/api/v1/files/{session_id}/content",
            json={"content": new_content}
        )
        assert update_response.status_code == status.HTTP_200_OK
        
        # 多次读取验证数据一致性
        for _ in range(5):
            read_response = await async_client.get(f"/api/v1/files/{session_id}/content")
            assert read_response.status_code == status.HTTP_200_OK
            assert read_response.json()["content"] == new_content
            
            # 短暂等待
            await asyncio.sleep(0.1)
        
        # 验证会话信息保持一致
        info_response = await async_client.get(f"/api/v1/sessions/{session_id}")
        assert info_response.status_code == status.HTTP_200_OK
        session_info = info_response.json()["session"]
        assert session_info["session_id"] == session_id
        assert session_info["file_type"] == "TEXT"
    
    @pytest.mark.asyncio
    async def test_session_error_handling(self, async_client: AsyncClient):
        """测试会话错误处理"""
        # 测试无效的会话ID格式
        invalid_session_ids = [
            "",
            "invalid-session",
            "../../../etc/passwd",
            "session with spaces",
            "session/with/slashes",
            "session\\with\\backslashes"
        ]
        
        for invalid_id in invalid_session_ids:
            # 测试获取会话信息
            info_response = await async_client.get(f"/api/v1/sessions/{invalid_id}")
            assert info_response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_422_UNPROCESSABLE_ENTITY]
            
            # 测试读取文件内容
            read_response = await async_client.get(f"/api/v1/files/{invalid_id}/content")
            assert read_response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_422_UNPROCESSABLE_ENTITY]
            
            # 测试删除会话
            delete_response = await async_client.delete(f"/api/v1/sessions/{invalid_id}")
            assert delete_response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_422_UNPROCESSABLE_ENTITY]