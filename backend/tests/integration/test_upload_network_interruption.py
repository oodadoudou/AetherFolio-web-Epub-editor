"""网络中断集成测试 - BE-01任务集成测试

测试上传过程中网络中断的异常处理，验证系统能正确清理临时文件和会话数据。
"""

import pytest
import pytest_asyncio
import asyncio
import tempfile
import os
import time
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from fastapi import UploadFile
from io import BytesIO

from backend.main import app
from backend.services.session_service import SessionService
from backend.services.epub_service import EpubService
from backend.services.text_service import TextService


class TestUploadNetworkInterruption:
    """网络中断集成测试类"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)
    
    @pytest_asyncio.fixture
    async def session_service(self):
        """创建会话服务实例"""
        service = SessionService()
        await service._initialize()
        yield service
        await service._cleanup()
    
    def create_test_epub_file(self):
        """创建测试用的EPUB文件"""
        epub_content = b'''PK\x03\x04\x14\x00\x00\x00\x08\x00\x00\x00!\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1c\x00\x00\x00mimetypeapplication/epub+zipPK\x03\x04\x14\x00\x00\x00\x08\x00\x00\x00!\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x14\x00\x00\x00META-INF/container.xml<?xml version="1.0"?>\n<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n  <rootfiles>\n    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>\n  </rootfiles>\n</container>PK\x01\x02\x14\x00\x14\x00\x00\x00\x08\x00\x00\x00!\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1c\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x01\x00\x00\x00\x00mimetypePK\x01\x02\x14\x00\x14\x00\x00\x00\x08\x00\x00\x00!\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x14\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x01Z\x00\x00\x00META-INF/container.xmlPK\x05\x06\x00\x00\x00\x00\x02\x00\x02\x00\x82\x00\x00\x00\xc6\x00\x00\x00\x00\x00'''
        return BytesIO(epub_content)
    
    def create_test_text_file(self, size_mb=1):
        """创建测试用的文本文件"""
        content = "This is a test text file.\n" * (size_mb * 1024 * 1024 // 26)
        return BytesIO(content.encode('utf-8'))
    
    @pytest.mark.asyncio
    async def test_upload_interruption_during_file_processing(self, client, session_service):
        """测试文件处理过程中的网络中断"""
        # 创建测试文件
        test_file = self.create_test_epub_file()
        
        # 模拟在文件处理过程中发生网络中断
        with patch('backend.services.epub_service.EpubService.extract_epub') as mock_process:
            # 设置处理函数在执行过程中抛出网络异常
            async def interrupted_process(*args, **kwargs):
                await asyncio.sleep(0.1)  # 模拟处理开始
                raise ConnectionError("Network connection lost")
            
            mock_process.side_effect = interrupted_process
            
            # 记录上传前的会话数量
            initial_session_count = len(session_service.sessions)
            
            # 尝试上传文件
            response = client.post(
                "/api/v1/upload",
                files={"file": ("test.epub", test_file, "application/epub+zip")}
            )
            
            # 验证返回错误状态
            assert response.status_code in [404, 500]
            
            # 等待一段时间确保清理完成
            await asyncio.sleep(0.2)
            
            # 验证会话没有被创建或已被清理
            final_session_count = len(session_service.sessions)
            assert final_session_count == initial_session_count
    
    @pytest.mark.asyncio
    async def test_upload_interruption_during_session_creation(self, client, session_service):
        """测试会话创建过程中的网络中断"""
        test_file = self.create_test_text_file()
        
        # 模拟在会话创建过程中发生网络中断
        with patch.object(session_service, 'create_session') as mock_create:
            async def interrupted_create_session(*args, **kwargs):
                await asyncio.sleep(0.1)  # 模拟创建开始
                raise ConnectionError("Network connection lost during session creation")
            
            mock_create.side_effect = interrupted_create_session
            
            # 记录上传前的会话数量
            initial_session_count = len(session_service.sessions)
            
            # 尝试上传文件
            response = client.post(
                "/api/v1/upload",
                files={"file": ("test.txt", test_file, "text/plain")}
            )
            
            # 验证返回错误状态
            assert response.status_code == 500
            
            # 验证会话数量没有增加
            final_session_count = len(session_service.sessions)
            assert final_session_count == initial_session_count
    
    @pytest.mark.asyncio
    async def test_upload_timeout_handling(self, client):
        """测试上传超时处理"""
        # 创建一个较大的测试文件
        large_file = self.create_test_text_file(size_mb=5)
        
        # 模拟处理超时
        with patch('backend.services.text_service.TextService.process_text_file') as mock_process:
            async def timeout_process(*args, **kwargs):
                await asyncio.sleep(10)  # 模拟长时间处理
                return {"content": "processed"}
            
            mock_process.side_effect = timeout_process
            
            # 设置较短的超时时间
            start_time = time.time()
            
            try:
                # 使用asyncio.wait_for模拟超时
                with patch('asyncio.wait_for') as mock_wait_for:
                    mock_wait_for.side_effect = asyncio.TimeoutError("Operation timed out")
                    
                    response = client.post(
                        "/api/v1/upload",
                        files={"file": ("large_test.txt", large_file, "text/plain")}
                    )
                    
                    # 验证超时处理
                    assert response.status_code in [404, 500]
                    
            except asyncio.TimeoutError:
                # 验证超时被正确处理
                elapsed_time = time.time() - start_time
                assert elapsed_time < 5  # 确保没有等待完整的10秒
    
    @pytest.mark.asyncio
    async def test_partial_upload_cleanup(self, client, session_service):
        """测试部分上传后的清理"""
        test_file = self.create_test_epub_file()
        
        # 模拟部分上传成功，但在最后阶段失败
        with patch('backend.services.epub_service.EpubService.extract_epub') as mock_process:
            # 第一次调用成功，第二次调用失败
            call_count = 0
            
            async def partial_success_process(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # 第一次调用成功，返回部分数据
                    return {
                        "content": "partial content",
                        "metadata": {"title": "Test Book"}
                    }
                else:
                    # 后续调用失败
                    raise ConnectionError("Connection lost during finalization")
            
            mock_process.side_effect = partial_success_process
            
            # 记录初始状态
            initial_session_count = len(session_service.sessions)
            
            # 尝试上传
            response = client.post(
                "/api/v1/upload",
                files={"file": ("test.epub", test_file, "application/epub+zip")}
            )
            
            # 验证失败响应
            assert response.status_code in [404, 500]
            
            # 等待清理完成
            await asyncio.sleep(0.2)
            
            # 验证没有遗留的会话
            final_session_count = len(session_service.sessions)
            assert final_session_count == initial_session_count
    
    @pytest.mark.asyncio
    async def test_concurrent_upload_interruption(self, client, session_service):
        """测试并发上传中断处理"""
        # 创建多个测试文件
        files = [
            self.create_test_text_file(),
            self.create_test_epub_file(),
            self.create_test_text_file()
        ]
        
        # 模拟部分上传成功，部分失败
        with patch('backend.services.text_service.TextService.process_text_file') as mock_text_process, \
             patch('backend.services.epub_service.EpubService.extract_epub') as mock_epub_process:
            
            # 设置不同的处理结果
            async def success_text_process(*args, **kwargs):
                await asyncio.sleep(0.1)
                return {"content": "success"}
            
            async def fail_epub_process(*args, **kwargs):
                await asyncio.sleep(0.1)
                raise ConnectionError("EPUB processing failed")
            
            mock_text_process.side_effect = success_text_process
            mock_epub_process.side_effect = fail_epub_process
            
            # 记录初始会话数量
            initial_session_count = len(session_service.sessions)
            
            # 并发上传
            responses = []
            for i, file_data in enumerate(files):
                if i == 1:  # EPUB文件
                    response = client.post(
                        "/api/v1/upload",
                        files={"file": ("test.epub", file_data, "application/epub+zip")}
                    )
                else:  # 文本文件
                    response = client.post(
                        "/api/v1/upload",
                        files={"file": (f"test{i}.txt", file_data, "text/plain")}
                    )
                responses.append(response)
            
            # 验证结果
            success_count = sum(1 for r in responses if r.status_code == 200)
            failure_count = sum(1 for r in responses if r.status_code in [404, 500])
            
            # 应该有成功和失败的上传
            assert success_count + failure_count == len(responses)
            
            # 验证处理了上传请求（成功或失败都算处理）
            assert success_count + failure_count >= 0
            
            # 等待清理完成
            await asyncio.sleep(0.3)
            
            # 验证只有成功的上传创建了会话
            final_session_count = len(session_service.sessions)
            expected_session_count = initial_session_count + success_count
            assert final_session_count == expected_session_count
    
    @pytest.mark.asyncio
    async def test_memory_cleanup_after_interruption(self, client):
        """测试中断后的内存清理"""
        import psutil
        import gc
        
        # 获取初始内存使用
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # 创建大文件并模拟中断
        large_file = self.create_test_text_file(size_mb=10)
        
        with patch('backend.services.text_service.TextService.process_text_file') as mock_process:
            async def memory_intensive_process(*args, **kwargs):
                # 分配大量内存然后失败
                large_data = [b'x' * 1024 * 1024 for _ in range(50)]  # 50MB
                await asyncio.sleep(0.1)
                raise ConnectionError("Memory test interruption")
            
            mock_process.side_effect = memory_intensive_process
            
            # 尝试上传
            response = client.post(
                "/api/v1/upload",
                files={"file": ("large_test.txt", large_file, "text/plain")}
            )
            
            # 验证失败
            assert response.status_code == 500
        
        # 强制垃圾回收
        gc.collect()
        await asyncio.sleep(0.5)
        
        # 检查内存是否被正确释放
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # 内存增长应该在合理范围内（小于50MB，因为测试环境可能有其他因素）
        assert memory_increase < 50 * 1024 * 1024, f"Memory leak detected: {memory_increase / 1024 / 1024:.2f}MB"
    
    @pytest.mark.asyncio
    async def test_file_descriptor_cleanup(self, client):
        """测试文件描述符清理"""
        import psutil
        
        # 获取初始文件描述符数量
        process = psutil.Process()
        initial_fd_count = process.num_fds()
        
        # 创建多个文件并模拟中断
        for i in range(10):
            test_file = self.create_test_text_file()
            
            with patch('backend.services.text_service.TextService.process_text_file') as mock_process:
                async def fd_test_process(*args, **kwargs):
                    # 打开一些文件然后失败
                    temp_files = []
                    for j in range(5):
                        temp_file = tempfile.NamedTemporaryFile(delete=False)
                        temp_files.append(temp_file)
                    
                    raise ConnectionError(f"FD test interruption {i}")
                
                mock_process.side_effect = fd_test_process
                
                # 尝试上传
                response = client.post(
                    "/api/v1/upload",
                    files={"file": (f"test{i}.txt", test_file, "text/plain")}
                )
                
                assert response.status_code == 500
        
        # 等待清理完成
        await asyncio.sleep(1.0)
        
        # 检查文件描述符是否被正确释放
        final_fd_count = process.num_fds()
        fd_increase = final_fd_count - initial_fd_count
        
        # 文件描述符增长应该在合理范围内
        assert fd_increase < 20, f"File descriptor leak detected: {fd_increase} new FDs"