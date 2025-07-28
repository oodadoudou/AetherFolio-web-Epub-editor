"""规则模板下载并发测试

BE-02: 规则模板下载功能的并发测试用例
"""

import asyncio
import pytest
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient
from httpx import AsyncClient


class TestTemplateDownloadConcurrent:
    """规则模板下载并发测试类"""
    
    def test_concurrent_template_download_threads(self, client: TestClient):
        """测试多线程并发下载模板"""
        def download_template():
            """单次下载模板"""
            response = client.get("/api/v1/batch-replace/template")
            return {
                'status_code': response.status_code,
                'content_length': len(response.content),
                'headers': dict(response.headers),
                'timestamp': time.time()
            }
        
        # 并发数量
        concurrent_count = 10
        results = []
        
        # 使用线程池执行并发请求
        with ThreadPoolExecutor(max_workers=concurrent_count) as executor:
            futures = [executor.submit(download_template) for _ in range(concurrent_count)]
            
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
        
        # 验证所有请求都成功
        assert len(results) == concurrent_count
        for result in results:
            assert result['status_code'] == 200
            assert result['content_length'] > 0
            assert 'text/plain' in result['headers']['content-type']
            assert 'charset=utf-8' in result['headers']['content-type']
    
    def test_concurrent_template_download_stress(self, client: TestClient):
        """测试高并发压力下载"""
        def download_template_with_timing():
            """带计时的下载模板"""
            start_time = time.time()
            response = client.get("/api/v1/batch-replace/template")
            end_time = time.time()
            
            return {
                'status_code': response.status_code,
                'response_time': end_time - start_time,
                'content_valid': "AetherFolio 批量替换规则模板" in response.content.decode('utf-8')
            }
        
        # 高并发数量
        concurrent_count = 50
        results = []
        
        start_time = time.time()
        
        # 使用线程池执行高并发请求
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(download_template_with_timing) for _ in range(concurrent_count)]
            
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
        
        total_time = time.time() - start_time
        
        # 验证结果
        assert len(results) == concurrent_count
        
        # 统计成功率
        success_count = sum(1 for r in results if r['status_code'] == 200)
        success_rate = success_count / concurrent_count
        
        # 成功率应该大于95%
        assert success_rate >= 0.95, f"成功率过低: {success_rate:.2%}"
        
        # 验证内容正确性
        valid_content_count = sum(1 for r in results if r['content_valid'])
        content_validity_rate = valid_content_count / success_count if success_count > 0 else 0
        assert content_validity_rate >= 0.95, f"内容正确率过低: {content_validity_rate:.2%}"
        
        # 验证响应时间
        response_times = [r['response_time'] for r in results if r['status_code'] == 200]
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            
            # 平均响应时间应该小于2秒
            assert avg_response_time < 2.0, f"平均响应时间过长: {avg_response_time:.2f}s"
            # 最大响应时间应该小于5秒
            assert max_response_time < 5.0, f"最大响应时间过长: {max_response_time:.2f}s"
        
        print(f"并发测试完成: {concurrent_count}个请求, 总耗时: {total_time:.2f}s, 成功率: {success_rate:.2%}")
    
    def test_concurrent_template_download_memory_usage(self, client: TestClient):
        """测试并发下载时的内存使用情况"""
        import psutil
        import os
        
        # 获取当前进程
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        def download_template():
            """下载模板并返回内容大小"""
            response = client.get("/api/v1/batch-replace/template")
            return len(response.content)
        
        # 并发下载
        concurrent_count = 20
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(download_template) for _ in range(concurrent_count)]
            content_sizes = [future.result() for future in as_completed(futures)]
        
        # 检查内存使用
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # 验证所有下载都成功
        assert len(content_sizes) == concurrent_count
        assert all(size > 0 for size in content_sizes)
        
        # 内存增长应该在合理范围内（小于100MB）
        assert memory_increase < 100, f"内存增长过多: {memory_increase:.2f}MB"
        
        print(f"内存使用: 初始 {initial_memory:.2f}MB, 最终 {final_memory:.2f}MB, 增长 {memory_increase:.2f}MB")


@pytest.mark.asyncio
class TestTemplateDownloadConcurrentAsync:
    """异步规则模板下载并发测试类"""
    
    async def test_async_concurrent_template_download(self, async_client: AsyncClient):
        """测试异步并发下载模板"""
        async def download_template():
            """异步下载模板"""
            response = await async_client.get("/api/v1/batch-replace/template")
            return {
                'status_code': response.status_code,
                'content_length': len(response.content),
                'content_type': response.headers.get('content-type', '')
            }
        
        # 创建并发任务
        concurrent_count = 15
        tasks = [download_template() for _ in range(concurrent_count)]
        
        # 执行并发请求
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 验证结果
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == concurrent_count
        
        for result in successful_results:
            assert result['status_code'] == 200
            assert result['content_length'] > 0
            assert 'text/plain' in result['content_type']
    
    async def test_async_concurrent_template_download_with_delay(self, async_client: AsyncClient):
        """测试带延迟的异步并发下载"""
        async def download_template_with_delay(delay: float):
            """带延迟的异步下载模板"""
            await asyncio.sleep(delay)
            start_time = time.time()
            response = await async_client.get("/api/v1/batch-replace/template")
            end_time = time.time()
            
            return {
                'delay': delay,
                'status_code': response.status_code,
                'response_time': end_time - start_time,
                'content_valid': "AetherFolio" in response.text
            }
        
        # 创建不同延迟的任务
        delays = [0.1 * i for i in range(10)]  # 0.0s 到 0.9s
        tasks = [download_template_with_delay(delay) for delay in delays]
        
        # 执行并发请求
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # 验证结果
        assert len(results) == len(delays)
        
        for result in results:
            assert result['status_code'] == 200
            assert result['content_valid'] is True
            assert result['response_time'] < 2.0  # 单个请求响应时间小于2秒
        
        # 总时间应该接近最大延迟时间（并发执行）
        max_delay = max(delays)
        assert total_time < max_delay + 2.0, f"总时间过长: {total_time:.2f}s, 预期: < {max_delay + 2.0:.2f}s"
        
        print(f"异步并发测试完成: {len(delays)}个任务, 总耗时: {total_time:.2f}s")
    
    async def test_async_concurrent_template_download_error_handling(self, async_client: AsyncClient):
        """测试异步并发下载的错误处理"""
        async def download_template_with_error_check():
            """带错误检查的异步下载模板"""
            try:
                response = await async_client.get("/api/v1/batch-replace/template")
                return {
                    'success': True,
                    'status_code': response.status_code,
                    'error': None
                }
            except Exception as e:
                return {
                    'success': False,
                    'status_code': None,
                    'error': str(e)
                }
        
        # 创建大量并发任务
        concurrent_count = 30
        tasks = [download_template_with_error_check() for _ in range(concurrent_count)]
        
        # 执行并发请求
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计结果
        successful_results = [r for r in results if isinstance(r, dict) and r.get('success', False)]
        error_results = [r for r in results if isinstance(r, dict) and not r.get('success', True)]
        exception_results = [r for r in results if isinstance(r, Exception)]
        
        # 验证大部分请求成功
        success_rate = len(successful_results) / concurrent_count
        assert success_rate >= 0.9, f"成功率过低: {success_rate:.2%}"
        
        # 记录错误信息
        if error_results or exception_results:
            print(f"错误结果: {len(error_results)}, 异常结果: {len(exception_results)}")
            for error in error_results[:3]:  # 只打印前3个错误
                print(f"错误: {error['error']}")
            for exc in exception_results[:3]:  # 只打印前3个异常
                print(f"异常: {exc}")