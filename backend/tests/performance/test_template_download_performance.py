"""规则模板下载性能测试

BE-02: 规则模板下载功能的性能测试用例
"""

import time
import statistics
import pytest
import psutil
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient
from typing import List, Dict, Any


class TestTemplateDownloadPerformance:
    """规则模板下载性能测试类"""
    
    def test_single_download_performance(self, client: TestClient):
        """测试单次下载性能"""
        # 预热
        client.get("/api/v1/batch-replace/template")
        
        # 测试多次单独下载
        response_times = []
        content_sizes = []
        
        for _ in range(10):
            start_time = time.time()
            response = client.get("/api/v1/batch-replace/template")
            end_time = time.time()
            
            assert response.status_code == 200
            
            response_time = end_time - start_time
            content_size = len(response.content)
            
            response_times.append(response_time)
            content_sizes.append(content_size)
        
        # 性能指标验证
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)
        std_response_time = statistics.stdev(response_times) if len(response_times) > 1 else 0
        
        # 验证性能要求
        assert avg_response_time < 0.5, f"平均响应时间过长: {avg_response_time:.3f}s"
        assert max_response_time < 1.0, f"最大响应时间过长: {max_response_time:.3f}s"
        assert std_response_time < 0.2, f"响应时间波动过大: {std_response_time:.3f}s"
        
        # 验证内容大小一致性
        assert len(set(content_sizes)) == 1, "内容大小不一致"
        
        print(f"单次下载性能: 平均 {avg_response_time:.3f}s, 最大 {max_response_time:.3f}s, 最小 {min_response_time:.3f}s")
    
    def test_concurrent_download_performance(self, client: TestClient):
        """测试并发下载性能"""
        def download_with_metrics():
            """带性能指标的下载"""
            start_time = time.time()
            response = client.get("/api/v1/batch-replace/template")
            end_time = time.time()
            
            return {
                'status_code': response.status_code,
                'response_time': end_time - start_time,
                'content_size': len(response.content),
                'timestamp': start_time
            }
        
        # 测试不同并发级别
        concurrent_levels = [5, 10, 20, 30]
        
        for concurrent_count in concurrent_levels:
            print(f"\n测试并发级别: {concurrent_count}")
            
            start_time = time.time()
            
            # 执行并发请求
            with ThreadPoolExecutor(max_workers=concurrent_count) as executor:
                futures = [executor.submit(download_with_metrics) for _ in range(concurrent_count)]
                results = [future.result() for future in as_completed(futures)]
            
            total_time = time.time() - start_time
            
            # 分析结果
            successful_results = [r for r in results if r['status_code'] == 200]
            success_rate = len(successful_results) / concurrent_count
            
            if successful_results:
                response_times = [r['response_time'] for r in successful_results]
                avg_response_time = statistics.mean(response_times)
                max_response_time = max(response_times)
                throughput = len(successful_results) / total_time  # 请求/秒
                
                # 性能验证
                assert success_rate >= 0.95, f"成功率过低: {success_rate:.2%}"
                assert avg_response_time < 2.0, f"平均响应时间过长: {avg_response_time:.3f}s"
                assert throughput > 2.0, f"吞吐量过低: {throughput:.2f} req/s"
                
                print(f"  成功率: {success_rate:.2%}")
                print(f"  平均响应时间: {avg_response_time:.3f}s")
                print(f"  最大响应时间: {max_response_time:.3f}s")
                print(f"  吞吐量: {throughput:.2f} req/s")
                print(f"  总耗时: {total_time:.3f}s")
    
    def test_memory_usage_performance(self, client: TestClient):
        """测试内存使用性能"""
        process = psutil.Process(os.getpid())
        
        # 记录初始内存
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        def download_and_measure_memory():
            """下载并测量内存"""
            response = client.get("/api/v1/batch-replace/template")
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            return {
                'status_code': response.status_code,
                'content_size': len(response.content),
                'memory_usage': current_memory
            }
        
        # 执行多次下载
        memory_measurements = []
        
        for i in range(50):
            result = download_and_measure_memory()
            assert result['status_code'] == 200
            memory_measurements.append(result['memory_usage'])
            
            # 每10次检查一次内存增长
            if (i + 1) % 10 == 0:
                current_memory_increase = result['memory_usage'] - initial_memory
                print(f"第{i+1}次下载后内存增长: {current_memory_increase:.2f}MB")
        
        # 分析内存使用
        final_memory = memory_measurements[-1]
        max_memory = max(memory_measurements)
        memory_increase = final_memory - initial_memory
        max_memory_increase = max_memory - initial_memory
        
        # 内存使用验证
        assert memory_increase < 50, f"最终内存增长过多: {memory_increase:.2f}MB"
        assert max_memory_increase < 100, f"峰值内存增长过多: {max_memory_increase:.2f}MB"
        
        print(f"内存使用分析:")
        print(f"  初始内存: {initial_memory:.2f}MB")
        print(f"  最终内存: {final_memory:.2f}MB")
        print(f"  峰值内存: {max_memory:.2f}MB")
        print(f"  内存增长: {memory_increase:.2f}MB")
        print(f"  峰值增长: {max_memory_increase:.2f}MB")
    
    def test_sustained_load_performance(self, client: TestClient):
        """测试持续负载性能"""
        def download_with_timing():
            """带计时的下载"""
            start_time = time.time()
            response = client.get("/api/v1/batch-replace/template")
            end_time = time.time()
            
            return {
                'status_code': response.status_code,
                'response_time': end_time - start_time,
                'timestamp': start_time
            }
        
        # 持续负载测试：5分钟内每秒发送请求
        test_duration = 60  # 60秒（缩短测试时间）
        request_interval = 0.5  # 每0.5秒一个请求
        
        results = []
        start_time = time.time()
        
        while time.time() - start_time < test_duration:
            result = download_with_timing()
            results.append(result)
            
            # 等待下一个请求间隔
            time.sleep(request_interval)
        
        # 分析持续负载性能
        successful_results = [r for r in results if r['status_code'] == 200]
        success_rate = len(successful_results) / len(results)
        
        if successful_results:
            response_times = [r['response_time'] for r in successful_results]
            avg_response_time = statistics.mean(response_times)
            max_response_time = max(response_times)
            
            # 计算性能趋势
            first_half = response_times[:len(response_times)//2]
            second_half = response_times[len(response_times)//2:]
            
            first_half_avg = statistics.mean(first_half) if first_half else 0
            second_half_avg = statistics.mean(second_half) if second_half else 0
            
            performance_degradation = (second_half_avg - first_half_avg) / first_half_avg if first_half_avg > 0 else 0
            
            # 性能验证
            assert success_rate >= 0.95, f"持续负载成功率过低: {success_rate:.2%}"
            assert avg_response_time < 1.0, f"持续负载平均响应时间过长: {avg_response_time:.3f}s"
            assert performance_degradation < 0.5, f"性能退化过大: {performance_degradation:.2%}"
            
            print(f"持续负载测试结果:")
            print(f"  测试时长: {test_duration}s")
            print(f"  总请求数: {len(results)}")
            print(f"  成功率: {success_rate:.2%}")
            print(f"  平均响应时间: {avg_response_time:.3f}s")
            print(f"  最大响应时间: {max_response_time:.3f}s")
            print(f"  前半段平均: {first_half_avg:.3f}s")
            print(f"  后半段平均: {second_half_avg:.3f}s")
            print(f"  性能变化: {performance_degradation:.2%}")
    
    def test_cache_performance(self, client: TestClient):
        """测试缓存性能"""
        # 第一次请求（冷启动）
        start_time = time.time()
        response1 = client.get("/api/v1/batch-replace/template")
        cold_start_time = time.time() - start_time
        
        assert response1.status_code == 200
        
        # 后续请求（可能有缓存）
        warm_times = []
        for _ in range(10):
            start_time = time.time()
            response = client.get("/api/v1/batch-replace/template")
            warm_time = time.time() - start_time
            
            assert response.status_code == 200
            warm_times.append(warm_time)
        
        avg_warm_time = statistics.mean(warm_times)
        
        # 验证缓存效果（如果有的话）
        print(f"缓存性能分析:")
        print(f"  冷启动时间: {cold_start_time:.3f}s")
        print(f"  平均热启动时间: {avg_warm_time:.3f}s")
        
        # 基本性能要求
        assert avg_warm_time < 1.0, f"热启动时间过长: {avg_warm_time:.3f}s"
    
    def test_content_generation_performance(self, client: TestClient):
        """测试内容生成性能"""
        from backend.api.replace import _generate_template_content
        
        # 测试模板生成函数性能
        generation_times = []
        
        for _ in range(100):
            start_time = time.time()
            content = _generate_template_content()
            end_time = time.time()
            
            generation_time = end_time - start_time
            generation_times.append(generation_time)
            
            # 验证内容正确性
            assert len(content) > 0
            assert "AetherFolio" in content
        
        # 分析生成性能
        avg_generation_time = statistics.mean(generation_times)
        max_generation_time = max(generation_times)
        
        # 性能验证
        assert avg_generation_time < 0.01, f"平均生成时间过长: {avg_generation_time:.4f}s"
        assert max_generation_time < 0.05, f"最大生成时间过长: {max_generation_time:.4f}s"
        
        print(f"内容生成性能:")
        print(f"  平均生成时间: {avg_generation_time:.4f}s")
        print(f"  最大生成时间: {max_generation_time:.4f}s")
        print(f"  生成100次总耗时: {sum(generation_times):.3f}s")
    
    def test_large_scale_concurrent_performance(self, client: TestClient):
        """测试大规模并发性能"""
        def download_with_detailed_metrics():
            """带详细指标的下载"""
            start_time = time.time()
            try:
                response = client.get("/api/v1/batch-replace/template")
                end_time = time.time()
                
                return {
                    'success': True,
                    'status_code': response.status_code,
                    'response_time': end_time - start_time,
                    'content_size': len(response.content),
                    'error': None
                }
            except Exception as e:
                end_time = time.time()
                return {
                    'success': False,
                    'status_code': None,
                    'response_time': end_time - start_time,
                    'content_size': 0,
                    'error': str(e)
                }
        
        # 大规模并发测试
        concurrent_count = 100
        
        print(f"开始大规模并发测试: {concurrent_count}个并发请求")
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(download_with_detailed_metrics) for _ in range(concurrent_count)]
            results = [future.result() for future in as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # 分析结果
        successful_results = [r for r in results if r['success']]
        failed_results = [r for r in results if not r['success']]
        
        success_rate = len(successful_results) / concurrent_count
        
        if successful_results:
            response_times = [r['response_time'] for r in successful_results]
            avg_response_time = statistics.mean(response_times)
            p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)]
            throughput = len(successful_results) / total_time
            
            # 性能验证
            assert success_rate >= 0.90, f"大规模并发成功率过低: {success_rate:.2%}"
            assert avg_response_time < 5.0, f"大规模并发平均响应时间过长: {avg_response_time:.3f}s"
            assert p95_response_time < 10.0, f"大规模并发P95响应时间过长: {p95_response_time:.3f}s"
            
            print(f"大规模并发测试结果:")
            print(f"  并发数: {concurrent_count}")
            print(f"  成功率: {success_rate:.2%}")
            print(f"  失败数: {len(failed_results)}")
            print(f"  平均响应时间: {avg_response_time:.3f}s")
            print(f"  P95响应时间: {p95_response_time:.3f}s")
            print(f"  吞吐量: {throughput:.2f} req/s")
            print(f"  总耗时: {total_time:.3f}s")
            
            # 打印失败原因（如果有）
            if failed_results:
                error_types = {}
                for result in failed_results[:5]:  # 只显示前5个错误
                    error = result['error']
                    error_types[error] = error_types.get(error, 0) + 1
                
                print(f"  主要错误类型:")
                for error, count in error_types.items():
                    print(f"    {error}: {count}次")