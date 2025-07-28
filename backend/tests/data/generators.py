"""测试数据生成器"""

import os
import tempfile
import zipfile
from typing import Dict, List, Optional
from datetime import datetime
import uuid


class EPUBGenerator:
    """EPUB文件生成器"""
    
    @staticmethod
    def create_minimal_epub(output_path: str, title: str = "测试书籍", author: str = "测试作者") -> str:
        """创建最小的EPUB文件"""
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as epub:
            # mimetype文件
            epub.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
            
            # META-INF/container.xml
            container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''
            epub.writestr('META-INF/container.xml', container_xml)
            
            # OEBPS/content.opf
            content_opf = f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid" version="2.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
    <dc:title>{title}</dc:title>
    <dc:creator>{author}</dc:creator>
    <dc:identifier id="bookid">test-{uuid.uuid4()}</dc:identifier>
    <dc:language>zh</dc:language>
    <meta name="cover" content="cover-image"/>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="cover" href="cover.html" media-type="application/xhtml+xml"/>
    <item id="chapter1" href="chapter1.html" media-type="application/xhtml+xml"/>
    <item id="stylesheet" href="styles.css" media-type="text/css"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="cover"/>
    <itemref idref="chapter1"/>
  </spine>
</package>'''
            epub.writestr('OEBPS/content.opf', content_opf)
            
            # OEBPS/toc.ncx
            toc_ncx = f'''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="test-{uuid.uuid4()}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle>
    <text>{title}</text>
  </docTitle>
  <navMap>
    <navPoint id="navpoint-1" playOrder="1">
      <navLabel>
        <text>封面</text>
      </navLabel>
      <content src="cover.html"/>
    </navPoint>
    <navPoint id="navpoint-2" playOrder="2">
      <navLabel>
        <text>第一章</text>
      </navLabel>
      <content src="chapter1.html"/>
    </navPoint>
  </navMap>
</ncx>'''
            epub.writestr('OEBPS/toc.ncx', toc_ncx)
            
            # OEBPS/cover.html
            cover_html = f'''<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>封面</title>
    <link rel="stylesheet" type="text/css" href="styles.css"/>
</head>
<body>
    <div class="cover">
        <h1>{title}</h1>
        <h2>{author}</h2>
    </div>
</body>
</html>'''
            epub.writestr('OEBPS/cover.html', cover_html)
            
            # OEBPS/chapter1.html
            chapter1_html = '''<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>第一章</title>
    <link rel="stylesheet" type="text/css" href="styles.css"/>
</head>
<body>
    <h1>第一章：开始</h1>
    <p>这是第一章的内容。这里有一些旧文本需要替换。</p>
    <p>另一个段落，包含错误信息需要修正。</p>
    <p>测试段落，用于验证替换功能。</p>
</body>
</html>'''
            epub.writestr('OEBPS/chapter1.html', chapter1_html)
            
            # OEBPS/styles.css
            styles_css = '''body {
    font-family: serif;
    line-height: 1.6;
    margin: 2em;
}

h1, h2 {
    color: #333;
    text-align: center;
}

.cover {
    text-align: center;
    margin-top: 5em;
}

p {
    text-indent: 2em;
    margin: 1em 0;
}'''
            epub.writestr('OEBPS/styles.css', styles_css)
        
        return output_path
    
    @staticmethod
    def create_complex_epub(output_path: str, chapter_count: int = 5) -> str:
        """创建复杂的EPUB文件"""
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as epub:
            # 基础文件
            EPUBGenerator._add_basic_files(epub)
            
            # 生成多个章节
            manifest_items = []
            spine_items = []
            nav_points = []
            
            for i in range(1, chapter_count + 1):
                chapter_id = f"chapter{i}"
                chapter_file = f"chapter{i}.html"
                
                # 添加到manifest
                manifest_items.append(
                    f'    <item id="{chapter_id}" href="{chapter_file}" media-type="application/xhtml+xml"/>'
                )
                
                # 添加到spine
                spine_items.append(f'    <itemref idref="{chapter_id}"/>')
                
                # 添加到导航
                nav_points.append(f'''    <navPoint id="navpoint-{i}" playOrder="{i}">
      <navLabel>
        <text>第{i}章</text>
      </navLabel>
      <content src="{chapter_file}"/>
    </navPoint>''')
                
                # 创建章节内容
                chapter_html = f'''<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>第{i}章</title>
    <link rel="stylesheet" type="text/css" href="styles.css"/>
</head>
<body>
    <h1>第{i}章：章节标题{i}</h1>
    <p>这是第{i}章的内容。包含一些旧文本{i}。</p>
    <p>另一个段落{i}，包含错误信息{i}。</p>
    <p>测试段落{i}，用于验证替换功能。</p>
