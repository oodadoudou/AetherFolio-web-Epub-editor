import pytest
import pytest_asyncio
import asyncio
import os
import json
import tempfile
import shutil
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient
from pathlib import Path

from backend.main import app
from backend.models.schemas import SaveFileRequest
from backend.api.endpoints.save_file import router, FileBackupManager, FileHistoryManager, calculate_content_hash, verify_file_integrity, get_file_lock
from backend.services.session_service import session_service
from backend.services.file_service import file_service


class TestSaveFileAPI:
    """保存文件API测试"""
    
    @pytest.fixture
    def client(self):
        """测试客户端"""
        return TestClient(app)
    
    @pytest_asyncio.fixture
    async def async_client(self):
        """异步测试客户端"""
        from httpx import AsyncClient
        from fastapi.testclient import TestClient
        # 使用同步客户端进行异步测试
        yield TestClient(app)
    
    @pytest.fixture
    def temp_dir(self):
        """临时目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def mock_session_service(self):
        """模拟会话服务"""
        with patch('backend.api.endpoints.save_file.session_service') as mock:
            mock_session = MagicMock()
            mock_session.metadata = {"file_type": "text", "session_dir": "/tmp/test_session"}
            mock.get_session = AsyncMock(return_value=mock_session)
            yield mock
    
    @pytest.fixture
    def mock_file_service(self):
        """模拟文件服务"""
        with patch('backend.api.endpoints.save_file.file_service') as mock:
            yield mock
    
    def test_save_file_success(self, client, mock_session_service, mock_file_service, temp_dir):
        """测试成功保存文件"""
        # 准备测试数据
        session_id = "test_session_123"
        file_path = "test.txt"
        content = "测试文件内容"
        
        # 模拟文件服务返回原始内容
        from backend.models.file import FileContent
        original_content = FileContent(
            path=file_path,
            content="原始内容",
            mime_type="text/plain",
            size=12,
            encoding="utf-8"
        )
        mock_file_service.get_file_content_enhanced = AsyncMock(return_value=original_content)
        
        # 模拟会话目录
        session_dir = Path(temp_dir) / "session"
        session_dir.mkdir(exist_ok=True)
        mock_session_service.get_session.return_value.metadata["session_dir"] = str(session_dir)
        
        with patch('backend.api.endpoints.save_file.security_validator') as mock_validator:
            mock_validator.validate_file_path.return_value = True
            
            # 发送请求
            response = client.post(
                "/api/v1/save-file",
                json={
                    "session_id": session_id,
                    "file_path": file_path,
                    "content": content,
                    "encoding": "utf-8"
                }
            )
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "文件保存成功"
        assert "data" in data
        assert data["data"]["file_path"] == file_path
        assert "content_hash" in data["data"]
        assert "backup_created" in data["data"]
        assert "integrity_verified" in data["data"]
    
    def test_save_file_invalid_session(self, client):
        """测试无效会话"""
        with patch('backend.api.endpoints.save_file.session_service') as mock_session:
            mock_session.get_session = AsyncMock(return_value=None)
            
            response = client.post(
                "/api/v1/save-file",
                json={
                    "session_id": "invalid_session",
                    "file_path": "test.txt",
                    "content": "test content",
                    "encoding": "utf-8"
                }
            )
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "会话不存在" in data["error"]
    
    def test_save_file_invalid_path(self, client, mock_session_service):
        """测试无效文件路径"""
        with patch('backend.api.endpoints.save_file.security_validator') as mock_validator:
            mock_validator.validate_file_path.return_value = False
            
            response = client.post(
                "/api/v1/save-file",
                json={
                    "session_id": "test_session",
                    "file_path": "../../../etc/passwd",
                    "content": "malicious content",
                    "encoding": "utf-8"
                }
            )
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "文件路径无效" in data["error"]
    
    @pytest.mark.asyncio
    async def test_concurrent_save_operations(self, async_client, mock_session_service, mock_file_service, temp_dir):
        """测试并发保存操作"""
        session_id = "test_session_123"
        file_path = "concurrent_test.txt"
        
        # 模拟文件服务
        from backend.models.file import FileContent
        original_content = FileContent(
            path=file_path,
            content="原始内容",
            mime_type="text/plain",
            size=12,
            encoding="utf-8"
        )
        mock_file_service.get_file_content_enhanced = AsyncMock(return_value=original_content)
        
        # 模拟会话目录
        session_dir = Path(temp_dir) / "session"
        session_dir.mkdir(exist_ok=True)
        mock_session_service.get_session.return_value.metadata["session_dir"] = str(session_dir)
        
        with patch('backend.api.endpoints.save_file.security_validator') as mock_validator:
            mock_validator.validate_file_path.return_value = True
            
            # 创建多个并发请求
            responses = []
            for i in range(5):
                response = async_client.post(
                    "/api/v1/save-file",
                    json={
                        "session_id": session_id,
                        "file_path": file_path,
                        "content": f"并发内容 {i}",
                        "encoding": "utf-8"
                    }
                )
                responses.append(response)
        
        # 验证所有请求都成功
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
    
    def test_get_file_history_success(self, client, mock_session_service, temp_dir):
        """测试获取文件历史记录成功"""
        session_id = "test_session_123"
        
        # 创建模拟历史文件
        history_dir = Path(temp_dir) / "history"
        history_dir.mkdir(exist_ok=True)
        history_file = history_dir / f"{session_id}_history.json"
        
        history_data = [
            {
                "timestamp": "2024-01-01T10:00:00",
                "file_path": "test.txt",
                "backup_path": "/tmp/backup1.bak",
                "content_hash": "hash1",
                "file_size": 100,
                "encoding": "utf-8",
                "version": 1
            },
            {
                "timestamp": "2024-01-01T11:00:00",
                "file_path": "test.txt",
                "backup_path": "/tmp/backup2.bak",
                "content_hash": "hash2",
                "file_size": 150,
                "encoding": "utf-8",
                "version": 2
            }
        ]
        
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history_data, f)
        
        with patch('backend.api.endpoints.save_file.history_manager') as mock_history:
            mock_history._get_history_file.return_value = str(history_file)
            
            response = client.get(f"/api/v1/file-history/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "history" in data["data"]
        assert len(data["data"]["history"]) == 2
        assert data["data"]["total_count"] == 2
    
    def test_get_file_history_no_history(self, client, mock_session_service):
        """测试获取不存在的历史记录"""
        session_id = "test_session_123"
        
        with patch('backend.api.endpoints.save_file.history_manager') as mock_history:
            mock_history._get_history_file.return_value = "/nonexistent/history.json"
            
            response = client.get(f"/api/v1/file-history/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "暂无修改历史"
        assert data["data"]["history"] == []


class TestFileBackupManager:
    """文件备份管理器测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """临时目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def backup_manager(self, temp_dir):
        """备份管理器"""
        backup_dir = os.path.join(temp_dir, "backups")
        return FileBackupManager(backup_dir)
    
    @pytest.mark.asyncio
    async def test_create_backup(self, backup_manager, temp_dir):
        """测试创建备份"""
        session_id = "test_session"
        file_path = "test.txt"
        content = "测试内容"
        encoding = "utf-8"
        
        backup_path = await backup_manager.create_backup(
            session_id, file_path, content, encoding
        )
        
        # 验证备份文件存在
        assert os.path.exists(backup_path)
        
        # 验证备份内容
        with open(backup_path, 'r', encoding=encoding) as f:
            backup_content = f.read()
        assert backup_content == content
    
    @pytest.mark.asyncio
    async def test_cleanup_old_backups(self, backup_manager, temp_dir):
        """测试清理旧备份"""
        session_id = "test_session"
        
        # 创建多个备份文件
        backup_files = []
        for i in range(15):
            backup_path = await backup_manager.create_backup(
                session_id, f"test{i}.txt", f"内容{i}", "utf-8"
            )
            backup_files.append(backup_path)
        
        # 清理旧备份，保留最新的10个
        await backup_manager.cleanup_old_backups(session_id, max_backups=10)
        
        # 验证只保留了10个备份
        remaining_files = [
            f for f in os.listdir(backup_manager.backup_dir)
            if f.startswith(f"{session_id}_") and f.endswith(".bak")
        ]
        assert len(remaining_files) == 10


class TestFileHistoryManager:
    """文件历史管理器测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """临时目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def history_manager(self, temp_dir):
        """历史管理器"""
        history_dir = os.path.join(temp_dir, "history")
        return FileHistoryManager(history_dir)
    
    @pytest.mark.asyncio
    async def test_add_history_record(self, history_manager):
        """测试添加历史记录"""
        session_id = "test_session"
        file_path = "test.txt"
        backup_path = "/tmp/backup.bak"
        content_hash = "test_hash"
        file_size = 100
        encoding = "utf-8"
        
        await history_manager.add_history_record(
            session_id, file_path, backup_path, content_hash, file_size, encoding
        )
        
        # 验证历史文件存在
        history_file = history_manager._get_history_file(session_id)
        assert os.path.exists(history_file)
        
        # 验证历史记录内容
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
        
        assert len(history) == 1
        record = history[0]
        assert record["file_path"] == file_path
        assert record["backup_path"] == backup_path
        assert record["content_hash"] == content_hash
        assert record["file_size"] == file_size
        assert record["encoding"] == encoding
        assert record["version"] == 1
    
    @pytest.mark.asyncio
    async def test_version_increment(self, history_manager):
        """测试版本号递增"""
        session_id = "test_session"
        file_path = "test.txt"
        
        # 添加多个历史记录
        for i in range(3):
            await history_manager.add_history_record(
                session_id, file_path, f"/tmp/backup{i}.bak", 
                f"hash{i}", 100 + i, "utf-8"
            )
        
        # 验证版本号递增
        history_file = history_manager._get_history_file(session_id)
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
        
        versions = [record["version"] for record in history if record["file_path"] == file_path]
        assert versions == [1, 2, 3]


class TestUtilityFunctions:
    """工具函数测试"""
    
    def test_calculate_content_hash(self):
        """测试内容哈希计算"""
        content1 = "测试内容"
        content2 = "测试内容"
        content3 = "不同内容"
        
        hash1 = calculate_content_hash(content1)
        hash2 = calculate_content_hash(content2)
        hash3 = calculate_content_hash(content3)
        
        # 相同内容应该有相同哈希
        assert hash1 == hash2
        # 不同内容应该有不同哈希
        assert hash1 != hash3
        # 哈希应该是64位十六进制字符串
        assert len(hash1) == 64
        assert all(c in '0123456789abcdef' for c in hash1)
    
    @pytest.mark.asyncio
    async def test_verify_file_integrity(self, tmp_path):
        """测试文件完整性验证"""
        test_file = tmp_path / "test.txt"
        content = "测试文件内容"
        encoding = "utf-8"
        
        # 创建测试文件
        with open(test_file, 'w', encoding=encoding) as f:
            f.write(content)
        
        # 验证完整性
        result = await verify_file_integrity(str(test_file), content, encoding)
        assert result is True
        
        # 验证不匹配的内容
        result = await verify_file_integrity(str(test_file), "不同内容", encoding)
        assert result is False
        
        # 验证不存在的文件
        result = await verify_file_integrity("/nonexistent/file.txt", content, encoding)
        assert result is False
    
    def test_get_file_lock(self):
        """测试文件锁获取"""
        lock_key1 = "session1:file1.txt"
        lock_key2 = "session1:file1.txt"
        lock_key3 = "session2:file1.txt"
        
        lock1 = get_file_lock(lock_key1)
        lock2 = get_file_lock(lock_key2)
        lock3 = get_file_lock(lock_key3)
        
        # 相同键应该返回相同锁
        assert lock1 is lock2
        # 不同键应该返回不同锁
        assert lock1 is not lock3


class TestErrorHandling:
    """错误处理测试"""
    
    @pytest.fixture
    def client(self):
        """测试客户端"""
        return TestClient(app)
    
    def test_disk_space_error(self, client):
        """测试磁盘空间不足错误"""
        with patch('backend.api.endpoints.save_file.session_service') as mock_session:
            mock_session_info = MagicMock()
            mock_session_info.metadata = {"file_type": "text", "session_dir": "/tmp/test"}
            mock_session.get_session = AsyncMock(return_value=mock_session_info)
            
            with patch('backend.api.endpoints.save_file.security_validator') as mock_validator:
                mock_validator.validate_file_path.return_value = True
                
                with patch('builtins.open', side_effect=OSError("No space left on device")):
                    response = client.post(
                        "/api/v1/save-file",
                        json={
                            "session_id": "test_session",
                            "file_path": "test.txt",
                            "content": "test content",
                            "encoding": "utf-8"
                        }
                    )
        
        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False
        assert "文件保存失败" in data["error"]
    
    def test_permission_error(self, client):
        """测试权限错误"""
        with patch('backend.api.endpoints.save_file.session_service') as mock_session:
            mock_session_info = MagicMock()
            mock_session_info.metadata = {"file_type": "text", "session_dir": "/tmp/test"}
            mock_session.get_session = AsyncMock(return_value=mock_session_info)
            
            with patch('backend.api.endpoints.save_file.security_validator') as mock_validator:
                mock_validator.validate_file_path.return_value = True
                
                with patch('builtins.open', side_effect=PermissionError("Permission denied")):
                    response = client.post(
                        "/api/v1/save-file",
                        json={
                            "session_id": "test_session",
                            "file_path": "test.txt",
                            "content": "test content",
                            "encoding": "utf-8"
                        }
                    )
        
        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False
        assert "文件保存失败" in data["error"]


class TestIntegration:
    """集成测试"""
    
    @pytest.fixture
    def client(self):
        """测试客户端"""
        return TestClient(app)
    
    @pytest.fixture
    def temp_dir(self):
        """临时目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_complete_save_workflow(self, client, temp_dir):
        """测试完整的保存工作流程"""
        session_id = "integration_test_session"
        file_path = "integration_test.txt"
        original_content = "原始文件内容"
        new_content = "修改后的文件内容"
        
        # 模拟会话和文件服务
        with patch('backend.api.endpoints.save_file.session_service') as mock_session:
            mock_session_info = MagicMock()
            session_dir = Path(temp_dir) / "session"
            session_dir.mkdir(exist_ok=True)
            mock_session_info.metadata = {"file_type": "text", "session_dir": str(session_dir)}
            mock_session.get_session = AsyncMock(return_value=mock_session_info)
            
            with patch('backend.api.endpoints.save_file.file_service') as mock_file_service:
                from backend.models.file import FileContent
                original_file_content = FileContent(
                    path=file_path,
                    content=original_content,
                    mime_type="text/plain",
                    size=len(original_content.encode('utf-8')),
                    encoding="utf-8"
                )
                mock_file_service.get_file_content_enhanced = AsyncMock(return_value=original_file_content)
                
                with patch('backend.api.endpoints.save_file.security_validator') as mock_validator:
                    mock_validator.validate_file_path.return_value = True
                    
                    with patch('backend.services.preview_service.preview_service') as mock_preview:
                        mock_preview.clear_preview_cache = AsyncMock()
                        
                        # 第一次保存
                        response1 = client.post(
                            "/api/v1/save-file",
                            json={
                                "session_id": session_id,
                                "file_path": file_path,
                                "content": new_content,
                                "encoding": "utf-8"
                            }
                        )
                        
                        assert response1.status_code == 200
                        data1 = response1.json()
                        assert data1["status"] == "success"
                        assert data1["data"]["backup_created"] is True
                        
                        # 第二次保存（应该创建新的备份和历史记录）
                        response2 = client.post(
                            "/api/v1/save-file",
                            json={
                                "session_id": session_id,
                                "file_path": file_path,
                                "content": new_content + " - 第二次修改",
                                "encoding": "utf-8"
                            }
                        )
                        
                        assert response2.status_code == 200
                        data2 = response2.json()
                        assert data2["status"] == "success"
                        
                        # 验证内容哈希不同
                        assert data1["data"]["content_hash"] != data2["data"]["content_hash"]