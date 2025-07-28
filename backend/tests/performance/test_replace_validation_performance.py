import pytest
import pytest_asyncio
import asyncio
import time
import psutil
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
from unittest.mock import patch

from backend.services.replace_service import ReplaceService
from backend.models.schemas import RuleValidationResult


class TestReplaceValidationPerformance:
    """规则验证性能测试 - BE-03任务补充测试用例"""
    
    @pytest_asyncio.fixture
    async def service(self):
        """创建 ReplaceService 实例"""
        service = ReplaceService()
        await service._initialize()
        yield service
        await service.cleanup()
    
    def get_memory_usage(self) -> int:
        """获取当前内存使用量（字节）"""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss
    
    def get_cpu_usage(self) -> float:
        """获取当前CPU使用率"""
        return psutil.cpu_percent(interval=0.1)
    
    # 基准性能测试
    @pytest.mark.asyncio
    async def test_validation_baseline_performance(self, service):
        """测试基准验证性能"""
        # 标准规则集
        standard_rules = "\n".join([
            f"pattern_{i} -> replacement_{i} | Standard rule {i}"
            for i in range(100)
        ])
        
        # 执行多次测试获取平均性能
        times = []
        for _ in range(5):
            start_time = time.time()
            result = await service.validate_rules(standard_rules)
            end_time = time.time()
            
            times.append(end_time - start_time)
            assert isinstance(result, RuleValidationResult)
            assert result.is_valid is True
        
        # 计算平均时间
        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)
        
        # 性能基准：100条规则应在2秒内完成
        assert avg_time < 2.0, f"Average validation time too slow: {avg_time}s"
        assert max_time < 3.0, f"Maximum validation time too slow: {max_time}s"
        
        print(f"Baseline performance - Avg: {avg_time:.3f}s, Min: {min_time:.3f}s, Max: {max_time:.3f}s")
    
    @pytest.mark.asyncio
    async def test_validation_scalability_performance(self, service):
        """测试验证可扩展性性能"""
        # 测试不同规模的规则集
        scale_tests = [
            (10, 0.1),      # 10条规则，0.1秒内
            (100, 1.0),     # 100条规则，1秒内
            (500, 3.0),     # 500条规则，3秒内
            (1000, 8.0),    # 1000条规则，8秒内
            (2000, 20.0),   # 2000条规则，20秒内
        ]
        
        performance_results = []
        
        for rule_count, max_time in scale_tests:
            rules = "\n".join([
                f"scale_pattern_{i} -> scale_replacement_{i} | Scale test {i}"
                for i in range(rule_count)
            ])
            
            start_time = time.time()
            result = await service.validate_rules(rules)
            end_time = time.time()
            
            processing_time = end_time - start_time
            performance_results.append((rule_count, processing_time))
            
            assert isinstance(result, RuleValidationResult)
            assert processing_time < max_time, f"{rule_count} rules took {processing_time}s > {max_time}s"
            
            print(f"Scale test - {rule_count} rules: {processing_time:.3f}s")
        
        # 验证性能随规模线性增长（不应超过O(n²)）
        for i in range(1, len(performance_results)):
            prev_count, prev_time = performance_results[i-1]
            curr_count, curr_time = performance_results[i]
            
            # 时间增长比例不应超过规模增长比例的平方
            scale_ratio = curr_count / prev_count
            time_ratio = curr_time / prev_time if prev_time > 0 else 1
            
            assert time_ratio <= scale_ratio ** 1.5, f"Performance degradation detected: {time_ratio} > {scale_ratio}^1.5"
    
    # 内存使用性能测试
    @pytest.mark.asyncio
    async def test_validation_memory_performance(self, service):
        """测试验证内存使用性能"""
        initial_memory = self.get_memory_usage()
        
        # 测试大规模规则的内存使用
        large_rules = "\n".join([
            f"memory_pattern_{i} -> memory_replacement_{i} | Memory test {i}"
            for i in range(5000)
        ])
        
        # 执行验证
        start_time = time.time()
        result = await service.validate_rules(large_rules)
        end_time = time.time()
        
        peak_memory = self.get_memory_usage()
        memory_increase = peak_memory - initial_memory
        
        assert isinstance(result, RuleValidationResult)
        
        # 内存使用不应超过50MB
        assert memory_increase < 50 * 1024 * 1024, f"Memory usage too high: {memory_increase} bytes"
        
        # 处理时间应合理
        processing_time = end_time - start_time
        assert processing_time < 30, f"Processing time too long: {processing_time}s"
        
        print(f"Memory performance - Used: {memory_increase / 1024 / 1024:.2f}MB, Time: {processing_time:.3f}s")
    
    @pytest.mark.asyncio
    async def test_validation_memory_leak_detection(self, service):
        """测试验证内存泄漏检测"""
        initial_memory = self.get_memory_usage()
        
        # 执行多轮验证
        for round_num in range(10):
            rules = "\n".join([
                f"leak_test_{round_num}_{i} -> replacement_{round_num}_{i} | Leak test {round_num}-{i}"
                for i in range(100)
            ])
            
            result = await service.validate_rules(rules)
            assert isinstance(result, RuleValidationResult)
            
            # 每5轮检查一次内存
            if round_num % 5 == 4:
                current_memory = self.get_memory_usage()
                memory_increase = current_memory - initial_memory
                
                # 内存增长不应超过20MB
                assert memory_increase < 20 * 1024 * 1024, f"Memory leak detected at round {round_num}: {memory_increase} bytes"
        
        final_memory = self.get_memory_usage()
        total_increase = final_memory - initial_memory
        
        print(f"Memory leak test - Total increase: {total_increase / 1024 / 1024:.2f}MB")
    
    # 并发性能测试
    @pytest.mark.asyncio
    async def test_validation_concurrent_performance(self, service):
        """测试并发验证性能"""
        # 创建多个不同的规则集
        rule_sets = []
        for i in range(10):
            rules = "\n".join([
                f"concurrent_{i}_{j} -> replacement_{i}_{j} | Concurrent test {i}-{j}"
                for j in range(50)
            ])
            rule_sets.append(rules)
        
        # 并发执行验证
        start_time = time.time()
        
        tasks = [service.validate_rules(rules) for rules in rule_sets]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        concurrent_time = end_time - start_time
        
        # 验证所有结果
        for result in results:
            assert isinstance(result, RuleValidationResult)
            assert result.is_valid is True
        
        # 并发执行时间应该比串行执行快
        # 估算串行时间（基于单个验证的平均时间）
        single_validation_time = 0.1  # 假设单个验证需要0.1秒
        estimated_serial_time = len(rule_sets) * single_validation_time
        
        # 并发执行应该有显著的性能提升
        assert concurrent_time < estimated_serial_time * 0.8, f"Concurrent performance not optimal: {concurrent_time}s vs estimated {estimated_serial_time}s"
        
        print(f"Concurrent performance - {len(rule_sets)} tasks in {concurrent_time:.3f}s")
    
    @pytest.mark.asyncio
    async def test_validation_thread_safety_performance(self, service):
        """测试线程安全性能"""
        import threading
        import queue
        
        results_queue = queue.Queue()
        errors_queue = queue.Queue()
        
        def validation_worker(worker_id: int):
            """验证工作线程"""
            try:
                # 创建异步事件循环
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                rules = "\n".join([
                    f"thread_{worker_id}_{i} -> replacement_{worker_id}_{i} | Thread test {worker_id}-{i}"
                    for i in range(20)
                ])
                
                start_time = time.time()
                result = loop.run_until_complete(service.validate_rules(rules))
                end_time = time.time()
                
                results_queue.put((worker_id, end_time - start_time, result))
                
            except Exception as e:
                errors_queue.put((worker_id, str(e)))
            finally:
                loop.close()
        
        # 创建多个线程
        threads = []
        thread_count = 5
        
        start_time = time.time()
        
        for i in range(thread_count):
            thread = threading.Thread(target=validation_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join(timeout=30)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 检查错误
        errors = []
        while not errors_queue.empty():
            errors.append(errors_queue.get())
        
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        
        # 检查结果
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())
        
        assert len(results) == thread_count, f"Expected {thread_count} results, got {len(results)}"
        
        # 验证所有结果
        for worker_id, processing_time, result in results:
            assert isinstance(result, RuleValidationResult)
            assert result.is_valid is True
            assert processing_time < 5.0, f"Worker {worker_id} took too long: {processing_time}s"
        
        print(f"Thread safety performance - {thread_count} threads in {total_time:.3f}s")
    
    # 正则表达式性能测试
    @pytest.mark.asyncio
    async def test_validation_regex_performance(self, service):
        """测试正则表达式验证性能"""
        # 创建包含复杂正则表达式的规则
        complex_regex_rules = [
            r"\d{4}-\d{2}-\d{2} -> [DATE] | Date pattern | regex",
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,} -> [EMAIL] | Email pattern | regex",
            r"https?://[\w\.-]+\.[a-zA-Z]{2,}[\w\.-]*/?[\w\.-]*\??[\w=&\.-]* -> [URL] | URL pattern | regex",
            r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b -> [IP] | IP address pattern | regex",
            r"\b[A-Z]{2,}\b -> [ACRONYM] | Acronym pattern | regex",
        ]
        
        # 重复规则以增加复杂度
        all_rules = []
        for _ in range(100):  # 每个复杂正则重复100次
            all_rules.extend(complex_regex_rules)
        
        content = "\n".join(all_rules)
        
        start_time = time.time()
        result = await service.validate_rules(content)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        assert isinstance(result, RuleValidationResult)
        
        # 复杂正则表达式验证应在合理时间内完成
        assert processing_time < 15.0, f"Regex validation too slow: {processing_time}s"
        
        print(f"Regex performance - {len(all_rules)} complex regex rules in {processing_time:.3f}s")
    
    # 边界条件性能测试
    @pytest.mark.asyncio
    async def test_validation_boundary_performance(self, service):
        """测试边界条件性能"""
        boundary_tests = [
            # 空规则文件
            ("", "Empty file"),
            # 只有注释
            ("# Only comments\n# No actual rules\n", "Comments only"),
            # 单个超长规则
            ("x" * 10000 + " -> " + "y" * 10000 + " | Very long rule", "Single long rule"),
            # 大量空行
            ("\n" * 1000 + "test -> replacement | Rule with many empty lines", "Many empty lines"),
            # 复杂Unicode
            ("\n".join([f"测试{i} -> 替换{i} | Unicode test {i}" for i in range(100)]), "Unicode rules"),
        ]
        
        for content, description in boundary_tests:
            start_time = time.time()
            result = await service.validate_rules(content)
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            assert isinstance(result, RuleValidationResult)
            assert processing_time < 5.0, f"{description} took too long: {processing_time}s"
            
            print(f"Boundary test '{description}': {processing_time:.3f}s")
    
    # 资源限制性能测试
    @pytest.mark.asyncio
    async def test_validation_resource_limits_performance(self, service):
        """测试资源限制下的性能"""
        # 模拟低内存环境
        with patch('psutil.virtual_memory') as mock_memory:
            # 模拟可用内存较少的情况
            mock_memory.return_value.available = 100 * 1024 * 1024  # 100MB可用内存
            
            # 创建中等规模的规则集
            rules = "\n".join([
                f"resource_limit_{i} -> replacement_{i} | Resource limit test {i}"
                for i in range(500)
            ])
            
            start_time = time.time()
            result = await service.validate_rules(rules)
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            assert isinstance(result, RuleValidationResult)
            # 在资源受限环境下仍应在合理时间内完成
            assert processing_time < 10.0, f"Resource limited validation too slow: {processing_time}s"
    
    # 性能回归测试
    @pytest.mark.asyncio
    async def test_validation_performance_regression(self, service):
        """测试性能回归"""
        # 标准测试用例
        standard_test = "\n".join([
            f"regression_test_{i} -> replacement_{i} | Regression test {i}"
            for i in range(200)
        ])
        
        # 执行多次测试
        times = []
        for iteration in range(10):
            start_time = time.time()
            result = await service.validate_rules(standard_test)
            end_time = time.time()
            
            times.append(end_time - start_time)
            assert isinstance(result, RuleValidationResult)
            assert result.is_valid is True
        
        # 计算统计信息
        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)
        std_dev = (sum((t - avg_time) ** 2 for t in times) / len(times)) ** 0.5
        
        # 性能应该稳定（标准差不应过大）
        assert std_dev < avg_time * 0.3, f"Performance unstable: std_dev {std_dev} > 30% of avg {avg_time}"
        
        # 最大时间不应超过平均时间的2倍
        assert max_time < avg_time * 2, f"Performance spike detected: max {max_time} > 2x avg {avg_time}"
        
        print(f"Performance regression test - Avg: {avg_time:.3f}s, StdDev: {std_dev:.3f}s, Range: {min_time:.3f}s - {max_time:.3f}s")