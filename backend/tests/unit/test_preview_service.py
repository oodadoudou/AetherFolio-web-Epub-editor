"""预览服务单元测试"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from bs4 import BeautifulSoup

from backend.services.preview_service import PreviewService
from backend.models.schemas import FileType
from backend.core.config import settings


class TestPreviewService:
    """预览服务测试类"""
    
    @pytest.fixture
    async def service(self):
        """创建测试用的预览服务实例"""
        service = PreviewService()
        await service._initialize()
        yield service
        await service._cleanup()
    
    @pytest.fixture
    def mock_file_content(self):
        """模拟文件内容"""
        def create_mock_content(content, file_type=FileType.HTML, path="test.html", encoding="utf-8", size=None):
            mock = MagicMock()
            mock.content = content
            mock.type = file_type
            mock.path = path
            mock.encoding = encoding
            mock.size = size or len(content.encode(encoding))
            return mock
        return create_mock_content
    
    @pytest.fixture
    def sample_html_content(self):
        """示例HTML内容"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Test Chapter</title>
    <style>
        body { font-family: Arial, sans-serif; }
        .highlight { background-color: yellow; }
    </style>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <h1>Chapter 1</h1>
    <p>This is a <span class="highlight">test</span> paragraph.</p>
    <img src="images/test.jpg" alt="Test Image">
    <a href="chapter2.html">Next Chapter</a>
    <a href="https://example.com">External Link</a>
    <a href="#section1">Internal Link</a>
</body>
</html>
        """
    
    @pytest.fixture
    def sample_xml_content(self):
        """示例XML内容"""
        return """
<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
    <metadata>
        <dc:title>Test Book</dc:title>
        <dc:creator>Test Author</dc:creator>
    </metadata>
    <manifest>
        <item id="chapter1" href="chapter1.html" media-type="application/xhtml+xml"/>
    </manifest>
</package>
        """
    
    @pytest.fixture
    def sample_css_content(self):
        """示例CSS内容"""
        return """
body {
    font-family: 'Times New Roman', serif;
    line-height: 1.6;
    margin: 0;
    padding: 20px;
}

h1, h2, h3 {
    color: #333;
    margin-top: 1.5em;
}

p {
    text-align: justify;
    margin-bottom: 1em;
}
        """
    
    @pytest.fixture
    def sample_text_content(self):
        """示例文本内容"""
        return """This is a plain text file.
