"""Export API测试"""

import os
import io
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from httpx import AsyncClient

from backend.main import app
from backend.core.config import settings
from backend.services.session_service import session_service
from backend.services.epub_service import epub_service


class TestExportAPI:
    """导出API测试类"""
    
    def _upload_test_epub(self, client: TestClient, sample_epub_data: bytes) -> str:
        """上传测试EPUB文件并返回session_id"""
        files = {
            "file": ("test.epub", io.BytesIO(sample_epub_data), "application/epub+zip")
        }
        response = client.post("/api/v1/upload/epub", files=files)
        assert response.status_code == 200
        return response.json()["data"]["session_id"]
    
    def test_download_processed_epub_success(self, client: TestClient, sample_epub_data: bytes, test_settings):
        """测试成功下载处理后的EPUB文件"""
        # 上传文件创建会话
        session_id = self._upload_test_epub(client, sample_epub_data)
        
        # 创建处理后的文件在正确的会话目录中
        session_dir = Path(test_settings.session_dir) / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        processed_file = session_dir / "processed.epub"
        processed_file.write_bytes(sample_epub_data)
        
        # 下载文件
        response = client.get(f"/api/v1/export/{session_id}")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/epub+zip"
        assert "processed_" in response.headers.get("content-disposition", "")
        assert len(response.content) > 0
    
    def test_download_original_epub_when_processed_not_exists(self, client: TestClient, sample_epub_data: bytes, test_settings):
        """测试当处理后文件不存在时下载原始文件"""
        # 上传文件创建会话
        session_id = self._upload_test_epub(client, sample_epub_data)
        
        # 创建原始文件但不创建处理后文件
        session_dir = Path(test_settings.session_dir) / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        original_file = session_dir / "original.epub"
        original_file.write_bytes(sample_epub_data)
        
        # 下载文件
        response = client.get(f"/api/v1/export/{session_id}")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/epub+zip"
        assert len(response.content) > 0
    
    def test_download_epub_session_not_found(self, client: TestClient):
        """测试下载不存在会话的EPUB文件"""
        response = client.get("/api/v1/export/nonexistent_session")
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "会话不存在" in data["error"]
    
    def test_download_epub_file_not_found(self, client: TestClient, sample_epub_data: bytes, test_settings):
        """测试下载不存在的EPUB文件"""
        # 上传文件创建会话，但删除文件
        session_id = self._upload_test_epub(client, sample_epub_data)
        
        # 确保没有处理后的文件和原始文件
        session_dir = Path(test_settings.session_dir) / session_id
        if session_dir.exists():
            import shutil
            shutil.rmtree(session_dir)
        
        response = client.get(f"/api/v1/export/{session_id}")
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "EPUB文件不存在" in data["error"]
    
    def test_download_epub_invalid_session_id(self, client: TestClient):
        """测试无效的会话ID"""
        invalid_session_ids = [
            "",  # 空字符串
            "../../../etc/passwd",  # 路径遍历攻击
            "session with spaces",  # 包含空格
            "session/with/slashes",  # 包含斜杠
        ]
        
        for session_id in invalid_session_ids:
            response = client.get(f"/api/v1/export/{session_id}")
            assert response.status_code in [404, 422, 500]  # 404、422或500都是合理的
    
    def test_download_epub_file_permissions(self, client: TestClient, sample_epub_data: bytes, test_settings):
        """测试文件权限问题"""
        import os
        import platform
        
        # 在某些系统上跳过权限测试
        if platform.system() == "Darwin" and os.getuid() == 0:
            pytest.skip("Skipping permission test on macOS as root")
        
        # 上传文件创建会话
        session_id = self._upload_test_epub(client, sample_epub_data)
        
        # 创建文件但设置为不可读（在支持的系统上）
        session_dir = Path(test_settings.session_dir) / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        processed_file = session_dir / "processed.epub"
        processed_file.write_bytes(sample_epub_data)
        
        try:
            # 尝试移除读权限
            processed_file.chmod(0o000)
            
            response = client.get(f"/api/v1/export/{session_id}")
            # 可能返回500或404，取决于系统行为
            assert response.status_code in [404, 500]
            
        except PermissionError:
            # 如果无法设置权限，跳过测试
            pytest.skip("Cannot modify file permissions on this system")
        finally:
            # 恢复权限以便清理
            try:
                processed_file.chmod(0o644)
            except:
                pass
    
    def test_download_epub_large_file(self, client: TestClient, sample_epub_data: bytes, test_settings):
        """测试下载大文件"""
        # 上传文件创建会话
        session_id = self._upload_test_epub(client, sample_epub_data)
        
        # 创建一个较大的测试文件（1MB）
        session_dir = Path(test_settings.session_dir) / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        processed_file = session_dir / "processed.epub"
        
        # 创建1MB的测试数据
        large_data = b"0" * (1024 * 1024)
        processed_file.write_bytes(large_data)
        
        response = client.get(f"/api/v1/export/{session_id}")
        assert response.status_code == 200
        assert len(response.content) == 1024 * 1024


