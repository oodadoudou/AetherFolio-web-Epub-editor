"""模型单元测试"""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from backend.models.session import Session, SessionStatus
from backend.models.epub import EpubFile, EpubMetadata
from backend.models.replace import ReplaceRule, ReplaceOptions, ReplaceTask, ReplaceProgress, ReplaceReport
from backend.models.file import FileNode, FileType


class TestSession:
    """Session模型测试"""
    
    def test_session_creation(self):
        """测试会话创建"""
        session = Session(
            session_id="test-session",
            epub_path="/path/to/test.epub",
            upload_time=datetime.now()
        )
        
        assert session.session_id == "test-session"
        assert session.epub_path == "/path/to/test.epub"
        assert session.status == SessionStatus.ACTIVE
        assert session.last_accessed is not None
        assert session.expires_at is not None
        assert not session.is_expired()
    
    def test_session_expiration(self):
        """测试会话过期"""
        # 创建已过期的会话
        past_time = datetime.now() - timedelta(hours=2)
        session = Session(
            session_id="expired-session",
            epub_path="/path/to/test.epub",
            upload_time=past_time,
            expires_at=past_time + timedelta(minutes=30)
        )
        
        assert session.is_expired()
    
    def test_session_extension(self):
        """测试会话延期"""
        session = Session(
            session_id="test-session",
            epub_path="/path/to/test.epub",
            upload_time=datetime.now()
        )
        
        original_expires_at = session.expires_at
        session.extend_session(hours=2)
        
        assert session.expires_at > original_expires_at
        assert session.last_accessed is not None
    
    def test_session_touch(self):
        """测试会话访问时间更新"""
        session = Session(
            session_id="test-session",
            epub_path="/path/to/test.epub",
            upload_time=datetime.now()
        )
        
        original_last_accessed = session.last_accessed
        session.touch()
        
        assert session.last_accessed > original_last_accessed
    
    def test_session_to_dict(self):
        """测试会话序列化"""
        session = Session(
            session_id="test-session",
            epub_path="/path/to/test.epub",
            upload_time=datetime.now()
        )
        
        session_dict = session.to_dict()
        
        assert session_dict["session_id"] == "test-session"
        assert session_dict["epub_path"] == "/path/to/test.epub"
        assert session_dict["status"] == "active"
        assert "upload_time" in session_dict
        assert "last_accessed" in session_dict
        assert "expires_at" in session_dict
        assert "is_expired" in session_dict


class TestEpubFile:
    """EpubFile模型测试"""
    
    def test_epub_metadata_creation(self):
        """测试EPUB元数据创建"""
        metadata = EpubMetadata(
            title="Test Book",
            author="Test Author",
            language="en",
            identifier="test-id-123"
        )
        
        assert metadata.title == "Test Book"
        assert metadata.author == "Test Author"
        assert metadata.language == "en"
        assert metadata.identifier == "test-id-123"
    
    def test_epub_file_creation(self):
        """测试EPUB文件创建"""
        metadata = EpubMetadata(
            title="Test Book",
            author="Test Author",
            language="en"
        )
        
        epub_file = EpubFile(
            file_path="/path/to/test.epub",
            metadata=metadata,
            file_size=1024000
        )
        
        assert epub_file.file_path == "/path/to/test.epub"
        assert epub_file.metadata.title == "Test Book"
        assert epub_file.file_size == 1024000
        assert epub_file.extracted_path is None
    
    def test_epub_file_to_dict(self):
        """测试EPUB文件序列化"""
        metadata = EpubMetadata(
            title="Test Book",
            author="Test Author",
            language="en"
        )
        
        epub_file = EpubFile(
            file_path="/path/to/test.epub",
            metadata=metadata,
            file_size=1024000,
            extracted_path="/path/to/extracted"
        )
        
        epub_dict = epub_file.to_dict()
        
        assert epub_dict["file_path"] == "/path/to/test.epub"
        assert epub_dict["file_size"] == 1024000
        assert epub_dict["extracted_path"] == "/path/to/extracted"
        assert "metadata" in epub_dict
        assert epub_dict["metadata"]["title"] == "Test Book"


