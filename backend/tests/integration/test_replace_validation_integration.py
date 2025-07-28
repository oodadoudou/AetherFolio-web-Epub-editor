import pytest
import pytest_asyncio
import asyncio
import tempfile
import os
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any

from backend.services.replace_service import ReplaceService
from backend.services.session_service import SessionService
from backend.models.schemas import ReplaceRule, RuleValidationResult
from backend.models.session import Session
from backend.core.security import SecurityValidator
from backend.core.exceptions import ContentValidationError


class TestReplaceValidationIntegration:
    """规则验证集成测试 - BE-03任务补充测试用例"""
    
    @pytest_asyncio.fixture
    async def replace_service(self):
        """创建 ReplaceService 实例"""
        service = ReplaceService()
        await service._initialize()
        yield service
        await service.cleanup()
    
    @pytest_asyncio.fixture
    async def session_service(self):
        """创建 SessionService 实例"""
        service = SessionService()
        await service._initialize()
        yield service
        await service.cleanup()
    
    @pytest.fixture
    def temp_rules_file(self):
        """创建临时规则文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("""# 测试规则文件
old_text -> new_text | Basic replacement
\\d{4}-\\d{2}-\\d{2} -> [DATE] | Date replacement | regex
""")
            temp_path = f.name
        
        yield temp_path
        
        # 清理
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    # 服务间集成测试
    @pytest.mark.asyncio
    async def test_validation_with_session_integration(self, replace_service, session_service):
        """测试规则验证与会话服务的集成"""
        # 创建测试会话
        session = Session(
            session_id="test_session_123",
            epub_path="/path/to/test.epub",
            original_filename="test.epub",
            file_size=1024,
            metadata={"file_type": "epub"}
        )
        
        # 添加会话到会话服务
        await session_service.add_session(session)
        
        # 验证规则
        rules_content = """# 集成测试规则
test_pattern -> replacement | Integration test
\\w+ -> [WORD] | Word replacement | regex
"""
        
        result = await replace_service.validate_rules(rules_content)
        
        # 验证结果应该正确
        assert result.is_valid is True
        assert result.valid_rules == 2
        
        # 验证会话仍然存在
        retrieved_session = await session_service.get_session("test_session_123")
        assert retrieved_session is not None
        assert retrieved_session.session_id == "test_session_123"
    
    @pytest.mark.asyncio
    async def test_validation_with_security_validator_integration(self, replace_service):
        """测试规则验证与安全验证器的集成"""
        # 创建包含潜在安全问题的规则
        security_test_content = """# 安全测试规则
