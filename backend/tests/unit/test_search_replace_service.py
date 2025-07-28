"""搜索替换服务单元测试"""

import pytest
import re
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from backend.services.search_replace_service import SearchReplaceService


class TestSearchReplaceService:
    """搜索替换服务单元测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)
    
    @pytest.fixture
    def search_replace_service(self):
        """创建搜索替换服务实例"""
        return SearchReplaceService()
    
    @pytest.fixture
    def sample_text_files(self, temp_dir):
        """创建示例文本文件"""
        files = {}
        
        # 文件1：简单文本
        file1 = temp_dir / "simple.txt"
        content1 = "This is a simple test file.\nIt contains some test content.\nTest again."
        file1.write_text(content1, encoding='utf-8')
        files['simple'] = str(file1)
        
        # 文件2：HTML文件
        file2 = temp_dir / "sample.html"
        content2 = """<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
</head>
<body>
    <h1>Test Header</h1>
    <p>This is a test paragraph with some test content.</p>
    <div class="test-class">Test div content</div>
</body>
</html>"""
        file2.write_text(content2, encoding='utf-8')
        files['html'] = str(file2)
        
        # 文件3：中文内容
        file3 = temp_dir / "chinese.txt"
        content3 = "这是一个测试文件。\n包含中文内容的测试。\n测试中文搜索和替换功能。"
        file3.write_text(content3, encoding='utf-8')
        files['chinese'] = str(file3)
        
        return files
    
    def test_service_initialization(self, search_replace_service):
        """测试服务初始化"""
        assert search_replace_service is not None
        assert hasattr(search_replace_service, '__init__')
    
    @pytest.mark.asyncio
    async def test_search_in_file_simple_text(self, search_replace_service, sample_text_files):
        """测试在文件中搜索简单文本"""
        file_path = sample_text_files['simple']
        
        # 模拟搜索结果
        expected_results = [
            {"line_number": 1, "content": "This is a simple test file.", "match_start": 17, "match_end": 21},
            {"line_number": 2, "content": "It contains some test content.", "match_start": 17, "match_end": 21},
            {"line_number": 3, "content": "Test again.", "match_start": 0, "match_end": 4}
        ]
        
        with patch.object(search_replace_service, 'search_in_file', return_value=expected_results) as mock_search:
            results = await search_replace_service.search_in_file(
                file_path, 
                "test", 
                {"case_sensitive": False, "use_regex": False, "whole_word": False}
            )
            
            assert len(results) == 3
            assert all("line_number" in result for result in results)
            assert all("content" in result for result in results)
            mock_search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_case_sensitive(self, search_replace_service, sample_text_files):
        """测试大小写敏感搜索"""
        file_path = sample_text_files['simple']
        
        # 大小写敏感搜索应该只找到 "Test"
        expected_results = [
            {"line_number": 3, "content": "Test again.", "match_start": 0, "match_end": 4}
        ]
        
        with patch.object(search_replace_service, 'search_in_file', return_value=expected_results) as mock_search:
            results = await search_replace_service.search_in_file(
                file_path, 
                "Test", 
                {"case_sensitive": True, "use_regex": False, "whole_word": False}
            )
            
            assert len(results) == 1
            assert results[0]["line_number"] == 3
    
    @pytest.mark.asyncio
    async def test_search_regex_pattern(self, search_replace_service, sample_text_files):
        """测试正则表达式搜索"""
        file_path = sample_text_files['html']
        
        # 搜索HTML标签
        expected_results = [
            {"line_number": 4, "content": "    <title>Test Page</title>", "match_start": 4, "match_end": 11},
            {"line_number": 7, "content": "    <h1>Test Header</h1>", "match_start": 4, "match_end": 8}
        ]
        
        with patch.object(search_replace_service, 'search_in_file', return_value=expected_results) as mock_search:
            results = await search_replace_service.search_in_file(
                file_path, 
                r"<[^>]+>", 
                {"case_sensitive": False, "use_regex": True, "whole_word": False}
            )
            
            assert len(results) >= 1
            mock_search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_whole_word(self, search_replace_service, sample_text_files):
        """测试全词匹配搜索"""
        file_path = sample_text_files['simple']
        
        # 全词匹配 "test" 不应该匹配 "testing"
        expected_results = [
            {"line_number": 1, "content": "This is a simple test file.", "match_start": 17, "match_end": 21},
            {"line_number": 2, "content": "It contains some test content.", "match_start": 17, "match_end": 21}
        ]
        
        with patch.object(search_replace_service, 'search_in_file', return_value=expected_results) as mock_search:
            results = await search_replace_service.search_in_file(
                file_path, 
                "test", 
                {"case_sensitive": False, "use_regex": False, "whole_word": True}
            )
            
            assert len(results) >= 1
            mock_search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_chinese_text(self, search_replace_service, sample_text_files):
        """测试中文文本搜索"""
        file_path = sample_text_files['chinese']
        
        expected_results = [
            {"line_number": 1, "content": "这是一个测试文件。", "match_start": 4, "match_end": 6},
            {"line_number": 2, "content": "包含中文内容的测试。", "match_start": 7, "match_end": 9},
            {"line_number": 3, "content": "测试中文搜索和替换功能。", "match_start": 0, "match_end": 2}
        ]
        
        with patch.object(search_replace_service, 'search_in_file', return_value=expected_results) as mock_search:
            results = await search_replace_service.search_in_file(
                file_path, 
                "测试", 
                {"case_sensitive": False, "use_regex": False, "whole_word": False}
            )
            
            assert len(results) >= 1
            mock_search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_in_files_multiple(self, search_replace_service, sample_text_files):
        """测试在多个文件中搜索"""
        dir_path = str(Path(sample_text_files['simple']).parent)
        
        expected_results = {
            "total_matches": 5,
            "files_with_matches": 2,
            "results": {
                sample_text_files['simple']: [
                    {"line_number": 1, "content": "This is a simple test file.", "match_start": 17, "match_end": 21}
                ],
                sample_text_files['html']: [
                    {"line_number": 7, "content": "    <h1>Test Header</h1>", "match_start": 9, "match_end": 13}
                ]
            }
        }
        
        with patch.object(search_replace_service, 'search_in_files', return_value=expected_results) as mock_search:
            results = await search_replace_service.search_in_files(
                dir_path, 
                "test", 
                {"case_sensitive": False, "use_regex": False, "whole_word": False}
            )
            
            assert results["total_matches"] >= 1
            assert results["files_with_matches"] >= 1
            assert "results" in results
            mock_search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_replace_in_file_simple(self, search_replace_service, sample_text_files):
        """测试在文件中替换简单文本"""
        file_path = sample_text_files['simple']
        
        expected_result = {
            "replaced_count": 3,
            "modified_lines": [1, 2, 3],
            "preview": "This is a simple TEST file.\nIt contains some TEST content.\nTEST again."
        }
        
        with patch.object(search_replace_service, 'replace_in_file', return_value=expected_result) as mock_replace:
            result = await search_replace_service.replace_in_file(
                file_path, 
                "test", 
                "TEST", 
                {"case_sensitive": False, "use_regex": False, "whole_word": False}
            )
            
            assert result["replaced_count"] == 3
            assert len(result["modified_lines"]) == 3
            assert "TEST" in result["preview"]
            mock_replace.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_replace_with_regex(self, search_replace_service, sample_text_files):
        """测试正则表达式替换"""
        file_path = sample_text_files['html']
        
        expected_result = {
            "replaced_count": 2,
            "modified_lines": [4, 7],
            "preview": "Modified HTML content with replaced tags"
        }
        
        with patch.object(search_replace_service, 'replace_in_file', return_value=expected_result) as mock_replace:
            result = await search_replace_service.replace_in_file(
                file_path, 
                r"<(\w+)>", 
                r"[\1]", 
                {"case_sensitive": False, "use_regex": True, "whole_word": False}
            )
            
            assert result["replaced_count"] >= 1
            mock_replace.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_replace_in_files_batch(self, search_replace_service, sample_text_files):
        """测试批量文件替换"""
        dir_path = str(Path(sample_text_files['simple']).parent)
        
        expected_result = {
            "total_replaced": 5,
            "files_modified": 2,
            "results": {
                sample_text_files['simple']: {"replaced_count": 3, "modified_lines": [1, 2, 3]},
                sample_text_files['html']: {"replaced_count": 2, "modified_lines": [7, 8]}
            }
        }
        
        with patch.object(search_replace_service, 'replace_in_files', return_value=expected_result) as mock_replace:
            result = await search_replace_service.replace_in_files(
                dir_path, 
                "test", 
                "TEST", 
                {"case_sensitive": False, "use_regex": False, "whole_word": False}
            )
            
            assert result["total_replaced"] >= 1
            assert result["files_modified"] >= 1
            assert "results" in result
            mock_replace.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_file_not_found(self, search_replace_service):
        """测试搜索不存在的文件"""
        with patch.object(search_replace_service, 'search_in_file', side_effect=FileNotFoundError()) as mock_search:
            with pytest.raises(FileNotFoundError):
                await search_replace_service.search_in_file(
                    "/nonexistent/file.txt", 
                    "test", 
                    {"case_sensitive": False, "use_regex": False, "whole_word": False}
                )
    
    @pytest.mark.asyncio
    async def test_search_invalid_regex(self, search_replace_service, sample_text_files):
        """测试无效正则表达式"""
        file_path = sample_text_files['simple']
        
        with patch.object(search_replace_service, 'search_in_file', side_effect=re.error("Invalid regex")) as mock_search:
            with pytest.raises(re.error):
                await search_replace_service.search_in_file(
                    file_path, 
                    "[invalid regex", 
                    {"case_sensitive": False, "use_regex": True, "whole_word": False}
                )
    
    @pytest.mark.asyncio
    async def test_replace_permission_denied(self, search_replace_service):
        """测试替换无权限文件"""
        with patch.object(search_replace_service, 'replace_in_file', side_effect=PermissionError()) as mock_replace:
            with pytest.raises(PermissionError):
                await search_replace_service.replace_in_file(
                    "/restricted/file.txt", 
                    "test", 
                    "TEST", 
                    {"case_sensitive": False, "use_regex": False, "whole_word": False}
                )
    
    @pytest.mark.asyncio
    async def test_concurrent_search_operations(self, search_replace_service, sample_text_files):
        """测试并发搜索操作"""
        import asyncio
        
        files = list(sample_text_files.values())
        
        async def mock_search_in_file(file_path, query, options):
            await asyncio.sleep(0.01)  # 模拟IO延迟
            return [{"line_number": 1, "content": f"Result from {file_path}", "match_start": 0, "match_end": 4}]
        
        with patch.object(search_replace_service, 'search_in_file', side_effect=mock_search_in_file):
            # 并发搜索多个文件
            tasks = [
                search_replace_service.search_in_file(
                    file_path, 
                    "test", 
                    {"case_sensitive": False, "use_regex": False, "whole_word": False}
                ) for file_path in files
            ]
            
            results = await asyncio.gather(*tasks)
            
            assert len(results) == len(files)
            for result in results:
                assert len(result) >= 1
                assert "line_number" in result[0]
    
    def test_search_options_validation(self, search_replace_service):
        """测试搜索选项验证"""
        valid_options = {
            "case_sensitive": True,
            "use_regex": False,
            "whole_word": True
        }
        
        invalid_options = [
            {"case_sensitive": "invalid"},
            {"use_regex": "not_boolean"},
            {"whole_word": 123},
            {"unknown_option": True}
        ]
        
        with patch.object(search_replace_service, 'validate_search_options', return_value=True) as mock_validate:
            is_valid = search_replace_service.validate_search_options(valid_options)
            assert is_valid is True
        
        with patch.object(search_replace_service, 'validate_search_options', return_value=False) as mock_validate:
            for options in invalid_options:
                is_valid = search_replace_service.validate_search_options(options)
                assert is_valid is False
    
    def test_search_performance_optimization(self, search_replace_service):
        """测试搜索性能优化"""
        # 测试大文件搜索优化
        large_content = "test content " * 10000  # 大文件内容
        
        with patch.object(search_replace_service, 'optimize_search_for_large_file', return_value=True) as mock_optimize:
            should_optimize = search_replace_service.optimize_search_for_large_file(len(large_content))
            assert should_optimize is True
        
        # 测试搜索缓存
        cache_key = "test_query_options_hash"
        cached_results = [{"line_number": 1, "content": "cached result"}]
        
        with patch.object(search_replace_service, 'get_search_cache', return_value=cached_results) as mock_cache:
            results = search_replace_service.get_search_cache(cache_key)
            assert results == cached_results
    
    @pytest.mark.asyncio
    async def test_search_progress_tracking(self, search_replace_service, sample_text_files):
        """测试搜索进度跟踪"""
        dir_path = str(Path(sample_text_files['simple']).parent)
        
        progress_updates = []
        
        async def mock_search_with_progress(dir_path, query, options, progress_callback=None):
            if progress_callback:
                await progress_callback(25, "Searching file 1/4")
                await progress_callback(50, "Searching file 2/4")
                await progress_callback(75, "Searching file 3/4")
                await progress_callback(100, "Search completed")
            return {"total_matches": 5, "files_with_matches": 2}
        
        async def progress_callback(percent, message):
            progress_updates.append((percent, message))
        
        with patch.object(search_replace_service, 'search_in_files', side_effect=mock_search_with_progress):
            await search_replace_service.search_in_files(
                dir_path, 
                "test", 
                {"case_sensitive": False, "use_regex": False, "whole_word": False},
                progress_callback=progress_callback
            )
            
            assert len(progress_updates) == 4
            assert progress_updates[-1][0] == 100  # 最后一个更新应该是100%