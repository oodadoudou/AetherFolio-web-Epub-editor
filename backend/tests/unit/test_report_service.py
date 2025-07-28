"""报告服务单元测试"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from backend.services.report_service import ReportService


class TestReportService:
    """报告服务单元测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)
    
    @pytest.fixture
    def report_service(self):
        """创建报告服务实例"""
        return ReportService()
    
    def test_service_initialization(self, report_service):
        """测试服务初始化"""
        assert report_service is not None
        assert hasattr(report_service, '__init__')
    
    @pytest.mark.asyncio
    async def test_generate_html_report(self, report_service):
        """测试生成HTML报告"""
        from backend.models.schemas import BatchReplaceReport, ReplaceResult
        
        # 创建测试报告数据
        results = [
            ReplaceResult(
                file_path="test1.html",
                replacement_count=5,
                replacements=[
                    {
                        "original": "old_text",
                        "replacement": "new_text",
                        "position": 100
                    }
                ],
                original_size=1000,
                new_size=1020
            )
        ]
        
        report = BatchReplaceReport(
            task_id="test_task_123",
            session_id="test_session_123",
            total_files=1,
            total_replacements=5,
            results=results,
            file_stats={"test1.html": {"replacement_count": 5}},
            rule_stats={"old_text → new_text": 5},
            generated_at=datetime.now().timestamp()
        )
        
        html_content = await report_service.generate_html_report(
            report=report,
            source_filename="test.epub",
            style="green"
        )
        
        assert "<!DOCTYPE html>" in html_content
        assert "{{source_filename}}" in html_content or "test.epub" in html_content
        assert "old_text" in html_content
        assert "new_text" in html_content
    
    @pytest.mark.asyncio
    async def test_save_report(self, report_service, temp_dir):
        """测试保存报告到文件"""
        report_html = "<html><body><h1>Test Report</h1></body></html>"
        task_id = "test_task_123"
        
        # 测试保存报告
        saved_path = await report_service.save_report(
            report_html=report_html,
            task_id=task_id
        )
        
        assert saved_path.exists()
        assert saved_path.suffix == ".html"
        assert task_id in saved_path.name
        
        # 验证文件内容
        content = saved_path.read_text(encoding='utf-8')
        assert "Test Report" in content
    
    @pytest.mark.asyncio
    async def test_group_by_rules(self, report_service):
        """测试按规则分组功能"""
        from backend.models.schemas import ReplaceResult
        
        # 创建测试数据
        results = [
            ReplaceResult(
                file_path="test1.html",
                replacement_count=2,
                replacements=[
                    {
                        "original": "old_text",
                        "replacement": "new_text",
                        "position": 100
                    },
                    {
                        "original": "old_text",
                        "replacement": "new_text",
                        "position": 200
                    }
                ],
                original_size=1000,
                new_size=1020
            )
        ]
        
        rule_groups = await report_service._group_by_rules(results)
        
        assert len(rule_groups) == 1
        rule_key = "old_text → new_text"
        assert rule_key in rule_groups
        assert len(rule_groups[rule_key]['instances']) == 2
        assert rule_groups[rule_key]['original_text'] == "old_text"
        assert rule_groups[rule_key]['replacement_text'] == "new_text"
    
    @pytest.mark.asyncio
    async def test_get_template(self, report_service):
        """测试获取模板"""
        # 测试获取默认模板
        template_content = await report_service._get_template("green")
        
        assert "<!DOCTYPE html>" in template_content
        assert "{{source_filename}}" in template_content
        assert "{{rules_count}}" in template_content
        assert "{{total_instances}}" in template_content
    
    @pytest.mark.asyncio
    async def test_generate_rules_list(self, report_service):
        """测试生成规则列表"""
        sorted_rule_groups = [
            {
                "original_text": "old_text",
                "replacement_text": "new_text",
                "instances": [{}, {}]  # 2个实例
            },
            {
                "original_text": "another_old",
                "replacement_text": "another_new",
                "instances": [{}]  # 1个实例
            }
        ]
        
        rules_list = await report_service._generate_rules_list(sorted_rule_groups)
        
        assert "old_text" in rules_list
        assert "new_text" in rules_list
        assert "another_old" in rules_list
        assert "another_new" in rules_list
        assert "2 次" in rules_list
        assert "1 次" in rules_list
    
    @pytest.mark.asyncio
    async def test_generate_content_sections(self, report_service):
        """测试生成内容区域"""
        sorted_rule_groups = [
            {
                "original_text": "old_text",
                "replacement_text": "new_text",
                "instances": [
                    {
                        "original": "old_text in context",
                        "modified": "new_text in context",
                        "position": 100,
                        "file_path": "test.html"
                    }
                ]
            }
        ]
        
        content_sections = await report_service._generate_content_sections(sorted_rule_groups)
        
        assert "rule-group" in content_sections
        assert "old_text" in content_sections
        assert "new_text" in content_sections
        assert "old_text in context" in content_sections
        assert "new_text in context" in content_sections
    
    @pytest.mark.asyncio
    async def test_error_handling(self, report_service):
        """测试错误处理"""
        from backend.models.schemas import BatchReplaceReport
        
        # 测试无效的报告数据
        invalid_report = BatchReplaceReport(
            task_id="invalid_task",
            session_id="invalid_session",
            total_files=0,
            total_replacements=0,
            results=[],
            file_stats={},
            rule_stats={},
            generated_at=datetime.now().timestamp()
        )
        
        # 应该能够处理空的报告数据
        html_content = await report_service.generate_html_report(
            report=invalid_report,
            source_filename="empty.epub",
            style="green"
        )
        
        assert "<!DOCTYPE html>" in html_content
        assert "{{source_filename}}" in html_content or "empty.epub" in html_content