</body>
</html>'''
                epub.writestr(f'OEBPS/{chapter_file}', chapter_html)
            
            # 更新content.opf
            content_opf = f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid" version="2.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
    <dc:title>复杂测试书籍</dc:title>
    <dc:creator>测试作者</dc:creator>
    <dc:identifier id="bookid">complex-test-{uuid.uuid4()}</dc:identifier>
    <dc:language>zh</dc:language>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="stylesheet" href="styles.css" media-type="text/css"/>
{chr(10).join(manifest_items)}
  </manifest>
  <spine toc="ncx">
{chr(10).join(spine_items)}
  </spine>
</package>'''
            epub.writestr('OEBPS/content.opf', content_opf)
            
            # 更新toc.ncx
            toc_ncx = f'''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="complex-test-{uuid.uuid4()}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle>
    <text>复杂测试书籍</text>
  </docTitle>
  <navMap>
{chr(10).join(nav_points)}
  </navMap>
</ncx>'''
            epub.writestr('OEBPS/toc.ncx', toc_ncx)
        
        return output_path
    
    @staticmethod
    def _add_basic_files(epub: zipfile.ZipFile):
        """添加基础文件"""
        # mimetype
        epub.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
        
        # container.xml
        container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''
        epub.writestr('META-INF/container.xml', container_xml)
        
        # styles.css
        styles_css = '''body {
    font-family: serif;
    line-height: 1.6;
    margin: 2em;
}

h1, h2 {
    color: #333;
}

p {
    text-indent: 2em;
    margin: 1em 0;
}'''
        epub.writestr('OEBPS/styles.css', styles_css)


class RulesGenerator:
    """规则文件生成器"""
    
    @staticmethod
    def create_simple_rules(output_path: str) -> str:
        """创建简单规则文件"""
        rules = '''# 简单替换规则
旧文本 -> 新文本
错误 -> 正确
测试 -> 测试结果
'''
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rules)
        return output_path
    
    @staticmethod
    def create_complex_rules(output_path: str) -> str:
        """创建复杂规则文件"""
        rules = '''# 复杂替换规则
# 基本替换
旧文本 -> 新文本
错误信息 -> 正确信息

# 数字替换
旧文本1 -> 新文本1
旧文本2 -> 新文本2
旧文本3 -> 新文本3

# 特殊字符
"引号内容" -> "新引号内容"
<标签> -> <新标签>

# 长文本替换
这是一个很长的文本需要替换 -> 这是替换后的长文本

# 注释行（应该被忽略）
# 这是注释

# 空行测试

测试段落 -> 替换段落
'''
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rules)
        return output_path
    
    @staticmethod
    def create_invalid_rules(output_path: str) -> str:
        """创建无效规则文件"""
        rules = '''# 无效规则文件
无效规则行
另一个无效行
正确规则 -> 正确替换
又一个无效行
'''
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rules)
        return output_path


class SessionDataGenerator:
    """会话数据生成器"""
    
    @staticmethod
    def create_session_data(session_id: Optional[str] = None) -> Dict:
        """创建会话数据"""
        if session_id is None:
            session_id = f"test-session-{uuid.uuid4()}"
        
        return {
            "session_id": session_id,
            "metadata": {
                "original_filename": "test.epub",
                "file_size": 1024 * 50,  # 50KB
                "upload_time": datetime.now().isoformat(),
                "client_ip": "127.0.0.1",
                "extraction_path": f"/tmp/test/{session_id}",
                "file_count": 5,
                "book_metadata": {
                    "title": "测试书籍",
                    "author": "测试作者",
                    "language": "zh",
                    "publisher": "测试出版社",
                    "description": "这是一个测试书籍的描述"
                }
            },
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            "expires_at": datetime.now().isoformat()
        }
    
    @staticmethod
    def create_multiple_sessions(count: int) -> List[Dict]:
        """创建多个会话数据"""
        return [SessionDataGenerator.create_session_data() for _ in range(count)]


class FileContentGenerator:
    """文件内容生成器"""
    
    @staticmethod
    def create_html_content(title: str = "测试页面") -> str:
        """创建HTML内容"""
        return f'''<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{title}</title>
    <meta charset="utf-8"/>
    <link rel="stylesheet" type="text/css" href="styles.css"/>
</head>
<body>
    <h1>{title}</h1>
    <p>这是一个测试段落，包含一些旧文本。</p>
    <p>另一个段落，包含错误信息。</p>
    <p>测试段落，用于验证功能。</p>
    <div class="content">
        <h2>子标题</h2>
        <p>更多内容...</p>
    </div>
</body>
</html>'''
    
    @staticmethod
    def create_css_content() -> str:
        """创建CSS内容"""
        return '''/* 测试样式文件 */
body {
    font-family: serif;
    line-height: 1.6;
    margin: 2em;
    color: #333;
}

h1, h2 {
    color: #000;
    margin-bottom: 1em;
}

p {
    text-indent: 2em;
    margin: 1em 0;
}

.content {
    margin-top: 2em;
    padding: 1em;
    border: 1px solid #ccc;
}

/* 旧样式 */
.old-class {
    color: red;
}
'''
    
    @staticmethod
    def create_xml_content() -> str:
        """创建XML内容"""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<root>
    <metadata>
        <title>测试文档</title>
        <author>测试作者</author>
        <description>包含旧文本的描述</description>
    </metadata>
    <content>
        <chapter id="1">
            <title>第一章</title>
            <text>这里有一些错误信息需要修正。</text>
        </chapter>
        <chapter id="2">
            <title>第二章</title>
            <text>测试内容，用于验证功能。</text>
        </chapter>
    </content>
</root>'''