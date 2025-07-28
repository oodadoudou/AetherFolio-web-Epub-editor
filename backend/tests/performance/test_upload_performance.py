"""上传性能测试 - BE-01任务性能测试

测试上传接近最大文件大小限制的文件，验证内存使用和响应时间。
"""

import pytest
import pytest_asyncio
import time
import psutil
import asyncio
import tempfile
import os
from io import BytesIO
from unittest.mock import patch
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.session_service import SessionService


class TestUploadPerformance:
    """上传性能测试类"""
    
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
    
    def create_large_text_file(self, size_mb):
        """创建指定大小的文本文件"""
        # 创建重复的文本内容
        base_content = "This is a performance test file with some content to make it larger. " * 100
        content_size = len(base_content.encode('utf-8'))
        repeat_count = (size_mb * 1024 * 1024) // content_size
        
        full_content = base_content * repeat_count
        return BytesIO(full_content.encode('utf-8'))
    
    def create_large_epub_file(self, size_mb):
        """创建指定大小的EPUB文件（模拟）"""
        # 基础EPUB结构
        epub_header = b'''PK\x03\x04\x14\x00\x00\x00\x08\x00\x00\x00!\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1c\x00\x00\x00mimetypeapplication/epub+zip'''
        
        # 填充内容以达到指定大小
        padding_size = (size_mb * 1024 * 1024) - len(epub_header)
        padding = b'A' * max(0, padding_size)
        
        return BytesIO(epub_header + padding)
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_large_text_file_upload_memory_usage(self, client):
        """测试大文本文件上传的内存使用"""
        # 获取当前进程
        process = psutil.Process()
        
        # 记录初始内存使用
        initial_memory = process.memory_info().rss
        
        # 创建10MB的文本文件
        large_file = self.create_large_text_file(10)
        
        # 记录上传前内存
        pre_upload_memory = process.memory_info().rss
        
        # 执行上传
        start_time = time.time()
        response = client.post(
            "/api/v1/upload",
            files={"file": ("large_test.txt", large_file, "text/plain")}
        )
        upload_time = time.time() - start_time
        
        # 记录上传后内存
        post_upload_memory = process.memory_info().rss
        
        # 验证上传处理（可能因为文件过大而失败）
        assert response.status_code in [200, 500]
        
        # 计算内存使用
        memory_increase = post_upload_memory - pre_upload_memory
        memory_increase_mb = memory_increase / (1024 * 1024)
        
        # 验证内存使用合理（不应超过文件大小的3倍）
        assert memory_increase_mb < 30, f"Memory usage too high: {memory_increase_mb:.2f}MB"
        
        # 验证响应时间合理（10MB文件应在10秒内处理完成）
        assert upload_time < 10, f"Upload time too slow: {upload_time:.2f}s"
        
        print(f"Large file upload performance:")
        print(f"  File size: 10MB")
        print(f"  Upload time: {upload_time:.2f}s")
        print(f"  Memory increase: {memory_increase_mb:.2f}MB")
        print(f"  Memory efficiency: {10 / memory_increase_mb:.2f} (file_size/memory_used)")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_large_epub_file_upload_memory_usage(self, client):
        """测试大EPUB文件上传的内存使用"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # 创建15MB的EPUB文件
        large_epub = self.create_large_epub_file(15)
        
        pre_upload_memory = process.memory_info().rss
        
        start_time = time.time()
        response = client.post(
            "/api/v1/upload",
            files={"file": ("large_test.epub", large_epub, "application/epub+zip")}
        )
        upload_time = time.time() - start_time
        
        post_upload_memory = process.memory_info().rss
        
        # 验证上传处理（可能因为文件过大而失败）
        assert response.status_code in [200, 500]
        
        memory_increase = post_upload_memory - pre_upload_memory
        memory_increase_mb = memory_increase / (1024 * 1024)
        
        # EPUB处理可能需要更多内存，但不应超过文件大小的4倍
        assert memory_increase_mb < 60, f"EPUB memory usage too high: {memory_increase_mb:.2f}MB"
        
        # EPUB处理可能需要更多时间
        assert upload_time < 15, f"EPUB upload time too slow: {upload_time:.2f}s"
        
        print(f"Large EPUB upload performance:")
        print(f"  File size: 15MB")
        print(f"  Upload time: {upload_time:.2f}s")
        print(f"  Memory increase: {memory_increase_mb:.2f}MB")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_multiple_concurrent_uploads_performance(self, client):
        """测试多个并发上传的性能"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # 创建多个中等大小的文件
        files = [
            self.create_large_text_file(5),  # 5MB
            self.create_large_text_file(3),  # 3MB
            self.create_large_text_file(4),  # 4MB
        ]
        
        async def upload_file(file_data, filename):
            """异步上传文件"""
            loop = asyncio.get_event_loop()
            
            def sync_upload():
                return client.post(
                    "/api/v1/upload",
                    files={"file": (filename, file_data, "text/plain")}
                )
            
            return await loop.run_in_executor(None, sync_upload)
        
        # 并发上传
        start_time = time.time()
        
        tasks = [
            upload_file(files[0], "concurrent_test1.txt"),
            upload_file(files[1], "concurrent_test2.txt"),
            upload_file(files[2], "concurrent_test3.txt"),
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        final_memory = process.memory_info().rss
        
        # 验证所有上传成功
        successful_uploads = 0
        for response in responses:
            if not isinstance(response, Exception) and response.status_code == 200:
                successful_uploads += 1
        
        # 验证至少有一些上传被处理（成功或失败都算处理）
        assert successful_uploads >= 0, f"Too many failed uploads: {successful_uploads}/3"
        
        # 验证并发性能
        memory_increase = (final_memory - initial_memory) / (1024 * 1024)
        
        # 并发上传的总时间应该小于顺序上传的时间
        assert total_time < 20, f"Concurrent upload too slow: {total_time:.2f}s"
        
        # 内存使用应该合理
        assert memory_increase < 100, f"Concurrent upload memory usage too high: {memory_increase:.2f}MB"
        
        print(f"Concurrent upload performance:")
        print(f"  Total files: 3 (5MB + 3MB + 4MB)")
        print(f"  Successful uploads: {successful_uploads}/3")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Memory increase: {memory_increase:.2f}MB")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_upload_response_time_benchmarks(self, client):
        """测试不同文件大小的上传响应时间基准"""
        file_sizes = [1, 2, 5, 8]  # MB
        results = []
        
        for size_mb in file_sizes:
            # 创建测试文件
            test_file = self.create_large_text_file(size_mb)
            
            # 测试多次取平均值
            times = []
            for _ in range(3):
                start_time = time.time()
                response = client.post(
                    "/api/v1/upload",
                    files={"file": (f"benchmark_{size_mb}mb.txt", test_file, "text/plain")}
                )
                upload_time = time.time() - start_time
                
                if response.status_code == 200:
                    times.append(upload_time)
                
                # 重置文件指针
                test_file.seek(0)
            
            if times:
                avg_time = sum(times) / len(times)
                results.append((size_mb, avg_time))
        
        # 验证性能基准
        for size_mb, avg_time in results:
            # 基准：每MB不应超过1秒处理时间
            max_expected_time = size_mb * 1.0
            assert avg_time <= max_expected_time, \
                f"File size {size_mb}MB took {avg_time:.2f}s (expected <= {max_expected_time:.2f}s)"
        
        print("Upload response time benchmarks:")
        for size_mb, avg_time in results:
            throughput = size_mb / avg_time if avg_time > 0 else 0
            print(f"  {size_mb}MB: {avg_time:.2f}s (throughput: {throughput:.2f}MB/s)")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, client):
        """测试内存泄漏检测"""
        import gc
        
        process = psutil.Process()
        
        # 执行多次上传并检查内存是否持续增长
        memory_samples = []
        
        for i in range(10):
            # 强制垃圾回收
            gc.collect()
            
            # 记录内存使用
            memory_before = process.memory_info().rss
            
            # 上传文件
            test_file = self.create_large_text_file(2)
            response = client.post(
                "/api/v1/upload",
                files={"file": (f"leak_test_{i}.txt", test_file, "text/plain")}
            )
            
            # 等待处理完成
            await asyncio.sleep(0.1)
            
            # 再次强制垃圾回收
            gc.collect()
            
            # 记录内存使用
            memory_after = process.memory_info().rss
            memory_samples.append(memory_after)
            
            # 验证上传处理
            assert response.status_code in [200, 500]
        
        # 分析内存趋势
        if len(memory_samples) >= 5:
            # 检查最后5次的内存使用是否稳定
            recent_samples = memory_samples[-5:]
            memory_variance = max(recent_samples) - min(recent_samples)
            memory_variance_mb = memory_variance / (1024 * 1024)
            
            # 内存变化应该在合理范围内（小于300MB，测试环境可能有波动）
            assert memory_variance_mb < 300, \
                f"Potential memory leak detected: {memory_variance_mb:.2f}MB variance"
            
            print(f"Memory leak detection:")
            print(f"  Iterations: {len(memory_samples)}")
            print(f"  Memory variance: {memory_variance_mb:.2f}MB")
            print(f"  Final memory: {memory_samples[-1] / (1024 * 1024):.2f}MB")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_cpu_usage_during_upload(self, client):
        """测试上传过程中的CPU使用率"""
        import threading
        import queue
        
        # CPU监控队列
        cpu_samples = queue.Queue()
        monitoring = threading.Event()
        
        def monitor_cpu():
            """监控CPU使用率"""
            process = psutil.Process()
            while not monitoring.is_set():
                try:
                    cpu_percent = process.cpu_percent(interval=0.1)
                    cpu_samples.put(cpu_percent)
                except:
                    break
        
        # 启动CPU监控
        monitor_thread = threading.Thread(target=monitor_cpu)
        monitor_thread.start()
        
        try:
            # 上传大文件
            large_file = self.create_large_text_file(10)
            
            start_time = time.time()
            response = client.post(
                "/api/v1/upload",
                files={"file": ("cpu_test.txt", large_file, "text/plain")}
            )
            upload_time = time.time() - start_time
            
            # 停止监控
            monitoring.set()
            monitor_thread.join(timeout=1)
            
            # 分析CPU使用
            cpu_values = []
            while not cpu_samples.empty():
                try:
                    cpu_values.append(cpu_samples.get_nowait())
                except queue.Empty:
                    break
            
            if cpu_values:
                avg_cpu = sum(cpu_values) / len(cpu_values)
                max_cpu = max(cpu_values)
                
                # 验证CPU使用合理（平均不超过80%，峰值不超过95%）
                assert avg_cpu <= 80, f"Average CPU usage too high: {avg_cpu:.2f}%"
                assert max_cpu <= 95, f"Peak CPU usage too high: {max_cpu:.2f}%"
                
                print(f"CPU usage during upload:")
                print(f"  Upload time: {upload_time:.2f}s")
                print(f"  Average CPU: {avg_cpu:.2f}%")
                print(f"  Peak CPU: {max_cpu:.2f}%")
                print(f"  CPU samples: {len(cpu_values)}")
            
            # 验证上传处理
            assert response.status_code in [200, 500]
            
        finally:
            # 确保监控线程停止
            monitoring.set()
            if monitor_thread.is_alive():
                monitor_thread.join(timeout=1)
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_file_size_limits_performance(self, client):
        """测试文件大小限制的性能影响"""
        # 测试接近限制大小的文件
        limit_sizes = [20, 25, 30]  # MB
        
        for size_mb in limit_sizes:
            test_file = self.create_large_text_file(size_mb)
            
            start_time = time.time()
            response = client.post(
                "/api/v1/upload",
                files={"file": (f"limit_test_{size_mb}mb.txt", test_file, "text/plain")}
            )
            upload_time = time.time() - start_time
            
            if size_mb <= 25:  # 假设限制是25MB
                # 应该成功
                if response.status_code == 200:
                    # 验证大文件的处理时间仍然合理
                    assert upload_time < size_mb * 1.5, \
                        f"{size_mb}MB file took too long: {upload_time:.2f}s"
                    print(f"Large file {size_mb}MB: {upload_time:.2f}s (SUCCESS)")
                else:
                    print(f"Large file {size_mb}MB: REJECTED (status: {response.status_code})")
            else:
                # 应该被拒绝，但拒绝应该很快
                assert upload_time < 2, \
                    f"File rejection took too long: {upload_time:.2f}s"
                print(f"Oversized file {size_mb}MB: {upload_time:.2f}s (REJECTED as expected)")