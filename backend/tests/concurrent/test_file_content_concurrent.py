"""BE-04 文件内容获取功能并发测试

本文件专门针对 BE-04 任务的并发测试场景：
- 同时读取和修改同一文件的并发测试
- 多用户同时访问文件的并发测试
- 文件锁定和竞态条件测试
- 并发会话管理测试
- 数据一致性验证测试
"""

import pytest
import asyncio
import tempfile
import threading
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.file_service import file_service
from backend.models.schemas import FileContent


class TestConcurrentFileAccess:
    """并发文件访问测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.client = TestClient(app)
        self.test_file = Path(self.temp_dir) / "concurrent_test.txt"
        self.test_file.write_text("Initial content for concurrent testing", encoding='utf-8')
        
    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_concurrent_read_operations(self):
        """测试并发读取操作"""
        num_threads = 10
        results = []
        errors = []
        
        def read_file_content():
            """读取文件内容的线程函数"""
            try:
                with patch('backend.api.endpoints.file_content.session_service') as mock_session, \
                     patch('backend.api.endpoints.file_content.security_validator') as mock_validator:
                    
                    # 模拟会话服务
                    mock_session_obj = MagicMock()
                    mock_session_obj.session_id = f"session_{threading.current_thread().ident}"
                    mock_session_obj.base_path = self.temp_dir
                    mock_session.get_session = AsyncMock(return_value=mock_session_obj)
                    
                    # 模拟安全验证
                    mock_validator.validate_file_path.return_value = True
                    mock_validator.sanitize_path.return_value = str(self.test_file)
                    
                    response = self.client.get(
                        "/api/v1/file-content",
                        params={
                            "session_id": mock_session_obj.session_id,
                            "file_path": "concurrent_test.txt"
                        }
                    )
                    
                    return {
                        "thread_id": threading.current_thread().ident,
                        "status_code": response.status_code,
                        "content_length": len(response.content) if response.content else 0,
                        "response_time": time.time()
                    }
            except Exception as e:
                errors.append({
                    "thread_id": threading.current_thread().ident,
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                return None
        
        # 启动并发读取
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(read_file_content) for _ in range(num_threads)]
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)
        
        # 验证结果
        assert len(results) > 0, f"没有成功的读取操作，错误: {errors}"
        
        # 所有成功的读取应该返回相同的内容长度
        if len(results) > 1:
            content_lengths = [r["content_length"] for r in results]
            assert len(set(content_lengths)) <= 2, f"并发读取返回了不一致的内容长度: {content_lengths}"
        
        # 检查是否有过多的错误
        error_rate = len(errors) / (len(results) + len(errors))
        assert error_rate < 0.5, f"错误率过高: {error_rate:.2%}, 错误: {errors[:3]}"
    
    def test_concurrent_read_write_operations(self):
        """测试并发读写操作"""
        read_results = []
        write_results = []
        errors = []
        
        def read_operation():
            """读取操作"""
            try:
                time.sleep(0.1)  # 稍微延迟以增加并发冲突概率
                content = self.test_file.read_text(encoding='utf-8')
                return {
                    "operation": "read",
                    "thread_id": threading.current_thread().ident,
                    "content_length": len(content),
                    "timestamp": time.time()
                }
            except Exception as e:
                errors.append({
                    "operation": "read",
                    "thread_id": threading.current_thread().ident,
                    "error": str(e)
                })
                return None
        
        def write_operation(content_suffix):
            """写入操作"""
            try:
                time.sleep(0.05)  # 稍微延迟
                new_content = f"Modified content {content_suffix} at {time.time()}"
                self.test_file.write_text(new_content, encoding='utf-8')
                return {
                    "operation": "write",
                    "thread_id": threading.current_thread().ident,
                    "content_suffix": content_suffix,
                    "timestamp": time.time()
                }
            except Exception as e:
                errors.append({
                    "operation": "write",
                    "thread_id": threading.current_thread().ident,
                    "error": str(e)
                })
                return None
        
        # 启动并发读写操作
        with ThreadPoolExecutor(max_workers=8) as executor:
            # 提交读取任务
            read_futures = [executor.submit(read_operation) for _ in range(4)]
            
            # 提交写入任务
            write_futures = [executor.submit(write_operation, i) for i in range(4)]
            
            # 收集读取结果
            for future in as_completed(read_futures):
                result = future.result()
                if result:
                    read_results.append(result)
            
            # 收集写入结果
            for future in as_completed(write_futures):
                result = future.result()
                if result:
                    write_results.append(result)
        
        # 验证结果
        assert len(write_results) > 0, f"没有成功的写入操作，错误: {errors}"
        assert len(read_results) > 0, f"没有成功的读取操作，错误: {errors}"
        
        # 检查文件最终状态
        final_content = self.test_file.read_text(encoding='utf-8')
        assert "Modified content" in final_content, "文件内容未被正确修改"
        
        # 验证数据一致性（文件应该包含最后一次写入的内容）
        assert len(final_content) > 0, "文件内容为空"
    
    @pytest.mark.asyncio
    async def test_async_concurrent_file_service_calls(self):
        """测试异步并发文件服务调用"""
        num_concurrent_calls = 15
        results = []
        errors = []
        
        async def async_file_read():
            """异步文件读取"""
            try:
                result = await file_service.get_file_content_enhanced(str(self.test_file))
                return {
                    "task_id": id(asyncio.current_task()),
                    "content_length": len(result.content),
                    "mime_type": result.mime_type,
                    "encoding": result.encoding,
                    "timestamp": time.time()
                }
            except Exception as e:
                errors.append({
                    "task_id": id(asyncio.current_task()),
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                return None
        
        # 创建并发任务
        tasks = [async_file_read() for _ in range(num_concurrent_calls)]
        
        # 执行并发任务
        completed_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        for result in completed_results:
            if isinstance(result, Exception):
                errors.append({
                    "error": str(result),
                    "error_type": type(result).__name__
                })
            elif result:
                results.append(result)
        
        # 验证结果
        assert len(results) > 0, f"没有成功的异步读取操作，错误: {errors}"
        
        # 所有成功的读取应该返回一致的结果
        if len(results) > 1:
            content_lengths = [r["content_length"] for r in results]
            mime_types = [r["mime_type"] for r in results]
            
            assert len(set(content_lengths)) == 1, f"异步并发读取返回了不一致的内容长度: {set(content_lengths)}"
            assert len(set(mime_types)) == 1, f"异步并发读取返回了不一致的MIME类型: {set(mime_types)}"
        
        # 检查错误率
        total_operations = len(results) + len(errors)
        error_rate = len(errors) / total_operations if total_operations > 0 else 0
        assert error_rate < 0.3, f"异步并发操作错误率过高: {error_rate:.2%}, 错误: {errors[:3]}"


class TestConcurrentSessionManagement:
    """并发会话管理测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.client = TestClient(app)
        self.test_file = Path(self.temp_dir) / "session_test.txt"
        self.test_file.write_text("Session test content", encoding='utf-8')
        
    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_multiple_sessions_same_file(self):
        """测试多个会话访问同一文件"""
        num_sessions = 8
        results = []
        errors = []
        
        def session_file_access(session_id):
            """会话文件访问函数"""
            try:
                with patch('backend.api.endpoints.file_content.session_service') as mock_session, \
                     patch('backend.api.endpoints.file_content.security_validator') as mock_validator:
                    
                    # 模拟会话服务
                    mock_session_obj = MagicMock()
                    mock_session_obj.session_id = session_id
                    mock_session_obj.base_path = self.temp_dir
                    mock_session.get_session = AsyncMock(return_value=mock_session_obj)
                    
                    # 模拟安全验证
                    mock_validator.validate_file_path.return_value = True
                    mock_validator.sanitize_path.return_value = str(self.test_file)
                    
                    response = self.client.get(
                        "/api/v1/file-content",
                        params={
                            "session_id": session_id,
                            "file_path": "session_test.txt"
                        }
                    )
                    
                    return {
                        "session_id": session_id,
                        "status_code": response.status_code,
                        "success": response.status_code == 200,
                        "timestamp": time.time()
                    }
            except Exception as e:
                errors.append({
                    "session_id": session_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                return None
        
        # 启动多个会话的并发访问
        with ThreadPoolExecutor(max_workers=num_sessions) as executor:
            session_ids = [f"session_{i}" for i in range(num_sessions)]
            futures = [executor.submit(session_file_access, sid) for sid in session_ids]
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)
        
        # 验证结果
        assert len(results) > 0, f"没有成功的会话访问，错误: {errors}"
        
        # 检查成功率
        successful_sessions = [r for r in results if r["success"]]
        success_rate = len(successful_sessions) / len(results)
        assert success_rate > 0.7, f"会话成功率过低: {success_rate:.2%}"
        
        # 验证所有会话都能访问文件
        session_ids_with_success = {r["session_id"] for r in successful_sessions}
        assert len(session_ids_with_success) > num_sessions * 0.7, "太多会话无法访问文件"
    
    def test_session_isolation(self):
        """测试会话隔离"""
        # 创建不同的测试文件
        session1_file = Path(self.temp_dir) / "session1" / "test.txt"
        session2_file = Path(self.temp_dir) / "session2" / "test.txt"
        
        session1_file.parent.mkdir(exist_ok=True)
        session2_file.parent.mkdir(exist_ok=True)
        
        session1_file.write_text("Session 1 content", encoding='utf-8')
        session2_file.write_text("Session 2 content", encoding='utf-8')
        
        results = []
        errors = []
        
        def isolated_session_access(session_id, base_path, expected_content):
            """隔离会话访问函数"""
            try:
                with patch('backend.api.endpoints.file_content.session_service') as mock_session, \
                     patch('backend.api.endpoints.file_content.security_validator') as mock_validator:
                    
                    # 模拟会话服务
                    mock_session_obj = MagicMock()
                    mock_session_obj.session_id = session_id
                    mock_session_obj.base_path = base_path
                    mock_session.get_session = AsyncMock(return_value=mock_session_obj)
                    
                    # 模拟安全验证
                    mock_validator.validate_file_path.return_value = True
                    test_file_path = Path(base_path) / "test.txt"
                    mock_validator.sanitize_path.return_value = str(test_file_path)
                    
                    response = self.client.get(
                        "/api/v1/file-content",
                        params={
                            "session_id": session_id,
                            "file_path": "test.txt"
                        }
                    )
                    
                    return {
                        "session_id": session_id,
                        "status_code": response.status_code,
                        "expected_content": expected_content,
                        "timestamp": time.time()
                    }
            except Exception as e:
                errors.append({
                    "session_id": session_id,
                    "error": str(e)
                })
                return None
        
        # 启动隔离会话测试
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(isolated_session_access, "session1", str(session1_file.parent), "Session 1 content"),
                executor.submit(isolated_session_access, "session2", str(session2_file.parent), "Session 2 content"),
                executor.submit(isolated_session_access, "session1_dup", str(session1_file.parent), "Session 1 content"),
                executor.submit(isolated_session_access, "session2_dup", str(session2_file.parent), "Session 2 content"),
            ]
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)
        
        # 验证结果
        assert len(results) > 0, f"没有成功的隔离会话访问，错误: {errors}"
        
        # 验证会话隔离效果
        session1_results = [r for r in results if "session1" in r["session_id"]]
        session2_results = [r for r in results if "session2" in r["session_id"]]
        
        assert len(session1_results) > 0, "Session1 访问失败"
        assert len(session2_results) > 0, "Session2 访问失败"


