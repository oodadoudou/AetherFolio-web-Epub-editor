"""会话API测试"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from httpx import AsyncClient


class TestSessionsAPI:
    """会话API测试"""
    
    def test_health_check(self, client):
        """测试健康检查端点"""
        response = client.get("/api/v1/sessions/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
    
    def test_create_session_success(self, client):
        """测试成功创建会话"""
        response = client.post("/api/v1/sessions/")
        assert response.status_code == 201
        data = response.json()
        assert "session_id" in data
        assert "created_at" in data
        assert "status" in data
        assert data["status"] == "active"
    
    def test_get_session_success(self, client):
        """测试成功获取会话信息"""
        # 首先创建一个会话
        create_response = client.post("/api/v1/sessions/")
        session_id = create_response.json()["session_id"]
        
        # 获取会话信息
        response = client.get(f"/api/v1/sessions/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert "created_at" in data
        assert "status" in data
        assert "files_count" in data
    
    def test_get_session_not_found(self, client):
        """测试获取不存在的会话"""
        response = client.get("/api/v1/sessions/nonexistent_session_id")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_get_session_stats_success(self, client):
        """测试成功获取会话统计信息"""
        # 创建会话
        create_response = client.post("/api/v1/sessions/")
        session_id = create_response.json()["session_id"]
        
        # 获取统计信息
        response = client.get(f"/api/v1/sessions/{session_id}/stats")
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "files_count" in data
        assert "total_size" in data
        assert "operations_count" in data
        assert "created_at" in data
        assert "last_activity" in data
    
    def test_get_session_stats_not_found(self, client):
        """测试获取不存在会话的统计信息"""
        response = client.get("/api/v1/sessions/nonexistent_session/stats")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    def test_get_all_sessions_success(self, client):
        """测试成功获取所有会话列表"""
        # 创建几个会话
        session_ids = []
        for _ in range(3):
            response = client.post("/api/v1/sessions/")
            session_ids.append(response.json()["session_id"])
        
        # 获取所有会话
        response = client.get("/api/v1/sessions/")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "total_count" in data
        assert len(data["sessions"]) >= 3
        
        # 验证返回的会话包含必要字段
        for session in data["sessions"]:
            assert "session_id" in session
            assert "created_at" in session
            assert "status" in session
    
    def test_get_all_sessions_with_pagination(self, client):
        """测试带分页的会话列表获取"""
        response = client.get("/api/v1/sessions/?page=1&size=5")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "total_count" in data
        assert "page" in data
        assert "size" in data
        assert len(data["sessions"]) <= 5
    
    def test_delete_session_success(self, client):
        """测试成功删除会话"""
        # 创建会话
        create_response = client.post("/api/v1/sessions/")
        session_id = create_response.json()["session_id"]
        
        # 删除会话
        response = client.delete(f"/api/v1/sessions/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "deleted" in data["message"].lower()
        
        # 验证会话已被删除
        get_response = client.get(f"/api/v1/sessions/{session_id}")
        assert get_response.status_code == 404
    
    def test_delete_session_not_found(self, client):
        """测试删除不存在的会话"""
        response = client.delete("/api/v1/sessions/nonexistent_session")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    def test_cleanup_sessions_success(self, client):
        """测试成功清理会话"""
        response = client.post("/api/v1/sessions/cleanup")
        assert response.status_code == 200
        data = response.json()
        assert "cleaned_sessions" in data
        assert "freed_space" in data
        assert isinstance(data["cleaned_sessions"], int)
        assert isinstance(data["freed_space"], (int, float))
    
    def test_cleanup_sessions_with_age_filter(self, client):
        """测试带年龄过滤的会话清理"""
        response = client.post("/api/v1/sessions/cleanup?max_age_hours=24")
        assert response.status_code == 200
        data = response.json()
        assert "cleaned_sessions" in data
        assert "freed_space" in data
    
    def test_session_invalid_id_format(self, client):
        """测试无效的会话ID格式"""
        invalid_ids = [
            "invalid-id-format",
            "123",
            "session_with_special_chars!@#",
            "",
            "a" * 100  # 过长的ID
        ]
        
        for invalid_id in invalid_ids:
            response = client.get(f"/api/v1/sessions/{invalid_id}")
            assert response.status_code in [400, 404, 422]
    
    def test_session_concurrent_creation(self, client):
        """测试并发创建会话"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def create_session():
            response = client.post("/api/v1/sessions/")
            results.put((response.status_code, response.json()))
        
        # 创建多个线程并发创建会话
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=create_session)
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证所有会话都成功创建
        session_ids = set()
        while not results.empty():
            status_code, data = results.get()
            assert status_code == 201
            assert "session_id" in data
            session_ids.add(data["session_id"])
        
        # 验证所有会话ID都是唯一的
        assert len(session_ids) == 5
    
    def test_session_rate_limiting(self, client):
        """测试会话创建速率限制"""
        # 快速创建多个会话
        responses = []
        for _ in range(10):
            response = client.post("/api/v1/sessions/")
            responses.append(response)
            time.sleep(0.1)  # 短暂延迟
        
        # 大部分请求应该成功，但可能有一些被限制
        success_count = sum(1 for r in responses if r.status_code == 201)
        rate_limited_count = sum(1 for r in responses if r.status_code == 429)
        
        assert success_count >= 5  # 至少有一些成功
        # 注意：实际的速率限制行为取决于具体实现
    
    def test_session_expiration_handling(self, client):
        """测试会话过期处理"""
        # 创建会话
        create_response = client.post("/api/v1/sessions/")
        session_id = create_response.json()["session_id"]
        
        # 模拟会话过期（这里需要根据实际实现调整）
        with patch('backend.services.session_service.SessionService.is_session_expired', return_value=True):
            response = client.get(f"/api/v1/sessions/{session_id}")
            # 过期的会话可能返回404或特殊状态
            assert response.status_code in [404, 410]  # 410 Gone for expired resources


