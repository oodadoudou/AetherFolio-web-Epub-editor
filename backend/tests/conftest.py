"""pytest配置和fixtures"""

import asyncio
import os
import tempfile
import shutil
from pathlib import Path
from typing import AsyncGenerator, Generator
import pytest
import pytest_asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient

# 设置测试环境变量
os.environ["TESTING"] = "true"
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["DEBUG"] = "true"
os.environ["DISABLE_RATE_LIMIT"] = "true"

from backend.main import app
from backend.core.config import settings
from backend.services.session_service import session_service
from backend.services.epub_service import epub_service
from backend.core.logging import setup_logging

# 设置测试日志
setup_logging()


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def temp_dir() -> Generator[Path, None, None]:
    """创建临时目录"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture(scope="function")
def test_settings(temp_dir: Path):
    """测试配置"""
    # 备份原始设置
    original_upload_dir = settings.upload_dir
    original_session_dir = settings.session_dir
    original_temp_dir = settings.temp_dir
    original_reports_dir = settings.reports_dir
    
    # 设置测试目录
    settings.upload_dir = str(temp_dir / "uploads")
    settings.session_dir = str(temp_dir / "sessions")
    settings.temp_dir = str(temp_dir / "temp")
    settings.reports_dir = str(temp_dir / "reports")
    
    # 创建测试目录
    settings._ensure_directories()
    
    yield settings
    
    # 恢复原始设置
    settings.upload_dir = original_upload_dir
    settings.session_dir = original_session_dir
    settings.temp_dir = original_temp_dir
    settings.reports_dir = original_reports_dir


@pytest.fixture(scope="function")
def client(test_settings) -> TestClient:
    """测试客户端"""
    return TestClient(app)


@pytest_asyncio.fixture(scope="function")
async def async_client(test_settings) -> AsyncGenerator[AsyncClient, None]:
    """异步测试客户端"""
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture(scope="function")
def sample_epub_data() -> bytes:
    """示例EPUB数据"""
    # 创建一个简单的ZIP文件作为EPUB
    import zipfile
    import io
    
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zip_file:
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
        
        # 添加content.opf
        content_opf = '''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="2.0">
  <metadata>
    <dc:title xmlns:dc="http://purl.org/dc/elements/1.1/">Test Book</dc:title>
    <dc:creator xmlns:dc="http://purl.org/dc/elements/1.1/">Test Author</dc:creator>
    <dc:identifier xmlns:dc="http://purl.org/dc/elements/1.1/" id="BookId">test-book-id</dc:identifier>
    <dc:language xmlns:dc="http://purl.org/dc/elements/1.1/">en</dc:language>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="chapter1"/>
  </spine>
</package>'''
        zip_file.writestr('OEBPS/content.opf', content_opf)
        
        # 添加章节文件
        chapter1 = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Chapter 1</title>
</head>
<body>
    <h1>Chapter 1</h1>
    <p>This is a test chapter with some content to replace.</p>
    <p>Another paragraph with different text.</p>
</body>
</html>'''
        zip_file.writestr('OEBPS/chapter1.xhtml', chapter1)
        
        # 添加toc.ncx
        toc_ncx = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="test-book-id"/>
  </head>
  <docTitle>
    <text>Test Book</text>
  </docTitle>
  <navMap>
    <navPoint id="navpoint-1" playOrder="1">
      <navLabel>
        <text>Chapter 1</text>
      </navLabel>
      <content src="chapter1.xhtml"/>
    </navPoint>
  </navMap>
</ncx>'''
        zip_file.writestr('OEBPS/toc.ncx', toc_ncx)
    
    buffer.seek(0)
    return buffer.read()


@pytest.fixture(scope="function")
def sample_rules_data() -> str:
    """示例替换规则数据"""
    return """# 测试替换规则
test->TEST
content->内容
paragraph->段落"""