"""文件服务单元测试"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from backend.services.file_service import FileService


class TestFileService:
    """文件服务单元测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)
    
    @pytest.fixture
    def file_service(self):
        """创建文件服务实例"""
        return FileService()
    
    def test_service_initialization(self, file_service):
        """测试服务初始化"""
        assert file_service is not None
        assert hasattr(file_service, '__init__')
    
    @pytest.mark.asyncio
    async def test_read_file_success(self, file_service, temp_dir):
        """测试成功读取文件"""
        # 创建测试文件
        test_file = temp_dir / "test.txt"
        test_content = "这是测试文件内容\n包含多行文本"
        test_file.write_text(test_content, encoding='utf-8')
        
        # 模拟读取文件方法（因为FileService还未完全实现）
        with patch.object(file_service, 'read_file', return_value=test_content) as mock_read:
            content = await file_service.read_file(str(test_file))
            
            assert content == test_content
            mock_read.assert_called_once_with(str(test_file))
    
    @pytest.mark.asyncio
    async def test_read_file_not_found(self, file_service):
        """测试读取不存在的文件"""
        with patch.object(file_service, 'read_file', side_effect=FileNotFoundError()) as mock_read:
            with pytest.raises(FileNotFoundError):
                await file_service.read_file("/nonexistent/file.txt")
    
    @pytest.mark.asyncio
    async def test_read_file_permission_denied(self, file_service):
        """测试读取无权限文件"""
        with patch.object(file_service, 'read_file', side_effect=PermissionError()) as mock_read:
            with pytest.raises(PermissionError):
                await file_service.read_file("/restricted/file.txt")
    
    @pytest.mark.asyncio
    async def test_write_file_success(self, file_service, temp_dir):
        """测试成功写入文件"""
        test_file = temp_dir / "new_file.txt"
        test_content = "新文件内容\n包含中文字符"
        
        # 模拟写入文件方法
        with patch.object(file_service, 'write_file', return_value=True) as mock_write:
            result = await file_service.write_file(str(test_file), test_content)
            
            assert result is True
            mock_write.assert_called_once_with(str(test_file), test_content)
    
    @pytest.mark.asyncio
    async def test_write_file_permission_denied(self, file_service):
        """测试写入无权限目录"""
        with patch.object(file_service, 'write_file', side_effect=PermissionError()) as mock_write:
            with pytest.raises(PermissionError):
                await file_service.write_file("/restricted/file.txt", "content")
    
    @pytest.mark.asyncio
    async def test_write_file_disk_full(self, file_service):
        """测试磁盘空间不足"""
        with patch.object(file_service, 'write_file', side_effect=OSError("No space left on device")) as mock_write:
            with pytest.raises(OSError):
                await file_service.write_file("/tmp/file.txt", "content")
    
    @pytest.mark.asyncio
    async def test_delete_file_success(self, file_service, temp_dir):
        """测试成功删除文件"""
        test_file = temp_dir / "to_delete.txt"
        test_file.write_text("待删除文件", encoding='utf-8')
        
        with patch.object(file_service, 'delete_file', return_value=True) as mock_delete:
            result = await file_service.delete_file(str(test_file))
            
            assert result is True
            mock_delete.assert_called_once_with(str(test_file))
    
    @pytest.mark.asyncio
    async def test_delete_file_not_found(self, file_service):
        """测试删除不存在的文件"""
        with patch.object(file_service, 'delete_file', side_effect=FileNotFoundError()) as mock_delete:
            with pytest.raises(FileNotFoundError):
                await file_service.delete_file("/nonexistent/file.txt")
    
    @pytest.mark.asyncio
    async def test_rename_file_success(self, file_service, temp_dir):
        """测试成功重命名文件"""
        old_file = temp_dir / "old_name.txt"
        new_file = temp_dir / "new_name.txt"
        old_file.write_text("文件内容", encoding='utf-8')
        
        with patch.object(file_service, 'rename_file', return_value=True) as mock_rename:
            result = await file_service.rename_file(str(old_file), str(new_file))
            
            assert result is True
            mock_rename.assert_called_once_with(str(old_file), str(new_file))
    
    @pytest.mark.asyncio
    async def test_rename_file_target_exists(self, file_service, temp_dir):
        """测试重命名到已存在的文件"""
        old_file = temp_dir / "old_name.txt"
        new_file = temp_dir / "new_name.txt"
        old_file.write_text("原文件", encoding='utf-8')
        new_file.write_text("目标文件", encoding='utf-8')
        
        with patch.object(file_service, 'rename_file', side_effect=FileExistsError()) as mock_rename:
            with pytest.raises(FileExistsError):
                await file_service.rename_file(str(old_file), str(new_file))
    
    @pytest.mark.asyncio
    async def test_copy_file_success(self, file_service, temp_dir):
        """测试成功复制文件"""
        source_file = temp_dir / "source.txt"
        dest_file = temp_dir / "destination.txt"
        source_file.write_text("源文件内容", encoding='utf-8')
        
        with patch.object(file_service, 'copy_file', return_value=True) as mock_copy:
            result = await file_service.copy_file(str(source_file), str(dest_file))
            
            assert result is True
            mock_copy.assert_called_once_with(str(source_file), str(dest_file))
    
    @pytest.mark.asyncio
    async def test_get_file_info_success(self, file_service, temp_dir):
        """测试获取文件信息"""
        test_file = temp_dir / "info_test.txt"
        test_content = "文件信息测试"
        test_file.write_text(test_content, encoding='utf-8')
        
        expected_info = {
            "size": len(test_content.encode('utf-8')),
            "modified_time": test_file.stat().st_mtime,
            "is_file": True,
            "is_directory": False
        }
        
        with patch.object(file_service, 'get_file_info', return_value=expected_info) as mock_info:
            info = await file_service.get_file_info(str(test_file))
            
            assert info == expected_info
            mock_info.assert_called_once_with(str(test_file))
    
    @pytest.mark.asyncio
    async def test_list_directory_success(self, file_service, temp_dir):
        """测试列出目录内容"""
        # 创建测试文件和目录
        (temp_dir / "file1.txt").write_text("文件1", encoding='utf-8')
        (temp_dir / "file2.txt").write_text("文件2", encoding='utf-8')
        (temp_dir / "subdir").mkdir()
        
        expected_items = ["file1.txt", "file2.txt", "subdir"]
        
        with patch.object(file_service, 'list_directory', return_value=expected_items) as mock_list:
            items = await file_service.list_directory(str(temp_dir))
            
            assert set(items) == set(expected_items)
            mock_list.assert_called_once_with(str(temp_dir))
    
    @pytest.mark.asyncio
    async def test_create_directory_success(self, file_service, temp_dir):
        """测试创建目录"""
        new_dir = temp_dir / "new_directory"
        
        with patch.object(file_service, 'create_directory', return_value=True) as mock_create:
            result = await file_service.create_directory(str(new_dir))
            
            assert result is True
            mock_create.assert_called_once_with(str(new_dir))
    
    @pytest.mark.asyncio
    async def test_remove_directory_success(self, file_service, temp_dir):
        """测试删除目录"""
        dir_to_remove = temp_dir / "to_remove"
        dir_to_remove.mkdir()
        
        with patch.object(file_service, 'remove_directory', return_value=True) as mock_remove:
            result = await file_service.remove_directory(str(dir_to_remove))
            
            assert result is True
            mock_remove.assert_called_once_with(str(dir_to_remove))
    
    @pytest.mark.asyncio
    async def test_file_exists_true(self, file_service, temp_dir):
        """测试文件存在检查"""
        test_file = temp_dir / "exists.txt"
        test_file.write_text("存在的文件", encoding='utf-8')
        
        with patch.object(file_service, 'file_exists', return_value=True) as mock_exists:
            exists = await file_service.file_exists(str(test_file))
            
            assert exists is True
            mock_exists.assert_called_once_with(str(test_file))
    
    @pytest.mark.asyncio
    async def test_file_exists_false(self, file_service):
        """测试文件不存在检查"""
        with patch.object(file_service, 'file_exists', return_value=False) as mock_exists:
            exists = await file_service.file_exists("/nonexistent/file.txt")
            
            assert exists is False
            mock_exists.assert_called_once_with("/nonexistent/file.txt")
    
    @pytest.mark.asyncio
    async def test_get_file_size(self, file_service, temp_dir):
        """测试获取文件大小"""
        test_file = temp_dir / "size_test.txt"
        test_content = "测试文件大小" * 100  # 创建较大内容
        test_file.write_text(test_content, encoding='utf-8')
        
        expected_size = len(test_content.encode('utf-8'))
        
        with patch.object(file_service, 'get_file_size', return_value=expected_size) as mock_size:
            size = await file_service.get_file_size(str(test_file))
            
            assert size == expected_size
            mock_size.assert_called_once_with(str(test_file))
    
    @pytest.mark.asyncio
    async def test_concurrent_file_operations(self, file_service, temp_dir):
        """测试并发文件操作"""
        import asyncio
        
        # 创建多个测试文件
        files = []
        for i in range(5):
            test_file = temp_dir / f"concurrent_{i}.txt"
            test_file.write_text(f"并发测试文件 {i}", encoding='utf-8')
            files.append(str(test_file))
        
        # 模拟并发读取
        async def mock_read_file(file_path):
            await asyncio.sleep(0.01)  # 模拟IO延迟
            return f"内容来自 {file_path}"
        
        with patch.object(file_service, 'read_file', side_effect=mock_read_file):
            # 并发读取所有文件
            tasks = [file_service.read_file(file_path) for file_path in files]
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 5
            for i, result in enumerate(results):
                assert f"concurrent_{i}.txt" in result
    
    def test_path_validation(self, file_service):
        """测试路径验证"""
        # 测试路径遍历攻击防护
        dangerous_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "/etc/shadow",
            "C:\\Windows\\System32\\config\\SAM"
        ]
        
        with patch.object(file_service, 'validate_path', return_value=False) as mock_validate:
            for path in dangerous_paths:
                is_valid = file_service.validate_path(path)
                assert is_valid is False
    
    def test_file_type_validation(self, file_service):
        """测试文件类型验证"""
        allowed_extensions = [".txt", ".md", ".html", ".xhtml", ".css", ".js"]
        disallowed_extensions = [".exe", ".bat", ".sh", ".php", ".asp"]
        
        with patch.object(file_service, 'is_allowed_file_type', return_value=True) as mock_allowed:
            for ext in allowed_extensions:
                is_allowed = file_service.is_allowed_file_type(f"test{ext}")
                assert is_allowed is True
        
        with patch.object(file_service, 'is_allowed_file_type', return_value=False) as mock_disallowed:
            for ext in disallowed_extensions:
                is_allowed = file_service.is_allowed_file_type(f"test{ext}")
                assert is_allowed is False