class TestReplaceModels:
    """替换相关模型测试"""
    
    def test_replace_rule_creation(self):
        """测试替换规则创建"""
        rule = ReplaceRule(
            original="old text",
            replacement="new text",
            is_regex=False
        )
        
        assert rule.original == "old text"
        assert rule.replacement == "new text"
        assert rule.is_regex is False
    
    def test_replace_options_creation(self):
        """测试替换选项创建"""
        options = ReplaceOptions(
            case_sensitive=True,
            whole_word=False,
            use_regex=True
        )
        
        assert options.case_sensitive is True
        assert options.whole_word is False
        assert options.use_regex is True
    
    def test_replace_progress_creation(self):
        """测试替换进度创建"""
        progress = ReplaceProgress(
            status="running",
            percentage=50.0,
            current_file="chapter1.html",
            total_files=10,
            processed_files=5
        )
        
        assert progress.status == "running"
        assert progress.percentage == 50.0
        assert progress.current_file == "chapter1.html"
        assert progress.total_files == 10
        assert progress.processed_files == 5
    
    def test_replace_task_creation(self):
        """测试替换任务创建"""
        rules = [
            ReplaceRule(original="old", replacement="new", is_regex=False)
        ]
        options = ReplaceOptions(case_sensitive=True, whole_word=False, use_regex=False)
        
        task = ReplaceTask(
            task_id="task-123",
            session_id="session-456",
            rules=rules,
            options=options
        )
        
        assert task.task_id == "task-123"
        assert task.session_id == "session-456"
        assert len(task.rules) == 1
        assert task.rules[0].original == "old"
        assert task.options.case_sensitive is True
        assert task.status == "pending"
        assert task.created_at is not None
    
    def test_replace_report_creation(self):
        """测试替换报告创建"""
        from backend.models.replace import ReplaceFileResult
        
        summary = {
            "total_files": 10,
            "processed_files": 10,
            "total_replacements": 25,
            "status": "completed"
        }
        
        details = [
            ReplaceFileResult(
                file_path="chapter1.html",
                replacements_count=5,
                rules_applied=["rule1", "rule2"]
            )
        ]
        
        statistics = {
            "duration": 120.5,
            "files_per_second": 0.083,
            "replacements_per_file": 2.5
        }
        
        report = ReplaceReport(
            task_id="task-123",
            summary=summary,
            details=details,
            statistics=statistics
        )
        
        assert report.task_id == "task-123"
        assert report.summary["total_files"] == 10
        assert len(report.details) == 1
        assert report.details[0].file_path == "chapter1.html"
        assert report.details[0].replacements_count == 5
        assert report.statistics["duration"] == 120.5
        assert report.generated_at is not None


class TestFileNode:
    """FileNode模型测试"""
    
    def test_file_node_creation(self):
        """测试文件节点创建"""
        node = FileNode(
            name="test.html",
            path="/path/to/test.html",
            type=FileType.FILE,
            size=1024
        )
        
        assert node.name == "test.html"
        assert node.path == "/path/to/test.html"
        assert node.type == FileType.FILE
        assert node.size == 1024
        assert node.children == []
    
    def test_directory_node_creation(self):
        """测试目录节点创建"""
        file_node = FileNode(
            name="test.html",
            path="/path/to/test.html",
            type=FileType.FILE,
            size=1024
        )
        
        dir_node = FileNode(
            name="chapter",
            path="/path/to/chapter",
            type=FileType.DIRECTORY,
            children=[file_node]
        )
        
        assert dir_node.name == "chapter"
        assert dir_node.type == FileType.DIRECTORY
        assert len(dir_node.children) == 1
        assert dir_node.children[0].name == "test.html"
    
    def test_file_node_to_dict(self):
        """测试文件节点序列化"""
        file_node = FileNode(
            name="test.html",
            path="/path/to/test.html",
            type=FileType.FILE,
            size=1024
        )
        
        dir_node = FileNode(
            name="chapter",
            path="/path/to/chapter",
            type=FileType.DIRECTORY,
            children=[file_node]
        )
        
        dir_dict = dir_node.to_dict()
        
        assert dir_dict["name"] == "chapter"
        assert dir_dict["type"] == "directory"
        assert len(dir_dict["children"]) == 1
        assert dir_dict["children"][0]["name"] == "test.html"
        assert dir_dict["children"][0]["type"] == "file"
        assert dir_dict["children"][0]["size"] == 1024
    
    def test_file_node_add_child(self):
        """测试添加子节点"""
        parent = FileNode(
            name="parent",
            path="/path/to/parent",
            type=FileType.DIRECTORY
        )
        
        child = FileNode(
            name="child.html",
            path="/path/to/parent/child.html",
            type=FileType.FILE,
            size=512
        )
        
        parent.add_child(child)
        
        assert len(parent.children) == 1
        assert parent.children[0].name == "child.html"
    
    def test_file_node_find_child(self):
        """测试查找子节点"""
        parent = FileNode(
            name="parent",
            path="/path/to/parent",
            type=FileType.DIRECTORY
        )
        
        child1 = FileNode(
            name="child1.html",
            path="/path/to/parent/child1.html",
            type=FileType.FILE
        )
        
        child2 = FileNode(
            name="child2.html",
            path="/path/to/parent/child2.html",
            type=FileType.FILE
        )
        
        parent.add_child(child1)
        parent.add_child(child2)
        
        found_child = parent.find_child("child1.html")
        assert found_child is not None
        assert found_child.name == "child1.html"
        
        not_found = parent.find_child("nonexistent.html")
        assert not_found is None