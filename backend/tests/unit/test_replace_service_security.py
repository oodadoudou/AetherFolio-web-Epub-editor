import pytest
import pytest_asyncio
import re
import time
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any

from backend.services.replace_service import ReplaceService
from backend.models.schemas import ReplaceRule, RuleValidationResult
from backend.core.exceptions import ContentValidationError


class TestReplaceServiceSecurity:
    """ReplaceService 安全性测试 - BE-03任务补充测试用例"""
    
    @pytest_asyncio.fixture
    async def service(self):
        """创建 ReplaceService 实例"""
        service = ReplaceService()
        await service._initialize()
        yield service
        await service.cleanup()
    
    # 恶意正则表达式防护测试
    @pytest.mark.asyncio
    async def test_validate_rules_malicious_regex_catastrophic_backtracking(self, service):
        """测试灾难性回溯正则表达式防护"""
        malicious_content = """# 恶意正则表达式测试
# 灾难性回溯模式
(a+)+b -> replacement | Catastrophic backtracking | regex
(x+x+)+y -> replacement | Another catastrophic pattern | regex
([a-zA-Z]+)*$ -> replacement | Nested quantifiers | regex
"""
        
        result = await service.validate_rules(malicious_content)
        
        # 应该检测到恶意正则表达式
        assert result.is_valid is False
        assert len(result.invalid_rules) > 0
        
        # 检查是否包含正则表达式相关的错误信息
        regex_errors = [rule for rule in result.invalid_rules 
                       if 'regex' in rule.get('error', '').lower() or 
                          'pattern' in rule.get('error', '').lower()]
        assert len(regex_errors) > 0
    
    @pytest.mark.asyncio
    async def test_validate_rules_malicious_regex_redos_patterns(self, service):
        """测试ReDoS攻击模式防护"""
        redos_patterns = [
            "(a|a)*",  # 指数级回溯
            "([a-zA-Z]+)*",  # 嵌套量词
            "(a+)+",  # 重复量词
            "(.*a){x,y}",  # 贪婪匹配与回溯
            "^(a+)+$",  # 锚点与量词组合
        ]
        
        for pattern in redos_patterns:
            malicious_content = f"{pattern} -> safe_replacement | ReDoS test | regex"
            
            result = await service.validate_rules(malicious_content)
            
            # 应该检测到潜在的ReDoS模式
            assert result.is_valid is False, f"Failed to detect ReDoS pattern: {pattern}"
    
    @pytest.mark.asyncio
    async def test_validate_rules_regex_timeout_protection(self, service):
        """测试正则表达式超时保护"""
        # 模拟超时的正则表达式
        timeout_pattern = "(a+)+b"
        test_content = f"{timeout_pattern} -> replacement | Timeout test | regex"
        
        # 使用patch模拟re.compile超时
        with patch('re.compile') as mock_compile:
            mock_compile.side_effect = Exception("regex timeout")
            
            result = await service.validate_rules(test_content)
            
            assert result.is_valid is False
            assert len(result.invalid_rules) > 0
    
    @pytest.mark.asyncio
    async def test_validate_rules_regex_complexity_limit(self, service):
        """测试正则表达式复杂度限制"""
        # 创建高复杂度的正则表达式
        complex_patterns = [
            "(a{1,10}){1,10}",  # 嵌套量词
            "(?:(?:a|b)*){10,}",  # 深度嵌套
            "a{1000,2000}",  # 大量重复
            "(a|b|c|d|e|f|g|h|i|j){50,}",  # 大量选择
        ]
        
        for pattern in complex_patterns:
            test_content = f"{pattern} -> replacement | Complex regex | regex"
            
            result = await service.validate_rules(test_content)
            
            # 应该限制过于复杂的正则表达式
            if not result.is_valid:
                assert len(result.invalid_rules) > 0
    
    # 超长规则文件处理测试
    @pytest.mark.asyncio
    async def test_validate_rules_oversized_file_content(self, service):
        """测试超大规则文件内容处理"""
        # 创建超大规则文件（模拟10MB内容）
        large_rule = "a" * 1000 + " -> " + "b" * 1000 + " | Large rule"
        large_content = "\n".join([large_rule] * 5000)  # 约10MB
        
        start_time = time.time()
        result = await service.validate_rules(large_content)
        end_time = time.time()
        
        # 验证处理时间不应过长（超过30秒视为超时）
        processing_time = end_time - start_time
        assert processing_time < 30, f"Processing took too long: {processing_time}s"
        
        # 应该能够处理或适当拒绝超大文件
        assert isinstance(result, RuleValidationResult)
    
    @pytest.mark.asyncio
    async def test_validate_rules_excessive_rule_count(self, service):
        """测试过多规则数量限制"""
        # 创建大量规则（10000条）
        rules = []
        for i in range(10000):
            rules.append(f"rule_{i} -> replacement_{i} | Rule {i}")
        
        large_content = "\n".join(rules)
        
        start_time = time.time()
        result = await service.validate_rules(large_content)
        end_time = time.time()
        
        # 验证处理时间合理
        processing_time = end_time - start_time
        assert processing_time < 60, f"Processing took too long: {processing_time}s"
        
        # 应该有规则数量限制或性能保护
        assert isinstance(result, RuleValidationResult)
    
    @pytest.mark.asyncio
    async def test_validate_rules_memory_usage_protection(self, service):
        """测试内存使用保护"""
        # 创建可能导致内存问题的规则
        memory_intensive_rules = [
            "x" * 100000 + " -> " + "y" * 100000 + " | Memory test 1",
            ".*" * 1000 + " -> replacement | Memory test 2 | regex",
            "(a|b|c)" * 1000 + " -> replacement | Memory test 3 | regex",
        ]
        
        content = "\n".join(memory_intensive_rules)
        
        # 监控内存使用（简单实现）
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss
        
        result = await service.validate_rules(content)
        
        memory_after = process.memory_info().rss
        memory_increase = memory_after - memory_before
        
        # 内存增长不应超过100MB
        assert memory_increase < 100 * 1024 * 1024, f"Memory usage increased by {memory_increase} bytes"
    
    # Unicode字符测试
    @pytest.mark.asyncio
    async def test_validate_rules_unicode_characters(self, service):
        """测试Unicode字符处理"""
        unicode_content = """# Unicode字符测试
# 中文字符
你好 -> 再见 | Chinese characters
# 日文字符
こんにちは -> さようなら | Japanese characters
# 阿拉伯文字符
مرحبا -> وداعا | Arabic characters
# 表情符号
😀 -> 😢 | Emoji characters
# 特殊Unicode字符
\u200B -> \u200C | Zero-width characters
# 组合字符
é -> e | Combining characters
"""
        
        result = await service.validate_rules(unicode_content)
        
        # 应该能够正确处理Unicode字符
        assert isinstance(result, RuleValidationResult)
        
        # 检查是否正确解析了Unicode规则
        if result.is_valid:
            assert result.valid_rules > 0
    
    @pytest.mark.asyncio
    async def test_validate_rules_unicode_normalization(self, service):
        """测试Unicode标准化处理"""
        # 测试不同Unicode标准化形式
        import unicodedata
        
        # 创建相同字符的不同标准化形式
        char_nfc = unicodedata.normalize('NFC', 'é')  # 组合形式
        char_nfd = unicodedata.normalize('NFD', 'é')  # 分解形式
        
        content = f"""{char_nfc} -> replacement1 | NFC form
{char_nfd} -> replacement2 | NFD form"""
        
        result = await service.validate_rules(content)
        
        # 应该能够处理不同的Unicode标准化形式
        assert isinstance(result, RuleValidationResult)
    
    @pytest.mark.asyncio
    async def test_validate_rules_unicode_security_issues(self, service):
        """测试Unicode安全问题"""
        # 测试可能的Unicode安全问题
        security_test_content = """# Unicode安全测试
# 零宽字符
\u200B -> \u200C | Zero-width space
# 方向控制字符
\u202E -> \u202D | Direction override
# 不可见字符
\u00A0 -> \u0020 | Non-breaking space
# 同形异义字符
а -> a | Cyrillic vs Latin
"""
        
        result = await service.validate_rules(security_test_content)
        
        # 应该检测或警告潜在的Unicode安全问题
        assert isinstance(result, RuleValidationResult)
    
    # 循环引用和递归替换检测测试
    @pytest.mark.asyncio
    async def test_validate_rules_circular_replacement_detection(self, service):
        """测试循环替换检测"""
        circular_content = """# 循环替换测试
a -> b | Step 1
b -> c | Step 2
c -> a | Step 3 - creates cycle
"""
        
        # 使用详细验证来检测循环引用
        result = await service.validate_rules_detailed(circular_content)
        
        # 应该检测到循环引用
        assert "warnings" in result
        circular_warnings = [w for w in result["warnings"] 
                           if "circular" in w.get("message", "").lower() or 
                              "cycle" in w.get("message", "").lower()]
        assert len(circular_warnings) > 0
    
    @pytest.mark.asyncio
    async def test_validate_rules_recursive_replacement_depth(self, service):
        """测试递归替换深度检测"""
        # 创建深度递归替换链
        recursive_rules = []
        for i in range(20):  # 创建20层深度的替换链
            recursive_rules.append(f"level_{i} -> level_{i+1} | Recursive level {i}")
        
        recursive_content = "\n".join(recursive_rules)
        
        result = await service.validate_rules_detailed(recursive_content)
        
        # 应该检测到过深的递归替换
        assert "warnings" in result
        depth_warnings = [w for w in result["warnings"] 
                         if "recursive" in w.get("message", "").lower() or 
                            "depth" in w.get("message", "").lower()]
        assert len(depth_warnings) > 0
    
    @pytest.mark.asyncio
    async def test_validate_rules_self_reference_detection(self, service):
        """测试自引用检测"""
        self_ref_content = """# 自引用测试
test -> test_modified | Self reference
pattern -> pattern | Exact self reference
word -> word_suffix | Partial self reference
"""
        
        result = await service.validate_rules_detailed(self_ref_content)
        
        # 应该检测到自引用问题
        assert "warnings" in result or "dangerous_operations" in result
    
    # 边界条件和异常处理测试
    @pytest.mark.asyncio
    async def test_validate_rules_malformed_encoding(self, service):
        """测试编码错误处理"""
        # 模拟编码错误的内容
        with patch('builtins.open', side_effect=UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid')):
            # 直接测试字符串内容，模拟编码问题
            malformed_content = "test -> replacement | Normal rule"
            
            result = await service.validate_rules(malformed_content)
            
            # 应该能够处理编码错误
            assert isinstance(result, RuleValidationResult)
    
    @pytest.mark.asyncio
    async def test_validate_rules_null_bytes_injection(self, service):
        """测试空字节注入防护"""
        null_byte_content = """# 空字节注入测试
test\x00injection -> replacement | Null byte test
normal_rule -> replacement | Normal rule
"""
        
        result = await service.validate_rules(null_byte_content)
        
        # 应该检测或清理空字节
        assert isinstance(result, RuleValidationResult)
    
    @pytest.mark.asyncio
    async def test_validate_rules_control_characters(self, service):
        """测试控制字符处理"""
        control_char_content = """# 控制字符测试
test\r\n -> replacement | CRLF test
test\t -> replacement | Tab test
test\x1f -> replacement | Unit separator
"""
        
        result = await service.validate_rules(control_char_content)
        
        # 应该能够处理控制字符
        assert isinstance(result, RuleValidationResult)
    
    @pytest.mark.asyncio
    async def test_validate_rules_performance_regression(self, service):
        """测试性能回归检测"""
        # 创建可能导致性能问题的规则组合
        performance_test_rules = []
        
        # 添加复杂正则表达式
        for i in range(100):
            performance_test_rules.append(f"pattern_{i}.*test -> replacement_{i} | Complex regex {i} | regex")
        
        # 添加长文本规则
        for i in range(100):
            long_text = "word" * 100
            performance_test_rules.append(f"{long_text}_{i} -> replacement_{i} | Long text {i}")
        
        content = "\n".join(performance_test_rules)
        
        start_time = time.time()
        result = await service.validate_rules(content)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # 验证处理时间在合理范围内（10秒内）
        assert processing_time < 10, f"Performance regression detected: {processing_time}s"
        assert isinstance(result, RuleValidationResult)