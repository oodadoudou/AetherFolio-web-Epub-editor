import pytest
import pytest_asyncio
import asyncio
import time
import json
import re
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from pathlib import Path
from typing import List, Dict, Any

from backend.services.replace_service import ReplaceService, replace_service
from backend.models.schemas import (
    ReplaceRule, ReplaceResult, ReplaceProgress, BatchReplaceReport,
    RuleValidationResult, FileType, FileNode, FileContent
)
from backend.models.session import Session


class TestReplaceService:
    """ReplaceService 单元测试"""
    
    @pytest_asyncio.fixture
    async def service(self):
        """创建 ReplaceService 实例"""
        service = ReplaceService()
        await service._initialize()
        yield service
        await service.cleanup()
    
    @pytest.fixture
    def sample_rules(self):
        """示例替换规则"""
        return [
            ReplaceRule(
                original="old_text",
            replacement="new_text",
                description="Replace old with new",
                enabled=True,
                is_regex=False,
                case_sensitive=True
            ),
            ReplaceRule(
                original=r"\d{4}-\d{2}-\d{2}",
            replacement="[DATE]",
                description="Replace dates with placeholder",
                enabled=True,
                is_regex=True,
                case_sensitive=True
            )
        ]
    
    @pytest.fixture
    def sample_rules_content(self):
        """示例规则文件内容"""
        return """# 替换规则文件
# 格式: 搜索文本 -> 替换文本 | 描述

old_text -> new_text | Replace old with new
\\d{4}-\\d{2}-\\d{2} -> [DATE] | Replace dates with placeholder | regex
"""
    
    @pytest.fixture
    def sample_session(self):
        """示例会话"""
        return Session(
            session_id="test_session_123",
            epub_path="/path/to/test.epub",
            upload_time=datetime.now(),
            original_filename="test.epub",
            file_size=1024,
            metadata={
                "file_type": "epub",
                "file_size": 1024,
                "original_filename": "test.epub"
            }
        )
    
    @pytest.fixture
    def sample_text_session(self):
        """示例文本会话"""
        return Session(
            session_id="test_text_session_123",
            epub_path="/path/to/test.txt",
            upload_time=datetime.now(),
            original_filename="test.txt",
            file_size=512,
            metadata={
                "file_type": "text",
                "file_size": 512,
                "original_filename": "test.txt"
            }
        )

    # 测试规则验证
    @pytest.mark.asyncio
    async def test_validate_rules_valid(self, service, sample_rules_content):
        """测试有效规则验证"""
        result = await service.validate_rules(sample_rules_content)
        
        assert result.is_valid is True
        assert result.valid_rules == 2
        assert len(result.invalid_rules) == 0
        assert result.total_rules == 2
    
    @pytest.mark.asyncio
    async def test_validate_rules_invalid(self, service):
        """测试无效规则验证"""
        invalid_content = """# 无效规则
invalid_rule_without_arrow
 -> empty_search | Empty search
"""
        
        result = await service.validate_rules(invalid_content)
        
        assert result.is_valid is False
        assert len(result.invalid_rules) > 0
    
    @pytest.mark.asyncio
    async def test_validate_rules_empty(self, service):
        """测试空规则验证"""
        result = await service.validate_rules("")
        
        assert result.is_valid is True
        assert result.valid_rules == 0
        assert len(result.invalid_rules) == 0
    
    @pytest.mark.asyncio
    async def test_validate_rules_regex_error(self, service):
        """测试正则表达式错误"""
        invalid_regex_content = "[invalid_regex|replacement|true|true|Invalid regex"
        
        result = await service.validate_rules(invalid_regex_content)
        
        assert result.is_valid is False
        assert len(result.invalid_rules) > 0
    
    # 测试规则解析
    @pytest.mark.asyncio
    async def test_parse_rules_success(self, service, sample_rules_content):
        """测试规则解析成功"""
        rules = await service._parse_rules(sample_rules_content)
        
        assert len(rules) == 2
        assert rules[0].original == "old_text"
        assert rules[0].replacement == "new_text"
        assert rules[0].is_regex is False
        assert rules[1].is_regex is True
    
    @pytest.mark.asyncio
    async def test_parse_rules_with_comments(self, service):
        """测试带注释的规则解析"""
        content_with_comments = """# 这是注释
# 另一个注释
test -> result | Test rule

# 空行和注释应该被忽略
"""
        
        rules = await service._parse_rules(content_with_comments)
        
        assert len(rules) == 1
        assert rules[0].original == "test"
        assert rules[0].replacement == "result"
    
    # 测试单个规则应用
    @pytest.mark.asyncio
    async def test_apply_rule_text_replacement(self, service, sample_rules):
        """测试文本替换"""
        content = "This is old_text that should be replaced. Another old_text here."
        rule = sample_rules[0]  # 非正则规则
        
        new_content, count, replacements = await service._apply_rule(
            content, rule, case_sensitive=True, use_regex=False
        )
        
        assert count == 2
        assert "new_text" in new_content
        assert "old_text" not in new_content
        assert len(replacements) == 2
        assert replacements[0]["original"] == "old_text"
        assert replacements[0]["replacement"] == "new_text"
    
    @pytest.mark.asyncio
    async def test_apply_rule_regex_replacement(self, service, sample_rules):
        """测试正则表达式替换"""
        content = "Date: 2023-12-25 and another date 2024-01-01"
        rule = sample_rules[1]  # 正则规则
        
        new_content, count, replacements = await service._apply_rule(
            content, rule, case_sensitive=True, use_regex=True
        )
        
        assert count == 2
        assert "[DATE]" in new_content
        assert "2023-12-25" not in new_content
        assert "2024-01-01" not in new_content
        assert len(replacements) == 2
    
    @pytest.mark.asyncio
    async def test_apply_rule_case_insensitive(self, service):
        """测试不区分大小写替换"""
        content = "Hello HELLO hello HeLLo"
        rule = ReplaceRule(
            original="hello",
            replacement="hi",
            description="Test case insensitive",
            enabled=True,
            is_regex=False
        )
        
        new_content, count, replacements = await service._apply_rule(
            content, rule, case_sensitive=False, use_regex=False
        )
        
        assert count == 4
        assert new_content == "hi hi hi hi"
    
    @pytest.mark.asyncio
    async def test_apply_rule_no_matches(self, service, sample_rules):
        """测试无匹配的规则应用"""
        content = "This text has no matches"
        rule = sample_rules[0]
        
        new_content, count, replacements = await service._apply_rule(
            content, rule, case_sensitive=True, use_regex=False
        )
        
        assert count == 0
        assert new_content == content
        assert len(replacements) == 0
    
    # 测试进度更新
    @pytest.mark.asyncio
    async def test_update_progress(self, service):
        """测试进度更新"""
        task_id = "test_task_123"
        
        # 初始化进度
        service.progress_data[task_id] = ReplaceProgress(
            session_id="test_session",
            task_id=task_id,
            status="running",
            total_files=10,
            processed_files=0,
            total_replacements=0,
            current_file="",
            progress_percentage=0.0,
            start_time=time.time(),
            estimated_remaining=0
        )
        
        # 更新进度
        await service._update_progress(
            task_id,
            processed_files=5,
            progress_percentage=50.0,
            current_file="test.html"
        )
        
        progress = service.progress_data[task_id]
        assert progress.processed_files == 5
        assert progress.progress_percentage == 50.0
        assert progress.current_file == "test.html"
        assert progress.estimated_remaining >= 0
    
    # 测试获取进度
    @pytest.mark.asyncio
    async def test_get_progress(self, service):
        """测试获取进度"""
        task_id = "test_task_123"
        
        # 不存在的任务
        progress = await service.get_progress(task_id)
        assert progress is None
        
        # 存在的任务
        service.progress_data[task_id] = ReplaceProgress(
            session_id="test_session",
            task_id=task_id,
            status="running",
            total_files=10,
            processed_files=5,
            total_replacements=20,
            current_file="test.html",
            progress_percentage=50.0,
            start_time=time.time(),
            estimated_remaining=30
        )
        
        progress = await service.get_progress(task_id)
        assert progress is not None
        assert progress.task_id == task_id
        assert progress.processed_files == 5
    
    # 测试获取报告
    @pytest.mark.asyncio
    async def test_get_report(self, service):
        """测试获取报告"""
        task_id = "test_task_123"
        
        # 不存在的报告
        report = await service.get_report(task_id)
        assert report is None
        
        # 存在的报告
        service.replace_reports[task_id] = BatchReplaceReport(
            task_id=task_id,
            session_id="test_session",
            total_files=5,
            total_replacements=20,
            results=[],
            file_stats={},
            rule_stats={},
            generated_at=time.time()
        )
        
        report = await service.get_report(task_id)
        assert report is not None
        assert report.task_id == task_id
        assert report.total_files == 5
    
    @pytest.mark.asyncio
    async def test_get_report_by_session(self, service):
        """测试根据会话ID获取报告"""
        session_id = "test_session_123"
        task_id = "test_task_123"
        
        # 不存在的映射
        report = await service.get_report_by_session(session_id)
        assert report is None
        
        # 存在的映射
        service.session_to_task[session_id] = task_id
        service.replace_reports[task_id] = BatchReplaceReport(
            task_id=task_id,
            session_id=session_id,
            total_files=3,
            total_replacements=15,
            results=[],
            file_stats={},
            rule_stats={},
            generated_at=time.time()
        )
        
        report = await service.get_report_by_session(session_id)
        assert report is not None
        assert report.session_id == session_id
    
    # 测试任务取消
    @pytest.mark.asyncio
    async def test_cancel_task(self, service):
        """测试任务取消"""
        task_id = "test_task_123"
        
        # 初始化进度
        service.progress_data[task_id] = ReplaceProgress(
            session_id="test_session",
            task_id=task_id,
            status="running",
            total_files=10,
            processed_files=3,
            total_replacements=0,
            current_file="test.html",
            progress_percentage=30.0,
            start_time=time.time(),
            estimated_remaining=60
        )
        
        # 取消任务
        result = await service.cancel_task(task_id)
        
        # 检查状态更新
        progress = service.progress_data[task_id]
        assert progress.status == "cancelled"
    
    # 测试任务数据清理
    @pytest.mark.asyncio
    async def test_cleanup_task_data(self, service):
        """测试任务数据清理"""
        task_id = "test_task_123"
        session_id = "test_session_123"
        
        # 设置测试数据
        service.progress_data[task_id] = ReplaceProgress(
            session_id=session_id,
            task_id=task_id,
            status="completed",
            total_files=5,
            processed_files=5,
            total_replacements=20,
            current_file="",
            progress_percentage=100.0,
            start_time=time.time(),
            estimated_remaining=0
        )
        service.replace_reports[task_id] = BatchReplaceReport(
            task_id=task_id,
            session_id=session_id,
            total_files=5,
            total_replacements=20,
            results=[],
            file_stats={},
            rule_stats={},
            generated_at=time.time()
        )
        service.session_to_task[session_id] = task_id
        
        # 清理数据
        await service.cleanup_task_data(task_id)
        
        # 验证数据已清理
        assert task_id not in service.progress_data
        assert task_id not in service.replace_reports
        assert session_id not in service.session_to_task
    
    # 测试目标文件获取
    @pytest.mark.asyncio
    async def test_get_target_files(self, service):
        """测试获取目标文件列表"""
        # 模拟文件树
        file_tree = [
            FileNode(
                name="chapter1.html",
                path="OEBPS/chapter1.html",
                type=FileType.HTML,
                size=1024,
                children=[]
            ),
            FileNode(
                name="chapter2.html",
                path="OEBPS/chapter2.html",
                type=FileType.HTML,
                size=2048,
                children=[]
            ),
            FileNode(
                name="styles.css",
                path="OEBPS/styles.css",
                type=FileType.CSS,
                size=512,
                children=[]
            )
        ]
        
        # 获取所有目标文件
        target_files = await service._get_target_files(file_tree, None)
        assert len(target_files) == 2  # 只有HTML文件
        assert "OEBPS/chapter1.html" in target_files
        assert "OEBPS/chapter2.html" in target_files
        assert "OEBPS/styles.css" not in target_files
        
        # 指定目标文件
        specified_files = ["OEBPS/chapter1.html"]
        target_files = await service._get_target_files(file_tree, specified_files)
        assert len(target_files) == 1
        assert "OEBPS/chapter1.html" in target_files
    
    # 测试报告生成
    @pytest.mark.asyncio
    async def test_generate_report(self, service):
        """测试报告生成"""
        task_id = "test_task_123"
        session_id = "test_session_123"
        
        # 模拟替换结果
        results = [
            ReplaceResult(
                file_path="chapter1.html",
                replacement_count=5,
                replacements=[
                    {
                        "position": 100,
                        "original": "old_text",
                        "replacement": "new_text",
                        "rule_description": "Replace old with new"
                    }
                ],
                original_size=1000,
                new_size=1020
            ),
            ReplaceResult(
                file_path="chapter2.html",
                replacement_count=3,
                replacements=[
                    {
                        "position": 200,
                        "original": "2023-12-25",
                        "replacement": "[DATE]",
                        "rule_description": "Replace dates"
                    }
                ],
                original_size=2000,
                new_size=1990
            )
        ]
        
        # 模拟报告服务
        with patch('backend.services.replace_service.report_service') as mock_report_service:
            mock_report_service.generate_html_report = AsyncMock(return_value="<html>Report</html>")
            
            report = await service._generate_report(task_id, session_id, results)
            
            assert report.task_id == task_id
            assert report.session_id == session_id
            assert report.total_files == 2
            assert report.total_replacements == 8
            assert len(report.results) == 2
            assert "chapter1.html" in report.file_stats
            assert "Replace old with new" in report.rule_stats
    
    # 测试错误处理
    @pytest.mark.asyncio
    async def test_apply_rule_invalid_regex(self, service):
        """测试无效正则表达式处理"""
        content = "Test content"
        rule = ReplaceRule(
            original="[invalid_regex",  # 无效的正则表达式
            replacement="replacement",
            description="Invalid regex rule",
            enabled=True,
            is_regex=True
        )
        
        # 应该返回原内容，不抛出异常
        new_content, count, replacements = await service._apply_rule(
            content, rule, case_sensitive=True, use_regex=True
        )
        
        assert new_content == content
        assert count == 0
        assert len(replacements) == 0
    
    @pytest.mark.asyncio
    async def test_parse_rules_invalid_format(self, service):
        """测试无效格式规则解析"""
        invalid_content = """invalid_line_without_arrow
another -> valid | rule
"""
        
        with pytest.raises(ValueError, match="规则解析错误"):
            await service._parse_rules(invalid_content)
    
    # 测试边缘情况
    @pytest.mark.asyncio
    async def test_empty_content_replacement(self, service, sample_rules):
        """测试空内容替换"""
        content = ""
        rule = sample_rules[0]
        
        new_content, count, replacements = await service._apply_rule(
            content, rule, case_sensitive=True, use_regex=False
        )
        
        assert new_content == ""
        assert count == 0
        assert len(replacements) == 0
    
    @pytest.mark.asyncio
    async def test_disabled_rule_validation(self, service):
        """测试禁用规则验证"""
        content = """# 包含禁用规则
old_text -> new_text | Enabled rule
other_text -> replacement | Disabled rule | disabled
"""
        
        result = await service.validate_rules(content)
        
        assert result.is_valid is True
        assert result.valid_rules == 2
        assert result.total_rules == 2
    
    @pytest.mark.asyncio
    async def test_special_characters_replacement(self, service):
        """测试特殊字符替换"""
        content = "Text with $pecial ch@racters and [brackets]"
        rule = ReplaceRule(
            original="$pecial",
            replacement="special",
            description="Fix special chars",
            enabled=True,
            is_regex=False
        )
        
        new_content, count, replacements = await service._apply_rule(
            content, rule, case_sensitive=True, use_regex=False
        )
        
        assert count == 1
        assert "special" in new_content
        assert "$pecial" not in new_content
    
    # 测试文件处理
    @pytest.mark.asyncio
    async def test_process_epub_file_success(self, service, sample_rules, sample_session):
        """测试EPUB文件处理成功"""
        file_path = "OEBPS/chapter1.html"
        
        # 模拟EPUB服务
        with patch('backend.services.replace_service.epub_service') as mock_epub_service:
            # 模拟文件内容
            mock_file_content = FileContent(
                path=file_path,
                content="<p>This is old_text in HTML</p>",
                encoding="utf-8",
                mime_type="text/html",
                size=35
            )
            mock_epub_service.get_file_content = AsyncMock(return_value=mock_file_content)
            mock_epub_service.save_file_content = AsyncMock()
            
            result = await service._process_epub_file(
                sample_session.session_id,
                file_path,
                sample_rules,
                case_sensitive=True,
                use_regex=False
            )
            
            assert result is not None
            assert result.file_path == file_path
            assert result.replacement_count > 0
            assert len(result.replacements) > 0
            
            # 验证保存被调用
            mock_epub_service.save_file_content.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_epub_file_no_replacements(self, service, sample_session):
        """测试EPUB文件无替换"""
        file_path = "OEBPS/chapter1.html"
        rules = [ReplaceRule(
            original="nonexistent",
            replacement="replacement",
            description="No match rule",
            enabled=True,
            is_regex=False
        )]
        
        with patch('backend.services.replace_service.epub_service') as mock_epub_service:
            mock_file_content = FileContent(
                path=file_path,
                content="<p>This is some HTML content</p>",
                encoding="utf-8",
                mime_type="text/html",
                size=34
            )
            mock_epub_service.get_file_content = AsyncMock(return_value=mock_file_content)
            
            result = await service._process_epub_file(
                sample_session.session_id,
                file_path,
                rules,
                case_sensitive=True,
                use_regex=False
            )
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_process_text_file_success(self, service, sample_rules, sample_text_session):
        """测试文本文件处理成功"""
        file_path = "test.txt"
        
        # 模拟文本服务
        with patch('backend.services.replace_service.text_service') as mock_text_service:
            # 模拟文件内容
            mock_file_content = FileContent(
                path=file_path,
                content="This is old_text in a text file",
                encoding="utf-8",
                mime_type="text/plain",
                size=33
            )
            mock_text_service.read_text_file = AsyncMock(return_value=mock_file_content)
            mock_text_service.write_text_file = AsyncMock()
            
            # 模拟处理结果
            from backend.services.text_service import TextReplacement
            mock_replacements = [
                TextReplacement(
                    position=8,
                    original_text="old_text",
                    replacement_text="new_text",
                    rule_description="Replace old with new"
                )
            ]
            mock_text_service.process_text_file = AsyncMock(
                return_value=("This is new_text in a text file", mock_replacements)
            )
            
            # 模拟文件路径
            with patch('pathlib.Path.exists', return_value=True):
                result = await service._process_text_file(
                    sample_text_session.session_id,
                    file_path,
                    sample_rules,
                    case_sensitive=True,
                    use_regex=False
                )
            
            assert result is not None
            assert result.file_path == file_path
            assert result.replacement_count == 1
            assert len(result.replacements) == 1
            
            # 验证文件被写入
            mock_text_service.write_text_file.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_text_file_not_found(self, service, sample_rules, sample_text_session):
        """测试文本文件不存在"""
        file_path = "nonexistent.txt"
        
        with patch('backend.services.replace_service.text_service') as mock_text_service:
            with patch('pathlib.Path.exists', return_value=False):
                with patch('pathlib.Path.glob', return_value=[]):
                    result = await service._process_text_file(
                        sample_text_session.session_id,
                        file_path,
                        sample_rules,
                        case_sensitive=True,
                        use_regex=False
                    )
            
            assert result is None
    
    # 测试批量替换启动
    @pytest.mark.asyncio
    async def test_start_batch_replace_success(self, service, sample_rules_content, sample_session):
        """测试批量替换启动成功"""
        session_id = sample_session.session_id
        
        # 模拟依赖服务
        with patch.object(service, 'run_task') as mock_run_task:
            mock_run_task.return_value = None
            
            task_id = await service.start_batch_replace(
                session_id=session_id,
                rules_content=sample_rules_content,
                case_sensitive=True,
                use_regex=False,
                target_files=None
            )
            
            assert task_id.startswith(f"replace_{session_id}_")
            assert task_id in service.progress_data
            
            progress = service.progress_data[task_id]
            assert progress.session_id == session_id
            assert progress.status == "starting"
            
            # 验证任务被启动
            mock_run_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_batch_replace_invalid_rules(self, service, sample_session):
        """测试批量替换无效规则"""
        invalid_rules = "invalid_rule_format"
        
        with pytest.raises(ValueError, match="规则验证失败"):
            await service.start_batch_replace(
                session_id=sample_session.session_id,
                rules_content=invalid_rules,
                case_sensitive=True,
                use_regex=False
            )
    
    @pytest.mark.asyncio
    async def test_execute_batch_replace_success(self, service, sample_rules, sample_session):
        """测试执行批量替换成功"""
        session_id = sample_session.session_id
        
        with patch.object(service, 'run_task') as mock_run_task:
            mock_run_task.return_value = None
            
            task_id = await service.execute_batch_replace(
                session_id=session_id,
                rules=sample_rules,
                case_sensitive=True,
                target_files=None
            )
            
            assert task_id in service.progress_data
            assert session_id in service.session_to_task
            assert service.session_to_task[session_id] == task_id
            
            progress = service.progress_data[task_id]
            assert progress.session_id == session_id
            assert progress.status == "running"
    
    # 测试进度流
    @pytest.mark.asyncio
    async def test_get_progress_stream(self, service):
        """测试获取进度流"""
        task_id = "test_task_123"
        
        # 初始化进度
        service.progress_data[task_id] = ReplaceProgress(
            session_id="test_session",
            task_id=task_id,
            status="running",
            total_files=10,
            processed_files=0,
            total_replacements=0,
            current_file="",
            progress_percentage=0.0,
            start_time=time.time(),
            estimated_remaining=0
        )
        
        # 创建进度流生成器
        progress_stream = service.get_progress_stream(task_id)
        
        # 模拟进度更新
        async def update_progress():
            await asyncio.sleep(0.1)
            await service._update_progress(task_id, processed_files=5, progress_percentage=50.0)
            await asyncio.sleep(0.1)
            await service._update_progress(task_id, status="completed", progress_percentage=100.0)
        
        # 启动更新任务
        update_task = asyncio.create_task(update_progress())
        
        # 收集进度数据，使用超时防止无限等待
        progress_updates = []
        try:
            async with asyncio.timeout(5):  # 5秒超时
                async for data in progress_stream:
                    progress_updates.append(data)
                    # 检查是否收到完成状态
                    if "completed" in data:
                        break
        except asyncio.TimeoutError:
            # 如果超时，确保任务被取消
            pass
        
        await update_task
        
        assert len(progress_updates) >= 1
        assert "data:" in progress_updates[0]
    
    # 测试复杂场景
    @pytest.mark.asyncio
    async def test_multiple_rules_application(self, service):
        """测试多规则应用"""
        content = "Hello world! Date: 2023-12-25. Another old_text here."
        
        rules = [
            ReplaceRule(
                original="Hello",
            replacement="Hi",
                description="Greeting change",
                enabled=True,
                is_regex=False
            ),
            ReplaceRule(
                original=r"\d{4}-\d{2}-\d{2}",
                replacement="[DATE]",
                description="Date replacement",
                enabled=True,
                is_regex=True
            ),
            ReplaceRule(
                original="old_text",
                replacement="new_text",
                description="Text update",
                enabled=True,
                is_regex=False
            )
        ]
        
        modified_content = content
        total_replacements = []
        
        for rule in rules:
            new_content, count, replacements = await service._apply_rule(
                modified_content, rule, case_sensitive=True, use_regex=rule.is_regex
            )
            if count > 0:
                modified_content = new_content
                total_replacements.extend(replacements)
        
        assert "Hi world!" in modified_content
        assert "[DATE]" in modified_content
        assert "new_text" in modified_content
        assert len(total_replacements) == 3
    
    @pytest.mark.asyncio
    async def test_concurrent_task_handling(self, service):
        """测试并发任务处理"""
        # 创建多个任务
        task_ids = []
        for i in range(3):
            task_id = f"test_task_{i}"
            task_ids.append(task_id)
            
            service.progress_data[task_id] = ReplaceProgress(
                session_id=f"session_{i}",
                task_id=task_id,
                status="running",
                total_files=10,
                processed_files=i * 2,
                total_replacements=i * 5,
                current_file=f"file_{i}.html",
                progress_percentage=i * 20.0,
                start_time=time.time(),
                estimated_remaining=60 - i * 20
            )
        
        # 验证所有任务都存在
        for task_id in task_ids:
            progress = await service.get_progress(task_id)
            assert progress is not None
            assert progress.task_id == task_id
        
        # 清理一个任务
        await service.cleanup_task_data(task_ids[0])
        
        # 验证清理结果
        assert await service.get_progress(task_ids[0]) is None
        assert await service.get_progress(task_ids[1]) is not None
        assert await service.get_progress(task_ids[2]) is not None
    
    # 测试错误恢复
    @pytest.mark.asyncio
    async def test_file_processing_error_recovery(self, service, sample_rules, sample_session):
        """测试文件处理错误恢复"""
        file_path = "OEBPS/chapter1.html"
        
        with patch('backend.services.replace_service.epub_service') as mock_epub_service:
            # 模拟文件读取错误
            mock_epub_service.get_file_content = AsyncMock(
                side_effect=Exception("File read error")
            )
            
            # 应该抛出异常
            with pytest.raises(Exception, match="File read error"):
                await service._process_epub_file(
                    sample_session.session_id,
                    file_path,
                    sample_rules,
                    case_sensitive=True,
                    use_regex=False
                )
    
    # 测试性能相关
    @pytest.mark.asyncio
    async def test_large_content_processing(self, service):
        """测试大内容处理"""
        # 创建大内容
        large_content = "old_text " * 10000  # 约70KB的内容
        
        rule = ReplaceRule(
            original="old_text",
            replacement="new_text",
            description="Large content test",
            enabled=True,
            is_regex=False
        )
        
        start_time = time.time()
        new_content, count, replacements = await service._apply_rule(
            large_content, rule, case_sensitive=True, use_regex=False
        )
        end_time = time.time()
        
        assert count == 10000
        assert len(replacements) == 10000
        assert "new_text" in new_content
        assert "old_text" not in new_content
        
        # 性能检查（应该在合理时间内完成）
        processing_time = end_time - start_time
        assert processing_time < 5.0  # 应该在5秒内完成
    
    @pytest.mark.asyncio
    async def test_regex_performance(self, service):
        """测试正则表达式性能"""
        content = "Date: 2023-12-25, another date 2024-01-01, and 2022-06-15" * 1000
        
        rule = ReplaceRule(
            original=r"\d{4}-\d{2}-\d{2}",
            replacement="[DATE]",
            description="Regex performance test",
            enabled=True,
            is_regex=True
        )
        
        start_time = time.time()
        new_content, count, replacements = await service._apply_rule(
            content, rule, case_sensitive=True, use_regex=True
        )
        end_time = time.time()
        
        assert count == 3000  # 3 dates * 1000 repetitions
        assert "[DATE]" in new_content
        
        # 性能检查
        processing_time = end_time - start_time
        assert processing_time < 3.0  # 应该在3秒内完成