It contains multiple lines.
With some special characters: <>&"'
And unicode: 中文测试"""
    
    async def test_service_initialization(self, service):
        """测试服务初始化"""
        assert service.service_name == "preview"
        assert service.cache_ttl == settings.preview_cache_timeout
        assert service.preview_template is not None
    
    async def test_create_preview_template(self, service):
        """测试创建预览模板"""
        template = service._create_preview_template()
        
        # 测试模板渲染
        html = template.render(
            title="Test Title",
            file_path="test.html",
            file_type="HTML",
            file_size="1.2 KB",
            file_info="Test file info",
            content="<p>Test content</p>",
            custom_css="body { color: red; }",
            error=None
        )
        
        assert "Test Title" in html
        assert "test.html" in html
        assert "<p>Test content</p>" in html
        assert "body { color: red; }" in html
        assert "<!DOCTYPE html>" in html
    
    async def test_create_preview_template_with_error(self, service):
        """测试创建带错误的预览模板"""
        template = service._create_preview_template()
        
        html = template.render(
            title="Error Title",
            file_path="error.html",
            file_type="HTML",
            file_size="0 B",
            file_info="Error file",
            content="",
            custom_css="",
            error="Test error message"
        )
        
        assert "Error Title" in html
        assert "Test error message" in html
        assert "error-message" in html
    
    @patch('backend.services.preview_service.epub_service')
    async def test_generate_preview_html_success(self, mock_epub_service, service, mock_file_content, sample_html_content):
        """测试成功生成HTML预览"""
        session_id = "test-session-123"
        file_path = "chapter1.html"
        
        # 模拟EPUB服务
        mock_content = mock_file_content(sample_html_content, FileType.HTML, file_path)
        mock_epub_service.get_file_content.return_value = mock_content
        
        # 生成预览
        html = await service.generate_preview(session_id, file_path)
        
        assert "Test Chapter" in html
        assert "Chapter 1" in html
        assert "test paragraph" in html
        assert "font-family: Arial, sans-serif" in html
        assert "preview-content" in html
        
        mock_epub_service.get_file_content.assert_called_once_with(session_id, file_path)
    
    @patch('backend.services.preview_service.epub_service')
    async def test_generate_preview_xml_success(self, mock_epub_service, service, mock_file_content, sample_xml_content):
        """测试成功生成XML预览"""
        session_id = "test-session-123"
        file_path = "content.opf"
        
        # 模拟EPUB服务
        mock_content = mock_file_content(sample_xml_content, FileType.XML, file_path)
        mock_epub_service.get_file_content.return_value = mock_content
        
        # 生成预览
        html = await service.generate_preview(session_id, file_path)
        
        assert "content.opf" in html
        assert "&lt;package" in html  # XML应该被转义
        assert "Test Book" in html
        assert "<pre><code>" in html
        
        mock_epub_service.get_file_content.assert_called_once_with(session_id, file_path)
    
    @patch('backend.services.preview_service.epub_service')
    async def test_generate_preview_css_success(self, mock_epub_service, service, mock_file_content, sample_css_content):
        """测试成功生成CSS预览"""
        session_id = "test-session-123"
        file_path = "styles.css"
        
        # 模拟EPUB服务
        mock_content = mock_file_content(sample_css_content, FileType.CSS, file_path)
        mock_epub_service.get_file_content.return_value = mock_content
        
        # 生成预览
        html = await service.generate_preview(session_id, file_path)
        
        assert "styles.css" in html
        assert "font-family: 'Times New Roman'" in html
        assert "<pre><code>" in html
        assert "CSS样式表" in html
        
        mock_epub_service.get_file_content.assert_called_once_with(session_id, file_path)
    
    @patch('backend.services.preview_service.epub_service')
    async def test_generate_preview_text_success(self, mock_epub_service, service, mock_file_content, sample_text_content):
        """测试成功生成文本预览"""
        session_id = "test-session-123"
        file_path = "readme.txt"
        
        # 模拟EPUB服务
        mock_content = mock_file_content(sample_text_content, FileType.TEXT, file_path)
        mock_epub_service.get_file_content.return_value = mock_content
        
        # 生成预览
        html = await service.generate_preview(session_id, file_path)
        
        assert "readme.txt" in html
        assert "plain text file" in html
        assert "&lt;&gt;&amp;" in html  # 特殊字符应该被转义
        assert "中文测试" in html
        assert "<br>" in html  # 换行应该被转换
        assert "文本文件" in html
        
        mock_epub_service.get_file_content.assert_called_once_with(session_id, file_path)
    
    @patch('backend.services.preview_service.epub_service')
    async def test_generate_preview_default_success(self, mock_epub_service, service, mock_file_content):
        """测试成功生成默认预览"""
        session_id = "test-session-123"
        file_path = "unknown.bin"
        binary_content = "\x00\x01\x02\x03" + "A" * 2000  # 二进制内容
        
        # 模拟EPUB服务
        mock_content = mock_file_content(binary_content, FileType.UNKNOWN, file_path)
        mock_epub_service.get_file_content.return_value = mock_content
        
        # 生成预览
        html = await service.generate_preview(session_id, file_path)
        
        assert "unknown.bin" in html
        assert "内容已截断" in html  # 长内容应该被截断
        assert "二进制或未知格式文件" in html
        
        mock_epub_service.get_file_content.assert_called_once_with(session_id, file_path)
    
    @patch('backend.services.preview_service.epub_service')
    async def test_generate_preview_with_cache(self, mock_epub_service, service, mock_file_content, sample_html_content):
        """测试带缓存的预览生成"""
        session_id = "test-session-123"
        file_path = "chapter1.html"
        
        # 模拟EPUB服务
        mock_content = mock_file_content(sample_html_content, FileType.HTML, file_path)
        mock_epub_service.get_file_content.return_value = mock_content
        
        # 第一次生成预览
        html1 = await service.generate_preview(session_id, file_path)
        
        # 第二次生成预览（应该使用缓存）
        html2 = await service.generate_preview(session_id, file_path)
        
        assert html1 == html2
        # 第二次调用应该使用缓存，不再调用epub_service
        mock_epub_service.get_file_content.assert_called_once()
    
    @patch('backend.services.preview_service.epub_service')
    async def test_generate_preview_error_handling(self, mock_epub_service, service):
        """测试预览生成错误处理"""
        session_id = "test-session-123"
        file_path = "error.html"
        
        # 模拟EPUB服务抛出异常
        mock_epub_service.get_file_content.side_effect = Exception("File not found")
        
        # 生成预览
        html = await service.generate_preview(session_id, file_path)
        
        assert "预览错误" in html
        assert "File not found" in html
        assert "error-message" in html
    
    async def test_generate_html_preview_with_external_css(self, service, mock_file_content):
        """测试生成包含外部CSS的HTML预览"""
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Test</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <h1>Test</h1>
</body>
</html>
        """
        
        css_content = "h1 { color: blue; }"
        
        mock_content = mock_file_content(html_content, FileType.HTML, "test.html")
        
        with patch.object(service, '_load_css_file', return_value=css_content) as mock_load_css:
            html = await service._generate_html_preview(mock_content, "session-123")
        
        assert "color: blue" in html
        mock_load_css.assert_called_once_with("session-123", "styles.css", "test.html")
    
    async def test_generate_html_preview_no_body_tag(self, service, mock_file_content):
        """测试生成没有body标签的HTML预览"""
        html_content = """
<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<h1>No Body Tag</h1>
<p>Content without body</p>
</html>
        """
        
        mock_content = mock_file_content(html_content, FileType.HTML, "test.html")
        
        html = await service._generate_html_preview(mock_content, "session-123")
        
        assert "No Body Tag" in html
        assert "Content without body" in html
    
    async def test_generate_xml_preview_invalid_xml(self, service, mock_file_content):
        """测试生成无效XML的预览"""
        invalid_xml = "<invalid><unclosed>content"
        
        mock_content = mock_file_content(invalid_xml, FileType.XML, "invalid.xml")
        
        html = await service._generate_xml_preview(mock_content)
        
        assert "&lt;invalid&gt;&lt;unclosed&gt;content" in html
        assert "<pre><code>" in html
    
    @patch('backend.services.preview_service.epub_service')
    async def test_load_css_file_success(self, mock_epub_service, service, mock_file_content):
        """测试成功加载CSS文件"""
        session_id = "test-session"
        css_path = "styles.css"
        current_file_path = "chapter1.html"
        css_content = "body { color: red; }"
        
        # 模拟EPUB服务
        mock_content = mock_file_content(css_content, FileType.CSS, css_path)
        mock_epub_service.get_file_content.return_value = mock_content
        
        result = await service._load_css_file(session_id, css_path, current_file_path)
        
        assert result == css_content
        mock_epub_service.get_file_content.assert_called_once_with(session_id, css_path)
    
    @patch('backend.services.preview_service.epub_service')
    async def test_load_css_file_relative_path(self, mock_epub_service, service, mock_file_content):
        """测试加载相对路径的CSS文件"""
        session_id = "test-session"
        css_path = "../styles/main.css"
        current_file_path = "chapters/chapter1.html"
        css_content = "body { color: blue; }"
        
        # 模拟EPUB服务
        mock_content = mock_file_content(css_content, FileType.CSS, "styles/main.css")
        mock_epub_service.get_file_content.return_value = mock_content
        
        result = await service._load_css_file(session_id, css_path, current_file_path)
        
        assert result == css_content
        # 应该使用解析后的路径
        mock_epub_service.get_file_content.assert_called_once_with(session_id, "styles/main.css")
    
    @patch('backend.services.preview_service.epub_service')
    async def test_load_css_file_error(self, mock_epub_service, service):
        """测试加载CSS文件错误"""
        session_id = "test-session"
        css_path = "nonexistent.css"
        current_file_path = "chapter1.html"
        
        # 模拟EPUB服务抛出异常
        mock_epub_service.get_file_content.side_effect = Exception("File not found")
        
        result = await service._load_css_file(session_id, css_path, current_file_path)
        
        assert result is None
    
    async def test_process_image_paths_with_base_url(self, service):
        """测试处理带基础URL的图片路径"""
        content = '<img src="images/test.jpg" alt="Test"><img src="/absolute/path.jpg"><img src="http://example.com/external.jpg">'
        session_id = "test-session"
        current_file_path = "chapters/chapter1.html"
        base_url = "http://localhost:8000/"
        
        result = await service._process_image_paths(content, session_id, current_file_path, base_url)
        
        soup = BeautifulSoup(result, 'html.parser')
        images = soup.find_all('img')
        
        # 相对路径应该被转换为完整URL
        assert images[0]['src'] == "http://localhost:8000/chapters/images/test.jpg"
        # 绝对路径应该被转换为完整URL
        assert images[1]['src'] == "http://localhost:8000/absolute/path.jpg"
        # 外部URL应该保持不变
        assert images[2]['src'] == "http://example.com/external.jpg"
    
    async def test_process_image_paths_without_base_url(self, service):
        """测试处理没有基础URL的图片路径"""
        content = '<img src="images/test.jpg" alt="Test">'
        session_id = "test-session"
        current_file_path = "chapters/chapter1.html"
        
        result = await service._process_image_paths(content, session_id, current_file_path, None)
        
        soup = BeautifulSoup(result, 'html.parser')
        img = soup.find('img')
        
        # 应该使用占位符
        assert img['src'].startswith("data:image/svg+xml")
        assert "图片无法加载" in img['alt']
        assert "images/test.jpg" in img['title']
    
    async def test_process_image_paths_data_url(self, service):
        """测试处理data URL的图片"""
        content = '<img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==" alt="Test">'
        session_id = "test-session"
        current_file_path = "chapter1.html"
        
        result = await service._process_image_paths(content, session_id, current_file_path, None)
        
        soup = BeautifulSoup(result, 'html.parser')
        img = soup.find('img')
        
        # data URL应该保持不变
        assert img['src'].startswith("data:image/png;base64")
    
    async def test_process_image_paths_error_handling(self, service):
        """测试处理图片路径时的错误处理"""
        # 无效的HTML内容
        content = "<img src='test.jpg' invalid html>"
        session_id = "test-session"
        current_file_path = "chapter1.html"
        
        result = await service._process_image_paths(content, session_id, current_file_path, None)
        
        # 应该返回原始内容
        assert "test.jpg" in result
    
    async def test_process_links(self, service):
        """测试处理链接"""
        content = """
        <a href="chapter2.html">Next Chapter</a>
        <a href="https://example.com">External Link</a>
        <a href="#section1">Internal Link</a>
        <a href="mailto:test@example.com">Email</a>
        """
        
        result = service._process_links(content, "http://localhost:8000/")
        
        soup = BeautifulSoup(result, 'html.parser')
        links = soup.find_all('a')
        
        # 内部链接应该被禁用
        internal_link = links[0]
        assert "预览模式下无法跳转" in internal_link.get('title', '')
        assert "cursor: not-allowed" in internal_link.get('style', '')
        
        # 外部链接应该保持不变
        external_link = links[1]
        assert external_link['href'] == "https://example.com"
        
        # 锚点链接应该保持不变
        anchor_link = links[2]
        assert anchor_link['href'] == "#section1"
    
    async def test_process_links_error_handling(self, service):
        """测试处理链接时的错误处理"""
        # 无效的HTML内容
        content = "<a href='test.html' invalid html>"
        
        result = service._process_links(content, None)
        
        # 应该返回原始内容
        assert "test.html" in result
    
    async def test_format_file_size(self, service):
        """测试格式化文件大小"""
        assert service._format_file_size(500) == "500 B"
        assert service._format_file_size(1024) == "1.0 KB"
        assert service._format_file_size(1536) == "1.5 KB"
        assert service._format_file_size(1024 * 1024) == "1.0 MB"
        assert service._format_file_size(1024 * 1024 * 1.5) == "1.5 MB"
    
    async def test_clear_preview_cache_all(self, service):
        """测试清理所有预览缓存"""
        # 添加一些缓存数据
        service.set_cache("key1", "value1")
        service.set_cache("key2", "value2")
        
        # 清理所有缓存
        await service.clear_preview_cache()
        
        # 验证缓存被清理
        assert service.get_from_cache("key1") is None
        assert service.get_from_cache("key2") is None
    
    async def test_clear_preview_cache_by_session(self, service):
        """测试按会话清理预览缓存"""
        session_id = "test-session-123"
        
        # 添加一些缓存数据
        service.set_cache(f"preview_{session_id}_file1", "value1")
        service.set_cache(f"preview_{session_id}_file2", "value2")
        service.set_cache("preview_other_session_file1", "value3")
        
        # 清理特定会话的缓存
        await service.clear_preview_cache(session_id)
        
        # 验证只有指定会话的缓存被清理
        assert service.get_from_cache(f"preview_{session_id}_file1") is None
        assert service.get_from_cache(f"preview_{session_id}_file2") is None
        assert service.get_from_cache("preview_other_session_file1") is not None
    
    async def test_get_cache_key(self, service):
        """测试生成缓存键"""
        session_id = "test-session"
        file_path = "chapter1.html"
        base_url = "http://localhost:8000/"
        
        # 测试私有方法（如果存在）
        if hasattr(service, '_get_cache_key'):
            cache_key = service._get_cache_key(session_id, file_path, base_url)
            assert session_id in cache_key
            assert file_path in cache_key
            assert base_url in cache_key
    
    async def test_concurrent_preview_generation(self, service, mock_file_content, sample_html_content):
        """测试并发预览生成"""
        session_id = "test-session"
        
        async def generate_preview(file_path):
            with patch('backend.services.preview_service.epub_service') as mock_epub_service:
                mock_content = mock_file_content(sample_html_content, FileType.HTML, file_path)
                mock_epub_service.get_file_content.return_value = mock_content
                return await service.generate_preview(session_id, file_path)
        
        # 并发生成多个预览
        tasks = [generate_preview(f"chapter{i}.html") for i in range(3)]
        results = await asyncio.gather(*tasks)
        
        # 验证所有预览都生成成功
        assert len(results) == 3
        for result in results:
            assert "Test Chapter" in result
            assert "preview-content" in result
    
    async def test_service_cleanup(self, service):
        """测试服务清理"""
        # 添加一些缓存数据
        service.set_cache("test_key", "test_value")
        
        # 验证缓存存在
        assert service.get_from_cache("test_key") == "test_value"
        
        # 清理服务
        await service._cleanup()
        
        # 验证缓存被清理
        assert service.get_from_cache("test_key") is None
    
    async def test_performance_context(self, service, mock_file_content, sample_html_content):
        """测试性能上下文"""
        session_id = "test-session"
        file_path = "chapter1.html"
        
        with patch('backend.services.preview_service.epub_service') as mock_epub_service:
            mock_content = mock_file_content(sample_html_content, FileType.HTML, file_path)
            mock_epub_service.get_file_content.return_value = mock_content
            
            # 生成预览（应该使用性能上下文）
            html = await service.generate_preview(session_id, file_path)
            
            assert "Test Chapter" in html
    
    async def test_error_logging(self, service):
        """测试错误日志记录"""
        session_id = "test-session"
        file_path = "error.html"
        
        with patch('backend.services.preview_service.epub_service') as mock_epub_service, \
             patch.object(service, 'log_error') as mock_log_error:
            
            # 模拟EPUB服务抛出异常
            mock_epub_service.get_file_content.side_effect = Exception("Test error")
            
            # 生成预览
            html = await service.generate_preview(session_id, file_path)
            
            # 验证错误被记录
            mock_log_error.assert_called_once()
            assert "预览错误" in html
    
    async def test_warning_logging(self, service):
        """测试警告日志记录"""
        content = '<img src="test.jpg">'
        session_id = "test-session"
        current_file_path = "chapter1.html"
        
        with patch.object(service, 'log_warning') as mock_log_warning:
            # 模拟BeautifulSoup解析错误
            with patch('backend.services.preview_service.BeautifulSoup', side_effect=Exception("Parse error")):
                result = await service._process_image_paths(content, session_id, current_file_path, None)
            
            # 验证警告被记录
            mock_log_warning.assert_called_once()
            assert result == content  # 应该返回原始内容