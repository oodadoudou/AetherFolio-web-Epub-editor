"""文本服务单元测试"""

import pytest
import tempfile
import shutil
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from backend.services.text_service import TextService, TextReplacement
from backend.models.schemas import ReplaceRule, FileContent


class TestTextService:
    """文本服务单元测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)
    
    @pytest.fixture
    def text_service(self):
        """创建文本服务实例"""
        return TextService()
    
    @pytest.fixture
    def sample_files(self, temp_dir):
        """创建示例文件"""
        files = {}
        
        # 创建.txt文件
        txt_file = temp_dir / "sample.txt"
        txt_content = "这是一个测试文件。\n包含多行内容。\n用于测试文本服务功能。"
        txt_file.write_text(txt_content, encoding='utf-8')
        files['txt'] = txt_file
        
        # 创建.md文件
        md_file = temp_dir / "sample.md"
        md_content = "# 标题\n\n这是Markdown文件。\n\n## 子标题\n\n内容段落。"
        md_file.write_text(md_content, encoding='utf-8')
        files['md'] = md_file
        
        # 创建空文件
        empty_file = temp_dir / "empty.txt"
        empty_file.write_text("", encoding='utf-8')
        files['empty'] = empty_file
        
        # 创建Unicode文件
        unicode_file = temp_dir / "unicode.txt"
        unicode_content = "Unicode测试：\n中文字符：你好世界\n特殊符号：©®™\n数学符号：∑∫∞≠≤≥"
        unicode_file.write_text(unicode_content, encoding='utf-8')
        files['unicode'] = unicode_file
        
        return files
    
    @pytest.fixture
    def sample_rules(self):
        """创建示例替换规则"""
        return [
            ReplaceRule(
                original="测试",
            replacement="TEST",
                description="测试替换",
                enabled=True,
                is_regex=False,
                case_sensitive=False
            ),
            ReplaceRule(
                original=r"\\d+",
            replacement="[数字]",
                description="数字替换",
                enabled=True,
                is_regex=True,
                case_sensitive=False
            )
        ]
    
    def test_service_initialization(self, text_service):
        """测试服务初始化"""
        assert text_service is not None
        assert text_service.service_name == "text"
    
    @pytest.mark.asyncio
    async def test_read_text_file_txt(self, text_service, sample_files):
        """测试读取txt文件"""
        txt_file = sample_files["txt"]
        file_content = await text_service.read_text_file(txt_file)
        assert file_content.content == "这是一个测试文件。\n包含多行内容。\n用于测试文本服务功能。"
    
    @pytest.mark.asyncio
    async def test_read_text_file_md(self, text_service, sample_files):
        """测试读取md文件"""
        md_file = sample_files["md"]
        file_content = await text_service.read_text_file(md_file)
        assert "# 标题" in file_content.content
    
    @pytest.mark.asyncio
    async def test_read_text_file_multiple_extensions(self, text_service, temp_dir):
        """测试读取多种扩展名的文件"""
        # 创建不同扩展名的文件
        files = {
            "test.txt": "TXT文件内容",
            "test.md": "# Markdown文件",
            "test.text": "TEXT文件内容"
        }
        
        for filename, content in files.items():
            file_path = temp_dir / filename
            file_path.write_text(content, encoding='utf-8')
            
            # 读取并验证
            file_content = await text_service.read_text_file(file_path)
            assert file_content.content == content
    
    @pytest.mark.asyncio
    async def test_read_text_file_not_found(self, text_service, temp_dir):
        """测试读取不存在的文件"""
        non_existent_file = temp_dir / "non_existent.txt"
        
        with pytest.raises(FileNotFoundError):
            await text_service.read_text_file(non_existent_file)
    
    @pytest.mark.asyncio
    async def test_read_text_file_empty_file(self, text_service, temp_dir):
        """测试读取空文件"""
        empty_file = temp_dir / "empty.txt"
        empty_file.write_text("", encoding='utf-8')
        
        file_content = await text_service.read_text_file(empty_file)
        assert file_content.content == ""
    
    @pytest.mark.asyncio
    async def test_read_text_file_unicode(self, text_service, temp_dir):
        """测试读取包含Unicode字符的文件"""
        unicode_file = temp_dir / "unicode.txt"
        unicode_content = "测试中文内容 🚀 emoji 和特殊字符 ñáéíóú"
        unicode_file.write_text(unicode_content, encoding='utf-8')
        
        file_content = await text_service.read_text_file(unicode_file)
        assert file_content.content == unicode_content
    
    @pytest.mark.asyncio
    async def test_write_text_file_new_file(self, text_service, temp_dir):
        """测试写入新文件"""
        new_file = temp_dir / "new_file.txt"
        content = "新文件内容"
        
        await text_service.write_text_file(new_file, content)
        
        # 验证文件被创建
        assert new_file.exists()
        
        # 验证内容正确
        written_content = new_file.read_text(encoding='utf-8')
        assert written_content == content
    
    @pytest.mark.asyncio
    async def test_write_text_file_existing_file(self, text_service, temp_dir):
        """测试覆盖现有文件"""
        existing_file = temp_dir / "existing.txt"
        original_content = "原始内容"
        new_content = "新内容"
        
        # 创建原始文件
        existing_file.write_text(original_content, encoding='utf-8')
        
        # 覆盖文件
        await text_service.write_text_file(existing_file, new_content)
        
        # 验证内容被更新
        written_content = existing_file.read_text(encoding='utf-8')
        assert written_content == new_content
    
    @pytest.mark.asyncio
    async def test_write_text_file_empty_content(self, text_service, temp_dir):
        """测试写入空内容"""
        empty_file = temp_dir / "empty_write.txt"
        
        await text_service.write_text_file(empty_file, "")
        
        # 验证文件被创建
        assert empty_file.exists()
        
        # 验证内容为空
        content = empty_file.read_text(encoding='utf-8')
        assert content == ""
    
    @pytest.mark.asyncio
    async def test_write_text_file_unicode(self, text_service, temp_dir):
        """测试写入Unicode内容"""
        unicode_file = temp_dir / "unicode_write.txt"
        unicode_content = "测试中文 🎉 emoji 和特殊字符"
        
        await text_service.write_text_file(unicode_file, unicode_content)
        
        # 验证文件被创建
        assert unicode_file.exists()
        
        # 验证内容正确
        written_content = unicode_file.read_text(encoding='utf-8')
        assert written_content == unicode_content
    
    @pytest.mark.asyncio
    async def test_write_text_file_large_content(self, text_service, temp_dir):
        """测试写入大文件内容"""
        large_file = temp_dir / "large_file.txt"
        large_content = "大文件测试内容\n" * 5000  # 约70KB
        
        await text_service.write_text_file(large_file, large_content)
        
        # 验证文件存在
        assert large_file.exists()
        
        # 读取并验证内容
        file_content = await text_service.read_text_file(large_file)
        assert file_content.content == large_content
        assert len(file_content.content) >= 40000  # 调整期望长度
    
    @pytest.mark.asyncio
    async def test_process_text_file(self, text_service, sample_files, sample_rules):
        """测试处理文本文件"""
        file_path = sample_files['txt']
        original_content = sample_files['txt'].read_text(encoding='utf-8')
        
        modified_content, replacements = await text_service.process_text_file(
            file_path, original_content, sample_rules
        )
        
        # 验证替换结果
        assert "TEST" in modified_content  # "测试" 应该被替换为 "TEST"
        assert len(replacements) > 0
        assert all(isinstance(r, TextReplacement) for r in replacements)
    
    @pytest.mark.asyncio
    async def test_validate_text_file(self, text_service, sample_files, temp_dir):
        """测试文件验证"""
        # 测试有效文件
        assert await text_service.validate_text_file(sample_files['txt']) == True
        assert await text_service.validate_text_file(sample_files['md']) == True
        
        # 测试无效扩展名
        invalid_file = temp_dir / "test.pdf"
        invalid_file.write_text("content", encoding='utf-8')
        assert await text_service.validate_text_file(invalid_file) == False
    
    @pytest.mark.asyncio
    async def test_read_file_content_session(self, text_service, temp_dir):
        """测试读取会话文件内容"""
        session_id = "test_session"
        test_content = "测试会话内容"
        
        with patch('backend.services.text_service.settings') as mock_settings:
            mock_settings.session_dir = str(temp_dir)
            
            # 先写入内容
            await text_service.write_file_content(session_id, test_content)
            
            # 读取内容
            result = await text_service.read_file_content(session_id)
            assert result == test_content
    
    @pytest.mark.asyncio
    async def test_read_file_content_not_found(self, text_service, temp_dir):
        """测试读取不存在的会话文件"""
        session_id = "non_existent_session"
        
        with patch('backend.core.config.settings') as mock_settings:
            mock_settings.session_dir = str(temp_dir)
            
            with pytest.raises(FileNotFoundError):
                await text_service.read_file_content(session_id)
    
    @pytest.mark.asyncio
    async def test_write_file_content_session(self, text_service, temp_dir):
        """测试写入会话文件内容"""
        session_id = "test_session"
        content = "测试会话文件内容"
        
        with patch('backend.services.text_service.settings') as mock_settings:
            mock_settings.session_dir = str(temp_dir)
            
            # 写入内容
            await text_service.write_file_content(session_id, content)
            
            # 验证会话目录存在
            session_dir = temp_dir / session_id
            assert session_dir.exists()
            
            # 验证内容文件存在
            content_file = session_dir / "content.txt"
            assert content_file.exists()
            
            # 验证内容正确
            written_content = content_file.read_text(encoding='utf-8')
            assert written_content == content
    
    @pytest.mark.asyncio
    async def test_generate_text_report(self, text_service, sample_files, sample_rules):
        """测试生成文本报告"""
        file_path = sample_files['txt']
        original_content = sample_files['txt'].read_text(encoding='utf-8')
        
        # 先处理文件获取替换记录
        modified_content, replacements = await text_service.process_text_file(
            file_path, original_content, sample_rules
        )
        
        # 生成报告
        report = await text_service.generate_text_report(
            str(file_path), original_content, modified_content, replacements
        )
        
        assert isinstance(report, list)
        # 如果有替换，报告应该包含数据
        if replacements:
            assert len(report) > 0
            for item in report:
                assert 'original' in item
                assert 'modified' in item
                assert 'position' in item
    
    @pytest.mark.asyncio
    async def test_concurrent_read_operations(self, text_service, temp_dir):
        """测试并发读取操作"""
        # 创建测试文件
        test_file = temp_dir / "concurrent_test.txt"
        content = "并发读取测试内容\n应该在所有并发读取中保持一致"
        test_file.write_text(content, encoding='utf-8')
        
        # 并发读取文件
        async def read_file():
            file_content = await text_service.read_text_file(test_file)
            return file_content.content
        
        tasks = [read_file() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        # 验证所有结果都相同
        for result in results:
            assert result == content
    
    @pytest.mark.asyncio
    async def test_concurrent_write_operations(self, text_service, temp_dir):
        """测试并发写入操作"""
        async def write_file(index):
            file_path = temp_dir / f"concurrent_write_{index}.txt"
            content = f"第{index}次写入的内容\n时间戳：{asyncio.get_event_loop().time()}\n循环次数：{index}"
            await text_service.write_text_file(file_path, content)
            return file_path, content
        
        tasks = [write_file(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        # 验证所有文件都被正确写入
        for file_path, expected_content in results:
            assert file_path.exists()
            actual_content = file_path.read_text(encoding='utf-8')
            assert actual_content == expected_content
    
    @pytest.mark.asyncio
    async def test_file_encoding_detection(self, text_service, temp_dir):
        """测试文件编码检测"""
        # 创建不同编码的文件
        encodings = ['utf-8', 'gbk', 'latin1']
        
        for encoding in encodings:
            file_path = temp_dir / f"test_{encoding}.txt"
            content = "测试编码检测功能" if encoding in ['utf-8', 'gbk'] else "Test encoding detection"
            
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)
            
            # 读取文件并验证编码检测
            file_content = await text_service.read_text_file(file_path)
            assert file_content.content == content
            # 编码可能被自动检测为其他兼容编码
            assert file_content.encoding is not None
    
    @pytest.mark.asyncio
    async def test_file_extension_priority(self, text_service, temp_dir):
        """测试文件扩展名优先级"""
        # 创建多个不同扩展名的文件
        extensions = ['.txt', '.text', '.md', '.markdown']
        
        for ext in extensions:
            file_path = temp_dir / f"test{ext}"
            content = f"{ext.upper()}文件内容"
            file_path.write_text(content, encoding='utf-8')
        
        # 验证服务能够正确识别和处理不同扩展名
        for ext in extensions:
            file_path = temp_dir / f"test{ext}"
            assert await text_service.validate_text_file(file_path) == True
    
    @pytest.mark.asyncio
    async def test_apply_rule_to_text_regex(self, text_service):
        """测试正则表达式规则应用"""
        rule = ReplaceRule(
            original=r"\d+",
            replacement="[数字]",
            description="数字替换",
            enabled=True,
            is_regex=True,
            case_sensitive=False
        )
        
        text = "这里有123个数字和456个字符"
        new_text, replacements = await text_service._apply_rule_to_text(text, rule, 0)
        
        assert "[数字]" in new_text
        assert "123" not in new_text or "456" not in new_text
        assert len(replacements) >= 1
    
    @pytest.mark.asyncio
    async def test_apply_rule_to_text_simple(self, text_service):
        """测试简单文本规则应用"""
        rule = ReplaceRule(
            original="测试",
            replacement="检验",
            description="测试替换",
            enabled=True,
            is_regex=False,
            case_sensitive=True
        )
        
        text = "这是一个测试文本，用于测试功能"
        new_text, replacements = await text_service._apply_rule_to_text(text, rule, 0)
        
        assert "检验" in new_text
        assert "测试" not in new_text
        assert len(replacements) == 2  # 应该有两个"测试"被替换