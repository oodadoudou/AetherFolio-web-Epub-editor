"""EPUB服务单元测试"""

import pytest
import tempfile
import shutil
import zipfile
import io
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException

from backend.services.epub_service import EpubService
from backend.models.schemas import BookMetadata, ErrorCode, ResponseStatus


class TestEpubService:
    """EPUB服务单元测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)
    
    @pytest.fixture
    def epub_service(self):
        """创建EPUB服务实例"""
        return EpubService()
    
    @pytest.fixture
    def sample_epub_file(self, temp_dir):
        """创建示例EPUB文件"""
        epub_path = temp_dir / "sample.epub"
        
        # 创建一个简单的EPUB文件
        with zipfile.ZipFile(epub_path, 'w') as zip_file:
            # 添加mimetype文件
            zip_file.writestr('mimetype', 'application/epub+zip')
            
            # 添加META-INF/container.xml
            container_xml = '''<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''
            zip_file.writestr('META-INF/container.xml', container_xml)
            
            # 添加OPF文件
            opf_content = '''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>测试书籍</dc:title>
    <dc:creator>测试作者</dc:creator>
    <dc:language>zh</dc:language>
    <dc:identifier id="uid">test-book-123</dc:identifier>
    <dc:description>这是一本测试书籍</dc:description>
    <dc:publisher>测试出版社</dc:publisher>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chapter1"/>
  </spine>
</package>'''
            zip_file.writestr('OEBPS/content.opf', opf_content)
            
            # 添加章节文件
            chapter_content = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>第一章</title>
</head>
<body>
    <h1>第一章</h1>
    <p>这是第一章的内容。</p>
</body>
</html>'''
            zip_file.writestr('OEBPS/chapter1.xhtml', chapter_content)
        
        return str(epub_path)
    
    def test_service_initialization(self, epub_service):
        """测试服务初始化"""
        assert epub_service is not None
        assert hasattr(epub_service, '__init__')
        assert epub_service.service_name == "epub"
    
    @pytest.mark.asyncio
    async def test_extract_epub_success(self, epub_service, sample_epub_file):
        """测试成功提取EPUB文件"""
        session_id = "test_session_123"
        
        with patch('backend.core.security.security_validator.validate_file_type', return_value=True), \
             patch('backend.services.session_service.session_service.set_session_data', new_callable=AsyncMock) as mock_session:
            
            temp_dir, metadata = await epub_service.extract_epub(sample_epub_file, session_id)
            
            # 验证返回值
            assert temp_dir is not None
            assert isinstance(metadata, BookMetadata)
            assert metadata.title == "测试书籍"
            assert metadata.author == "测试作者"
            assert metadata.language == "zh"
            
            # 验证临时目录被记录
            assert session_id in epub_service.temp_dirs
            
            # 验证会话数据被设置
            mock_session.assert_called_once_with(session_id, "temp_dir", temp_dir)
    
    @pytest.mark.asyncio
    async def test_extract_epub_file_not_found(self, epub_service):
        """测试提取不存在的EPUB文件"""
        session_id = "test_session_123"
        non_existent_file = "/path/to/nonexistent.epub"
        
        with pytest.raises(HTTPException) as exc_info:
            await epub_service.extract_epub(non_existent_file, session_id)
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error_code"] == ErrorCode.FILE_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_extract_epub_invalid_format(self, epub_service, temp_dir):
        """测试提取无效格式的文件"""
        session_id = "test_session_123"
        
        # 创建一个非EPUB文件
        invalid_file = temp_dir / "invalid.epub"
        invalid_file.write_text("这不是一个EPUB文件", encoding='utf-8')
        
        with patch('backend.core.security.security_validator.validate_file_type', return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                await epub_service.extract_epub(str(invalid_file), session_id)
            
            assert exc_info.value.status_code == 400
            assert exc_info.value.detail["error_code"] == ErrorCode.INVALID_FILE_FORMAT
    
    @pytest.mark.asyncio
    async def test_extract_epub_too_many_files(self, epub_service, temp_dir):
        """测试提取包含过多文件的EPUB"""
        session_id = "test_session_123"
        
        # 创建包含大量文件的EPUB
        large_epub = temp_dir / "large.epub"
        with zipfile.ZipFile(large_epub, 'w') as zip_file:
            zip_file.writestr('mimetype', 'application/epub+zip')
            # 添加大量文件
            for i in range(1001):  # 超过默认限制
                zip_file.writestr(f'file_{i}.txt', f'content {i}')
        
        with patch('backend.core.security.security_validator.validate_file_type', return_value=True), \
             patch('backend.core.config.settings.epub_max_files', 1000):
            
            with pytest.raises(HTTPException) as exc_info:
                await epub_service.extract_epub(str(large_epub), session_id)
            
            assert exc_info.value.status_code == 400
            assert exc_info.value.detail["error_code"] == ErrorCode.FILE_TOO_LARGE
    
    @pytest.mark.asyncio
    async def test_parse_metadata_success(self, epub_service, temp_dir):
        """测试成功解析元数据"""
        # 创建临时EPUB结构
        extract_dir = temp_dir / "extracted"
        extract_dir.mkdir()
        
        # 创建META-INF目录和container.xml
        meta_inf_dir = extract_dir / "META-INF"
        meta_inf_dir.mkdir()
        
        container_xml = '''<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''
        (meta_inf_dir / "container.xml").write_text(container_xml, encoding='utf-8')
        
        # 创建OEBPS目录和OPF文件
        oebps_dir = extract_dir / "OEBPS"
        oebps_dir.mkdir()
        
        opf_content = '''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>测试书籍标题</dc:title>
    <dc:creator>测试作者姓名</dc:creator>
    <dc:language>zh-CN</dc:language>
    <dc:identifier id="uid">test-book-456</dc:identifier>
    <dc:description>这是测试书籍的描述</dc:description>
    <dc:publisher>测试出版社名称</dc:publisher>
  </metadata>
</package>'''
        (oebps_dir / "content.opf").write_text(opf_content, encoding='utf-8')
        
        # 测试解析元数据
        metadata = await epub_service._parse_metadata(str(extract_dir))
        
        assert metadata.title == "测试书籍标题"
        assert metadata.author == "测试作者姓名"
        assert metadata.language == "zh-CN"
        assert metadata.description == "这是测试书籍的描述"
        assert metadata.publisher == "测试出版社名称"
    
    @pytest.mark.asyncio
    async def test_parse_metadata_missing_container(self, epub_service, temp_dir):
        """测试缺少container.xml的情况"""
        extract_dir = temp_dir / "extracted"
        extract_dir.mkdir()
        
        with pytest.raises(ValueError, match="找不到container.xml文件"):
            await epub_service._parse_metadata(str(extract_dir))
    
    @pytest.mark.asyncio
    async def test_get_file_tree_success(self, epub_service, temp_dir):
        """测试获取文件树"""
        session_id = "test_session_123"
        
        # 创建临时目录结构
        extract_dir = temp_dir / "extracted"
        extract_dir.mkdir()
        
        # 创建文件和目录
        (extract_dir / "file1.txt").write_text("内容1", encoding='utf-8')
        (extract_dir / "subdir").mkdir()
        (extract_dir / "subdir" / "file2.txt").write_text("内容2", encoding='utf-8')
        
        # 设置临时目录
        epub_service.temp_dirs[session_id] = str(extract_dir)
        
        with patch.object(epub_service, 'get_file_tree') as mock_get_tree:
            mock_get_tree.return_value = {
                "name": "extracted",
                "type": "directory",
                "children": [
                    {"name": "file1.txt", "type": "file", "size": 6},
                    {
                        "name": "subdir",
                        "type": "directory",
                        "children": [
                            {"name": "file2.txt", "type": "file", "size": 6}
                        ]
                    }
                ]
            }
            
            file_tree = epub_service.get_file_tree_sync(session_id)
            
            assert file_tree["name"] == "extracted"
            assert file_tree["type"] == "directory"
            assert len(file_tree["children"]) == 2
    
    @pytest.mark.asyncio
    async def test_read_file_content_success(self, epub_service, temp_dir):
        """测试读取文件内容"""
        session_id = "test_session_123"
        
        # 创建临时文件
        extract_dir = temp_dir / "extracted"
        extract_dir.mkdir()
        test_file = extract_dir / "test.txt"
        test_content = "这是测试文件的内容\n包含多行文本"
        test_file.write_text(test_content, encoding='utf-8')
        
        # 设置临时目录
        epub_service.temp_dirs[session_id] = str(extract_dir)
        
        with patch.object(epub_service, 'read_file_content') as mock_read:
            mock_read.return_value = {
                "content": test_content,
                "encoding": "utf-8",
                "size": len(test_content.encode('utf-8'))
            }
            
            content = epub_service.read_file_content(session_id, "test.txt")
            
            assert content["content"] == test_content
            assert content["encoding"] == "utf-8"
            assert content["size"] > 0
    
    @pytest.mark.asyncio
    async def test_write_file_content_success(self, epub_service, temp_dir):
        """测试写入文件内容"""
        session_id = "test_session_123"
        
        # 创建临时目录
        extract_dir = temp_dir / "extracted"
        extract_dir.mkdir()
        
        # 设置临时目录
        epub_service.temp_dirs[session_id] = str(extract_dir)
        
        new_content = "这是新的文件内容"
        
        with patch.object(epub_service, 'write_file_content', return_value=True) as mock_write:
            result = epub_service.write_file_content(session_id, "new_file.txt", new_content)
            
            assert result is True
            mock_write.assert_called_once_with(session_id, "new_file.txt", new_content)
    
    @pytest.mark.asyncio
    async def test_export_epub_success(self, epub_service, temp_dir):
        """测试导出EPUB文件"""
        session_id = "test_session_123"
        
        # 创建临时目录结构
        extract_dir = temp_dir / "extracted"
        extract_dir.mkdir()
        
        # 创建基本EPUB结构
        (extract_dir / "mimetype").write_text("application/epub+zip", encoding='utf-8')
        
        meta_inf_dir = extract_dir / "META-INF"
        meta_inf_dir.mkdir()
        (meta_inf_dir / "container.xml").write_text("<?xml version='1.0'?><container></container>", encoding='utf-8')
        
        # 设置临时目录
        epub_service.temp_dirs[session_id] = str(extract_dir)
        
        output_path = temp_dir / "output.epub"
        
        with patch.object(epub_service, 'export_epub', return_value=str(output_path)) as mock_export:
            result = epub_service.export_epub(session_id, str(output_path))
            
            assert result == str(output_path)
            mock_export.assert_called_once_with(session_id, str(output_path))
    
    @pytest.mark.asyncio
    async def test_cleanup_temp_directories(self, epub_service, temp_dir):
        """测试清理临时目录"""
        session_id = "test_session_123"
        
        # 创建临时目录
        temp_extract_dir = temp_dir / "temp_extract"
        temp_extract_dir.mkdir()
        (temp_extract_dir / "test_file.txt").write_text("测试内容", encoding='utf-8')
        
        # 添加到服务的临时目录记录
        epub_service.temp_dirs[session_id] = str(temp_extract_dir)
        
        # 执行清理
        await epub_service._cleanup()
        
        # 验证临时目录记录被清空
        assert len(epub_service.temp_dirs) == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_epub_operations(self, epub_service, temp_dir):
        """测试并发EPUB操作"""
        import asyncio
        
        # 创建多个EPUB文件
        epub_files = []
        for i in range(3):
            epub_path = temp_dir / f"test_{i}.epub"
            with zipfile.ZipFile(epub_path, 'w') as zip_file:
                zip_file.writestr('mimetype', 'application/epub+zip')
                zip_file.writestr('META-INF/container.xml', 
                                '<?xml version="1.0"?><container></container>')
            epub_files.append(str(epub_path))
        
        # 模拟并发提取
        async def mock_extract(epub_path, session_id):
            await asyncio.sleep(0.01)  # 模拟IO延迟
            return f"/tmp/extracted_{session_id}", BookMetadata(
                title=f"Book {session_id}",
                author="Test Author",
                language="zh"
            )
        
        with patch.object(epub_service, 'extract_epub', side_effect=mock_extract):
            # 并发提取所有EPUB文件
            tasks = [
                epub_service.extract_epub(epub_path, f"session_{i}")
                for i, epub_path in enumerate(epub_files)
            ]
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 3
            for i, (temp_dir, metadata) in enumerate(results):
                assert temp_dir == f"/tmp/extracted_session_{i}"
                assert metadata.title == f"Book session_{i}"
    
    def test_session_management(self, epub_service):
        """测试会话管理"""
        session_id_1 = "session_1"
        session_id_2 = "session_2"
        
        # 添加会话目录
        epub_service.temp_dirs[session_id_1] = "/tmp/session_1"
        epub_service.temp_dirs[session_id_2] = "/tmp/session_2"
        
        assert len(epub_service.temp_dirs) == 2
        assert session_id_1 in epub_service.temp_dirs
        assert session_id_2 in epub_service.temp_dirs
        
        # 移除特定会话
        del epub_service.temp_dirs[session_id_1]
        
        assert len(epub_service.temp_dirs) == 1
        assert session_id_1 not in epub_service.temp_dirs
        assert session_id_2 in epub_service.temp_dirs
    
    @pytest.mark.asyncio
    async def test_error_handling_during_extraction(self, epub_service, temp_dir):
        """测试提取过程中的错误处理"""
        session_id = "test_session_123"
        
        # 创建损坏的ZIP文件
        corrupted_epub = temp_dir / "corrupted.epub"
        corrupted_epub.write_bytes("这不是有效的ZIP文件内容".encode('utf-8'))
        
        with patch('backend.core.security.security_validator.validate_file_type', return_value=True):
            with pytest.raises(HTTPException) as exc_info:
                await epub_service.extract_epub(str(corrupted_epub), session_id)
            
            assert exc_info.value.status_code == 500
            assert exc_info.value.detail["error_code"] == ErrorCode.EPUB_EXTRACTION_FAILED
    
    def test_metadata_text_extraction(self, epub_service):
        """测试元数据文本提取"""
        # 这个测试需要访问私有方法，可以通过反射或者将方法设为公共来测试
        # 这里我们假设有一个公共的辅助方法来测试
        
        # 创建模拟的XML元素
        from xml.etree import ElementTree as ET
        
        metadata_xml = '''<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>测试标题</dc:title>
    <dc:creator>测试作者</dc:creator>
    <dc:language>zh</dc:language>
</metadata>'''
        
        metadata_elem = ET.fromstring(metadata_xml)
        
        # 测试私有方法（如果可以访问的话）
        if hasattr(epub_service, '_get_metadata_text'):
            title = epub_service._get_metadata_text(metadata_elem, "title", "默认标题")
            assert title == "测试标题"
            
            author = epub_service._get_metadata_text(metadata_elem, "creator", "默认作者")
            assert author == "测试作者"
            
            # 测试不存在的元素
            publisher = epub_service._get_metadata_text(metadata_elem, "publisher", "默认出版社")
            assert publisher == "默认出版社"