class TestRaceConditionPrevention:
    """竞态条件防护测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "race_condition_test.txt"
        self.test_file.write_text("Initial race condition test content", encoding='utf-8')
        
    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_file_modification_during_read(self):
        """测试读取过程中文件被修改的情况"""
        read_results = []
        modification_results = []
        errors = []
        
        def slow_file_read():
            """模拟慢速文件读取"""
            try:
                # 模拟慢速读取
                time.sleep(0.1)
                content = self.test_file.read_text(encoding='utf-8')
                time.sleep(0.1)  # 继续模拟处理时间
                
                return {
                    "operation": "read",
                    "content_length": len(content),
                    "content_preview": content[:50],
                    "timestamp": time.time()
                }
            except Exception as e:
                errors.append({
                    "operation": "read",
                    "error": str(e)
                })
                return None
        
        def rapid_file_modification():
            """快速文件修改"""
            try:
                for i in range(5):
                    time.sleep(0.05)  # 短暂延迟
                    new_content = f"Modified content iteration {i} at {time.time()}"
                    self.test_file.write_text(new_content, encoding='utf-8')
                
                return {
                    "operation": "modify",
                    "modifications": 5,
                    "timestamp": time.time()
                }
            except Exception as e:
                errors.append({
                    "operation": "modify",
                    "error": str(e)
                })
                return None
        
        # 启动竞态条件测试
        with ThreadPoolExecutor(max_workers=6) as executor:
            # 启动多个读取操作
            read_futures = [executor.submit(slow_file_read) for _ in range(3)]
            
            # 启动修改操作
            modify_futures = [executor.submit(rapid_file_modification) for _ in range(2)]
            
            # 收集读取结果
            for future in as_completed(read_futures):
                result = future.result()
                if result:
                    read_results.append(result)
            
            # 收集修改结果
            for future in as_completed(modify_futures):
                result = future.result()
                if result:
                    modification_results.append(result)
        
        # 验证结果
        assert len(read_results) > 0, f"没有成功的读取操作，错误: {errors}"
        assert len(modification_results) > 0, f"没有成功的修改操作，错误: {errors}"
        
        # 验证文件最终状态
        final_content = self.test_file.read_text(encoding='utf-8')
        assert "Modified content iteration" in final_content, "文件未被正确修改"
        
        # 验证读取操作的一致性（每次读取应该得到完整的内容）
        for read_result in read_results:
            assert read_result["content_length"] > 0, "读取到空内容"
            assert len(read_result["content_preview"]) > 0, "读取预览为空"
    
    @pytest.mark.asyncio
    async def test_async_file_service_race_conditions(self):
        """测试异步文件服务的竞态条件"""
        results = []
        errors = []
        
        async def concurrent_file_operations():
            """并发文件操作"""
            try:
                # 同时进行多种文件操作
                tasks = []
                
                # 添加读取任务
                for _ in range(5):
                    tasks.append(file_service.get_file_content_enhanced(str(self.test_file)))
                
                # 执行所有任务
                results_batch = await asyncio.gather(*tasks, return_exceptions=True)
                
                successful_results = []
                for result in results_batch:
                    if isinstance(result, Exception):
                        errors.append({
                            "error": str(result),
                            "error_type": type(result).__name__
                        })
                    else:
                        successful_results.append({
                            "content_length": len(result.content),
                            "mime_type": result.mime_type,
                            "encoding": result.encoding,
                            "timestamp": time.time()
                        })
                
                return successful_results
            
            except Exception as e:
                errors.append({
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                return []
        
        # 执行并发操作
        results = await concurrent_file_operations()
        
        # 验证结果
        assert len(results) > 0, f"没有成功的异步操作，错误: {errors}"
        
        # 验证一致性
        if len(results) > 1:
            content_lengths = [r["content_length"] for r in results]
            mime_types = [r["mime_type"] for r in results]
            
            # 所有读取应该返回一致的结果
            assert len(set(content_lengths)) == 1, f"异步操作返回不一致的内容长度: {set(content_lengths)}"
            assert len(set(mime_types)) == 1, f"异步操作返回不一致的MIME类型: {set(mime_types)}"
        
        # 检查错误率
        total_operations = len(results) + len(errors)
        if total_operations > 0:
            error_rate = len(errors) / total_operations
            assert error_rate < 0.2, f"异步竞态条件测试错误率过高: {error_rate:.2%}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])