class TestSessionsAPIAsync:
    """会话API异步测试"""
    
    @pytest.mark.asyncio
    async def test_async_create_session(self, async_client):
        """测试异步创建会话"""
        response = await async_client.post("/api/v1/sessions/")
        assert response.status_code == 201
        data = response.json()
        assert "session_id" in data
        assert "created_at" in data
    
    @pytest.mark.asyncio
    async def test_async_get_session(self, async_client):
        """测试异步获取会话"""
        # 创建会话
        create_response = await async_client.post("/api/v1/sessions/")
        session_id = create_response.json()["session_id"]
        
        # 获取会话
        response = await async_client.get(f"/api/v1/sessions/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
    
    @pytest.mark.asyncio
    async def test_async_concurrent_operations(self, async_client):
        """测试异步并发操作"""
        # 并发创建多个会话
        create_tasks = [
            async_client.post("/api/v1/sessions/")
            for _ in range(5)
        ]
        
        create_responses = await asyncio.gather(*create_tasks)
        
        # 验证所有会话都成功创建
        session_ids = []
        for response in create_responses:
            assert response.status_code == 201
            session_ids.append(response.json()["session_id"])
        
        # 并发获取会话信息
        get_tasks = [
            async_client.get(f"/api/v1/sessions/{session_id}")
            for session_id in session_ids
        ]
        
        get_responses = await asyncio.gather(*get_tasks)
        
        # 验证所有获取操作都成功
        for response in get_responses:
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_async_session_cleanup(self, async_client):
        """测试异步会话清理"""
        # 创建一些会话
        for _ in range(3):
            await async_client.post("/api/v1/sessions/")
        
        # 执行清理
        response = await async_client.post("/api/v1/sessions/cleanup")
        assert response.status_code == 200
        data = response.json()
        assert "cleaned_sessions" in data
        assert "freed_space" in data


class TestSessionsRateLimit:
    """会话API速率限制测试"""
    
    def test_create_session_rate_limit(self, client):
        """测试创建会话的速率限制"""
        # 在短时间内发送大量请求
        responses = []
        start_time = time.time()
        
        for _ in range(20):
            response = client.post("/api/v1/sessions/")
            responses.append(response)
            if time.time() - start_time > 1:  # 1秒内
                break
        
        # 检查是否有速率限制响应
        status_codes = [r.status_code for r in responses]
        
        # 应该有一些成功的请求
        assert 201 in status_codes
        
        # 可能有一些被速率限制的请求
        rate_limited = [r for r in responses if r.status_code == 429]
        if rate_limited:
            # 验证速率限制响应包含适当的头部
            for response in rate_limited:
                assert "Retry-After" in response.headers or "X-RateLimit-Reset" in response.headers
    
    def test_get_sessions_rate_limit(self, client):
        """测试获取会话列表的速率限制"""
        responses = []
        
        for _ in range(15):
            response = client.get("/api/v1/sessions/")
            responses.append(response)
            time.sleep(0.05)  # 短暂延迟
        
        # 大部分请求应该成功
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count >= 10
    
    def test_cleanup_rate_limit(self, client):
        """测试清理操作的速率限制"""
        responses = []
        
        # 连续发送清理请求
        for _ in range(5):
            response = client.post("/api/v1/sessions/cleanup")
            responses.append(response)
            time.sleep(0.1)
        
        # 第一个请求应该成功
        assert responses[0].status_code == 200
        
        # 后续请求可能被限制（取决于实现）
        rate_limited_count = sum(1 for r in responses[1:] if r.status_code == 429)
        # 清理操作通常有更严格的速率限制


class TestSessionsErrorHandling:
    """会话API错误处理测试"""
    
    def test_malformed_request_body(self, client):
        """测试格式错误的请求体"""
        # 发送无效的JSON
        response = client.post(
            "/api/v1/sessions/",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_unsupported_media_type(self, client):
        """测试不支持的媒体类型"""
        response = client.post(
            "/api/v1/sessions/",
            data="some data",
            headers={"Content-Type": "text/plain"}
        )
        # 根据API设计，可能返回415或接受请求
        assert response.status_code in [200, 201, 415]
    
    def test_method_not_allowed(self, client):
        """测试不允许的HTTP方法"""
        response = client.patch("/api/v1/sessions/")
        assert response.status_code == 405
        
        response = client.put("/api/v1/sessions/test_session")
        assert response.status_code == 405
    
    @patch('backend.services.session_service.SessionService')
    def test_internal_server_error(self, mock_service, client):
        """测试内部服务器错误"""
        # 模拟服务抛出异常
        mock_service.return_value.create_session.side_effect = Exception("Database error")
        
        response = client.post("/api/v1/sessions/")
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
    
    def test_service_unavailable(self, client):
        """测试服务不可用"""
        with patch('backend.services.session_service.SessionService') as mock_service:
            mock_service.return_value.create_session.side_effect = ConnectionError("Service unavailable")
            
            response = client.post("/api/v1/sessions/")
            assert response.status_code in [500, 503]


class TestSessionsPerformance:
    """会话API性能测试"""
    
    def test_session_creation_performance(self, client):
        """测试会话创建性能"""
        start_time = time.time()
        
        # 创建多个会话
        for _ in range(10):
            response = client.post("/api/v1/sessions/")
            assert response.status_code == 201
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 平均每个会话创建时间应该在合理范围内
        avg_time_per_session = total_time / 10
        assert avg_time_per_session < 1.0  # 每个会话创建应该少于1秒
    
    def test_session_list_performance(self, client):
        """测试会话列表获取性能"""
        # 先创建一些会话
        for _ in range(20):
            client.post("/api/v1/sessions/")
        
        start_time = time.time()
        response = client.get("/api/v1/sessions/")
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 2.0  # 获取会话列表应该少于2秒
    
    @pytest.mark.asyncio
    async def test_concurrent_session_access(self, async_client):
        """测试并发会话访问性能"""
        # 创建一个会话
        create_response = await async_client.post("/api/v1/sessions/")
        session_id = create_response.json()["session_id"]
        
        # 并发访问同一个会话
        start_time = time.time()
        
        tasks = [
            async_client.get(f"/api/v1/sessions/{session_id}")
            for _ in range(10)
        ]
        
        responses = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # 所有请求都应该成功
        for response in responses:
            assert response.status_code == 200
        
        total_time = end_time - start_time
        assert total_time < 3.0  # 10个并发请求应该在3秒内完成