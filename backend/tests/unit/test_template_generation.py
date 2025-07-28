"""规则模板生成单元测试

BE-02: 规则模板下载功能的单元测试用例
"""

import pytest
import re
from datetime import datetime
from unittest.mock import patch, MagicMock
from backend.api.replace import _generate_template_content


class TestTemplateGeneration:
    """模板生成逻辑单元测试类"""
    
    def test_generate_template_content_basic(self):
        """测试基本模板内容生成"""
        content = _generate_template_content()
        
        # 验证基本结构
        assert isinstance(content, str)
        assert len(content) > 0
        assert "AetherFolio 批量替换规则模板" in content
        
        # 验证时间戳格式
        timestamp_pattern = r"# 生成时间: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
        assert re.search(timestamp_pattern, content) is not None
    
    def test_generate_template_content_sections(self):
        """测试模板内容各个区域"""
        content = _generate_template_content()
        
        # 验证所有必需的区域都存在
        required_sections = [
            "# ========== 基本替换示例 ==========",
            "# ========== 正则表达式替换示例 ==========",
            "# ========== 大小写敏感替换示例 ==========",
            "# ========== 组合模式示例 ==========",
            "# ========== 特殊字符处理示例 ==========",
            "# ========== 多语言支持示例 ==========",
            "# ========== 格式化示例 ==========",
            "# ========== 自定义规则区域 =========="
        ]
        
        for section in required_sections:
            assert section in content, f"缺少区域: {section}"
    
    def test_generate_template_content_examples(self):
        """测试模板内容示例"""
        content = _generate_template_content()
        
        # 验证基本替换示例
        assert "旧文本 -> 新文本" in content
        assert "错误的词汇 -> 正确的词汇" in content
        
        # 验证正则表达式示例
        assert "REGEX: \\d{4}-\\d{2}-\\d{2} -> [日期已隐藏]" in content
        assert "REGEX: [a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,} -> [邮箱已隐藏]" in content
        
        # 验证大小写敏感示例
        assert "CASE: HTML -> html" in content
        assert "CASE: JavaScript -> JS" in content
        
        # 验证组合模式示例
        assert "CASE:REGEX: Chapter\\s+(\\d+) -> 第$1章" in content
        
        # 验证特殊字符处理示例
        assert '\"引号内容\" -> \'引号内容\'' in content
        assert "<标签> -> [标签]" in content
        
        # 验证多语言支持示例
        assert "Hello World -> 你好世界" in content
        assert "数据库 -> Database" in content
    
    def test_generate_template_content_instructions(self):
        """测试模板使用说明"""
        content = _generate_template_content()
        
        # 验证使用说明
        instructions = [
            "# 使用说明:",
            "# 1. 每行一个替换规则",
            "# 2. 格式: 原文本 -> 新文本",
            "# 3. 支持正则表达式（在规则前添加 REGEX: 前缀）",
            "# 4. 支持大小写敏感（在规则前添加 CASE: 前缀）",
            "# 5. 以 # 开头的行为注释，将被忽略",
            "# 6. 空行将被忽略"
        ]
        
        for instruction in instructions:
            assert instruction in content, f"缺少说明: {instruction}"
    
    def test_generate_template_content_encoding(self):
        """测试模板内容编码"""
        content = _generate_template_content()
        
        # 验证可以正确编码为UTF-8
        try:
            encoded = content.encode('utf-8')
            decoded = encoded.decode('utf-8')
            assert decoded == content
        except UnicodeEncodeError:
            pytest.fail("模板内容无法正确编码为UTF-8")
        except UnicodeDecodeError:
            pytest.fail("模板内容无法正确从UTF-8解码")
    
    def test_generate_template_content_line_endings(self):
        """测试模板内容行结束符"""
        content = _generate_template_content()
        
        # 验证使用统一的行结束符
        lines = content.split('\n')
        assert len(lines) > 10, "模板内容行数过少"
        
        # 验证没有混合的行结束符
        assert '\r\n' not in content, "不应包含Windows行结束符"
        assert '\r' not in content, "不应包含Mac行结束符"
    
    def test_generate_template_content_timestamp_format(self):
        """测试时间戳格式"""
        content = _generate_template_content()
        
        # 提取时间戳
        timestamp_match = re.search(r"# 生成时间: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", content)
        assert timestamp_match is not None, "未找到时间戳"
        
        timestamp_str = timestamp_match.group(1)
        
        # 验证时间戳可以解析
        try:
            parsed_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            assert isinstance(parsed_time, datetime)
        except ValueError:
            pytest.fail(f"时间戳格式错误: {timestamp_str}")
    
    @patch('backend.api.replace.datetime')
    def test_generate_template_content_timestamp_accuracy(self, mock_datetime):
        """测试时间戳准确性"""
        # 模拟固定时间
        fixed_time = datetime(2024, 1, 15, 10, 30, 45)
        mock_datetime.now.return_value = fixed_time
        
        content = _generate_template_content()
        
        # 验证时间戳是否正确
        expected_timestamp = "# 生成时间: 2024-01-15 10:30:45"
        assert expected_timestamp in content
    
    def test_generate_template_content_size_limits(self):
        """测试模板内容大小限制"""
        content = _generate_template_content()
        
        # 验证内容大小在合理范围内
        content_size = len(content.encode('utf-8'))
        
        # 内容应该大于1KB但小于100KB
        assert content_size > 1024, f"模板内容过小: {content_size} bytes"
        assert content_size < 100 * 1024, f"模板内容过大: {content_size} bytes"
    
    def test_generate_template_content_special_characters(self):
        """测试特殊字符处理"""
        content = _generate_template_content()
        
        # 验证包含各种特殊字符
        special_chars = [
            '"',  # 双引号
            "'",  # 单引号
            '<',  # 小于号
            '>',  # 大于号
            '\\', # 反斜杠
            '$',  # 美元符号
            '(',  # 左括号
            ')',  # 右括号
            '[',  # 左方括号
            ']',  # 右方括号
            '{',  # 左大括号
            '}',  # 右大括号
        ]
        
        for char in special_chars:
            assert char in content, f"缺少特殊字符: {char}"
    
    def test_generate_template_content_regex_patterns(self):
        """测试正则表达式模式"""
        content = _generate_template_content()
        
        # 验证正则表达式示例的语法正确性
        regex_patterns = [
            r"\d{4}-\d{2}-\d{2}",  # 日期模式
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",  # 邮箱模式
            r"Chapter\s+(\d+)",  # 章节模式
        ]
        
        for pattern in regex_patterns:
            # 验证模式在模板中存在
            assert pattern in content, f"缺少正则表达式模式: {pattern}"
            
            # 验证模式语法正确
            try:
                re.compile(pattern)
            except re.error:
                pytest.fail(f"正则表达式语法错误: {pattern}")
    
    def test_generate_template_content_consistency(self):
        """测试模板内容一致性"""
        # 生成多次模板内容
        contents = [_generate_template_content() for _ in range(5)]
        
        # 除了时间戳外，其他内容应该相同
        normalized_contents = []
        for content in contents:
            # 移除时间戳行
            lines = content.split('\n')
            filtered_lines = [line for line in lines if not line.startswith('# 生成时间:')]
            normalized_content = '\n'.join(filtered_lines)
            normalized_contents.append(normalized_content)
        
        # 验证所有标准化内容相同
        first_content = normalized_contents[0]
        for i, content in enumerate(normalized_contents[1:], 1):
            assert content == first_content, f"第{i+1}次生成的内容与第1次不同"
    
    def test_generate_template_content_empty_lines(self):
        """测试模板内容空行处理"""
        content = _generate_template_content()
        lines = content.split('\n')
        
        # 验证有适当的空行分隔
        empty_line_count = sum(1 for line in lines if line.strip() == '')
        assert empty_line_count > 0, "模板应该包含空行用于分隔"
        
        # 验证不会有连续的多个空行
        consecutive_empty = 0
        max_consecutive_empty = 0
        
        for line in lines:
            if line.strip() == '':
                consecutive_empty += 1
                max_consecutive_empty = max(max_consecutive_empty, consecutive_empty)
            else:
                consecutive_empty = 0
        
        assert max_consecutive_empty <= 2, f"连续空行过多: {max_consecutive_empty}"
    
    def test_generate_template_content_comment_lines(self):
        """测试模板内容注释行"""
        content = _generate_template_content()
        lines = content.split('\n')
        
        # 统计注释行
        comment_lines = [line for line in lines if line.strip().startswith('#')]
        non_comment_lines = [line for line in lines if line.strip() and not line.strip().startswith('#')]
        
        # 验证有足够的注释说明
        assert len(comment_lines) > 10, "注释行数量过少"
        
        # 验证有实际的规则示例
        assert len(non_comment_lines) > 5, "规则示例过少"
        
        # 验证注释行格式正确
        for line in comment_lines:
            assert line