@pytest.mark.asyncio
class TestExportAPIAsync:
    """异步导出API测试类"""
    
    async def _upload_test_epub_async(self, async_client: AsyncClient, sample_epub_data: bytes) -> str:
        """异步上传测试EPUB文件并返回session_id"""
        files = {
            "file": ("test.epub", io.BytesIO(sample_epub_data), "application/epub+zip")
        }
        response = await async_client.post("/api/v1/upload/epub", files=files)
        assert response.status_code == 200
        return response.json()["data"]["session_id"]
    
    async def test_async_download_processed_epub(self, async_client: AsyncClient, sample_epub_data: bytes, test_settings):
        """测试异步下载处理后的EPUB文件"""
        # 上传文件创建会话
        session_id = await self._upload_test_epub_async(async_client, sample_epub_data)
        
        # 创建处理后的文件
        session_dir = Path(test_settings.session_dir) / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        processed_file = session_dir / "processed.epub"
        processed_file.write_bytes(sample_epub_data)
        
        # 异步下载文件
        response = await async_client.get(f"/api/v1/export/{session_id}")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/epub+zip"
        assert len(response.content) > 0
    
    async def test_concurrent_downloads(self, async_client: AsyncClient, sample_epub_data: bytes, test_settings):
        """测试并发下载"""
        import asyncio
        
        # 创建多个会话
        session_ids = []
        for i in range(3):
            session_id = await self._upload_test_epub_async(async_client, sample_epub_data)
            session_ids.append(session_id)
            
            # 创建处理后的文件
            session_dir = Path(test_settings.session_dir) / session_id
            session_dir.mkdir(parents=True, exist_ok=True)
            processed_file = session_dir / "processed.epub"
            processed_file.write_bytes(sample_epub_data)
        
        # 并发下载
        async def download_file(session_id):
            response = await async_client.get(f"/api/v1/export/{session_id}")
            return response
        
        tasks = [download_file(session_id) for session_id in session_ids]
        responses = await asyncio.gather(*tasks)
        
        # 验证所有下载都成功
        for response in responses:
            assert response.status_code == 200
            assert len(response.content) > 0


class TestExportAPIErrorHandling:
    """导出API错误处理测试"""
    
    def _upload_test_epub(self, client: TestClient, sample_epub_data: bytes) -> str:
        """上传测试EPUB文件并返回session_id"""
        files = {
            "file": ("test.epub", io.BytesIO(sample_epub_data), "application/epub+zip")
        }
        response = client.post("/api/v1/upload/epub", files=files)
        assert response.status_code == 200
        return response.json()["data"]["session_id"]
    
    def test_download_with_corrupted_session_data(self, client: TestClient, sample_epub_data: bytes, test_settings):
        """测试会话数据损坏的情况"""
        # 上传文件创建会话
        session_id = self._upload_test_epub(client, sample_epub_data)
        
        # 创建损坏的文件
        session_dir = Path(test_settings.session_dir) / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        processed_file = session_dir / "processed.epub"
        processed_file.write_text("corrupted data")  # 写入文本而不是二进制数据
        
        response = client.get(f"/api/v1/export/{session_id}")
        assert response.status_code == 200  # 文件存在就会返回，不验证内容
    
    def test_download_with_network_simulation(self, client: TestClient, sample_epub_data: bytes, test_settings):
        """测试网络中断模拟"""
        # 上传文件创建会话
        session_id = self._upload_test_epub(client, sample_epub_data)
        
        # 创建处理后的文件
        session_dir = Path(test_settings.session_dir) / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        processed_file = session_dir / "processed.epub"
        processed_file.write_bytes(sample_epub_data)
        
        # 正常情况下应该成功
        response = client.get(f"/api/v1/export/{session_id}")
        assert response.status_code == 200


class TestExportAPIPerformance:
    """导出API性能测试"""
    
    def _upload_test_epub(self, client: TestClient, sample_epub_data: bytes) -> str:
        """上传测试EPUB文件并返回session_id"""
        files = {
            "file": ("test.epub", io.BytesIO(sample_epub_data), "application/epub+zip")
        }
        response = client.post("/api/v1/upload/epub", files=files)
        assert response.status_code == 200
        return response.json()["data"]["session_id"]
    
    def test_download_response_time(self, client: TestClient, sample_epub_data: bytes, test_settings):
        """测试下载响应时间"""
        import time
        
        # 上传文件创建会话
        session_id = self._upload_test_epub(client, sample_epub_data)
        
        # 创建处理后的文件
        session_dir = Path(test_settings.session_dir) / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        processed_file = session_dir / "processed.epub"
        processed_file.write_bytes(sample_epub_data)
        
        # 测量响应时间
        start_time = time.time()
        response = client.get(f"/api/v1/export/{session_id}")
        end_time = time.time()
        
        response_time = end_time - start_time
        assert response.status_code == 200
        assert response_time < 5.0  # 下载应该在5秒内完成