<script> -> [SCRIPT] | Script tag replacement
../../../etc/passwd -> [PATH] | Path traversal replacement
(a+)+b -> [REDOS] | ReDoS pattern | regex
"""
        
        # 验证规则
        result = await replace_service.validate_rules_detailed(security_test_content)
        
        # 应该检测到安全问题
        assert "dangerous_operations" in result
        assert len(result["dangerous_operations"]) > 0
        
        # 检查是否检测到了特定的安全问题
        security_issues = result["dangerous_operations"]
        issue_types = [issue["type"] for issue in security_issues]
        
        # 应该检测到结构性变更或其他安全问题
        assert any("structural" in issue_type or "security" in issue_type or "broad" in issue_type 
                  for issue_type in issue_types)
    
    # 文件系统集成测试
    @pytest.mark.asyncio
    async def test_validation_with_file_system_integration(self, replace_service, temp_rules_file):
        """测试规则验证与文件系统的集成"""
        # 读取临时文件内容
        with open(temp_rules_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 验证文件内容
        result = await replace_service.validate_rules(content)
        
        assert result.is_valid is True
        assert result.valid_rules > 0
    
    @pytest.mark.asyncio
    async def test_validation_with_large_file_integration(self, replace_service):
        """测试大文件验证的集成处理"""
        # 创建大型临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            # 写入大量规则（约1MB）
            for i in range(10000):
                f.write(f"pattern_{i} -> replacement_{i} | Rule {i}\n")
            large_file_path = f.name
        
        try:
            # 读取大文件
            with open(large_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 验证大文件
            start_time = time.time()
            result = await replace_service.validate_rules(content)
            end_time = time.time()
            
            # 验证处理时间合理
            processing_time = end_time - start_time
            assert processing_time < 30, f"Large file processing took too long: {processing_time}s"
            
            # 验证结果
            assert isinstance(result, RuleValidationResult)
            assert result.total_rules == 10000
            
        finally:
            # 清理大文件
            if os.path.exists(large_file_path):
                os.unlink(large_file_path)
    
    # 并发处理集成测试
    @pytest.mark.asyncio
    async def test_concurrent_validation_integration(self, replace_service):
        """测试并发规则验证的集成处理"""
        # 创建多个不同的规则内容
        rule_contents = [
            "pattern1 -> replacement1 | Test 1",
            "pattern2 -> replacement2 | Test 2\npattern3 -> replacement3 | Test 3",
            "\\d+ -> [NUMBER] | Number replacement | regex",
            "(a|b)+ -> [LETTERS] | Letter replacement | regex",
            "# 空规则文件\n"
        ]
        
        # 并发验证所有规则
        tasks = []
        for i, content in enumerate(rule_contents):
            task = replace_service.validate_rules(content)
            tasks.append(task)
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 验证所有结果
        assert len(results) == len(rule_contents)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                pytest.fail(f"Validation {i} failed with exception: {result}")
            
            assert isinstance(result, RuleValidationResult)
    
    # 错误恢复集成测试
    @pytest.mark.asyncio
    async def test_validation_error_recovery_integration(self, replace_service):
        """测试验证错误恢复的集成处理"""
        # 测试各种错误情况的恢复
        error_scenarios = [
            # 编码错误
            "test -> replacement | Normal rule",
            # 正则表达式错误
            "[invalid_regex -> replacement | Invalid regex | regex",
            # 空内容
            "",
            # 只有注释
            "# 只有注释\n# 没有规则",
            # 格式错误
            "invalid_format_rule"
        ]
        
        for i, content in enumerate(error_scenarios):
            try:
                result = await replace_service.validate_rules(content)
                
                # 所有情况都应该返回有效的结果对象
                assert isinstance(result, RuleValidationResult)
                
                # 验证服务状态正常
                assert replace_service is not None
                
            except Exception as e:
                pytest.fail(f"Error scenario {i} caused unhandled exception: {e}")
    
    # 内存管理集成测试
    @pytest.mark.asyncio
    async def test_validation_memory_management_integration(self, replace_service):
        """测试验证过程中的内存管理集成"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # 执行多次大规模验证
        for iteration in range(5):
            # 创建大量规则
            large_content = "\n".join([
                f"pattern_{i}_{iteration} -> replacement_{i}_{iteration} | Rule {i} iteration {iteration}"
                for i in range(1000)
            ])
            
            result = await replace_service.validate_rules(large_content)
            assert isinstance(result, RuleValidationResult)
            
            # 检查内存使用
            current_memory = process.memory_info().rss
            memory_increase = current_memory - initial_memory
            
            # 内存增长不应过多（限制在100MB内）
            assert memory_increase < 100 * 1024 * 1024, f"Memory leak detected: {memory_increase} bytes"
    
    # 性能基准集成测试
    @pytest.mark.asyncio
    async def test_validation_performance_benchmark_integration(self, replace_service):
        """测试验证性能基准的集成测试"""
        # 性能基准测试用例
        benchmark_cases = [
            # 小规模：10条规则
            ("\n".join([f"small_{i} -> replacement_{i} | Small {i}" for i in range(10)]), 1.0),
            # 中等规模：100条规则
            ("\n".join([f"medium_{i} -> replacement_{i} | Medium {i}" for i in range(100)]), 3.0),
            # 大规模：1000条规则
            ("\n".join([f"large_{i} -> replacement_{i} | Large {i}" for i in range(1000)]), 10.0),
        ]
        
        for content, max_time in benchmark_cases:
            start_time = time.time()
            result = await replace_service.validate_rules(content)
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            # 验证处理时间在预期范围内
            assert processing_time < max_time, f"Performance benchmark failed: {processing_time}s > {max_time}s"
            
            # 验证结果正确性
            assert isinstance(result, RuleValidationResult)
            assert result.is_valid is True
    
    # 资源清理集成测试
    @pytest.mark.asyncio
    async def test_validation_resource_cleanup_integration(self, replace_service):
        """测试验证过程中的资源清理集成"""
        # 模拟资源使用场景
        initial_task_count = len(asyncio.all_tasks())
        
        # 执行多个验证任务
        validation_tasks = []
        for i in range(10):
            content = f"test_{i} -> replacement_{i} | Resource test {i}"
            task = asyncio.create_task(replace_service.validate_rules(content))
            validation_tasks.append(task)
        
        # 等待所有任务完成
        results = await asyncio.gather(*validation_tasks)
        
        # 验证所有结果
        for result in results:
            assert isinstance(result, RuleValidationResult)
        
        # 等待一段时间让资源清理
        await asyncio.sleep(0.1)
        
        # 检查任务是否正确清理
        final_task_count = len(asyncio.all_tasks())
        
        # 任务数量不应显著增加
        assert final_task_count <= initial_task_count + 2, "Tasks not properly cleaned up"
    
    # 异常传播集成测试
    @pytest.mark.asyncio
    async def test_validation_exception_propagation_integration(self, replace_service):
        """测试验证异常传播的集成处理"""
        # 模拟各种异常情况
        with patch('re.compile') as mock_compile:
            # 模拟正则表达式编译异常
            mock_compile.side_effect = Exception("Regex compilation failed")
            
            content = "test_pattern -> replacement | Exception test | regex"
            
            # 验证异常被正确处理
            result = await replace_service.validate_rules(content)
            
            # 应该返回有效的错误结果，而不是抛出异常
            assert isinstance(result, RuleValidationResult)
            assert result.is_valid is False
    
    # 配置集成测试
    @pytest.mark.asyncio
    async def test_validation_configuration_integration(self, replace_service):
        """测试验证配置的集成处理"""
        # 测试不同配置下的验证行为
        test_content = """# 配置测试
test -> replacement | Basic rule
\\d+ -> [NUM] | Regex rule | regex
(a+)+b -> [DANGEROUS] | Dangerous regex | regex
"""
        
        # 基本验证
        basic_result = await replace_service.validate_rules(test_content)
        assert isinstance(basic_result, RuleValidationResult)
        
        # 详细验证
        detailed_result = await replace_service.validate_rules_detailed(test_content)
        assert isinstance(detailed_result, dict)
        assert "is_valid" in detailed_result
        assert "dangerous_operations" in detailed_result
        
        # 比较两种验证模式的结果一致性
        assert basic_result.is_valid == detailed_result["is_valid"]
        assert basic_result.total_rules == detailed_result["total_rules"]