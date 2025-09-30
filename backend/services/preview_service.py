"""预览服务"""

import os
import re
from typing import Optional, Dict, Any
from pathlib import Path
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from jinja2 import Template
from fastapi import HTTPException

from services.base import CacheableService
from services.epub_service import epub_service
from db.models.schemas import FileType, ResponseStatus, ErrorCode
from core.config import settings
from core.security import security_validator


class PreviewService(CacheableService[str]):
    """预览服务"""
    
    def __init__(self):
        super().__init__("preview", cache_ttl=settings.preview_cache_timeout)
        self.preview_template = self._create_preview_template()
    
    async def _initialize(self):
        """初始化服务"""
        self.log_info("Preview service initialized")
    
    async def _cleanup(self):
        """清理服务"""
        await super()._cleanup()
    
    def _create_preview_template(self) -> Template:
        """创建预览模板"""
        template_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - AetherFolio 预览</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9f9f9;
        }
        .preview-header {
            background: #fff;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .preview-header h1 {
            margin: 0;
            color: #2c3e50;
            font-size: 1.5em;
        }
        .preview-meta {
            color: #666;
            font-size: 0.9em;
            margin-top: 5px;
        }
        .preview-content {
            background: #fff;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            min-height: 400px;
        }
        .preview-content img {
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .preview-content pre {
            background: #f4f4f4;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
            border-left: 4px solid #3498db;
        }
        .preview-content code {
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
        }
        .preview-content blockquote {
            border-left: 4px solid #3498db;
            margin: 0;
            padding-left: 20px;
            color: #666;
            font-style: italic;
        }
        .preview-content table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        .preview-content th,
        .preview-content td {
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }
        .preview-content th {
            background-color: #f8f9fa;
            font-weight: 600;
        }
        .error-message {
            background: #fee;
            color: #c33;
            padding: 15px;
            border-radius: 4px;
            border-left: 4px solid #e74c3c;
        }
        .file-info {
            background: #e8f4fd;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 20px;
            font-size: 0.9em;
        }
        /* EPUB特定样式 */
        .epub-content h1, .epub-content h2, .epub-content h3,
        .epub-content h4, .epub-content h5, .epub-content h6 {
            color: #2c3e50;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
        }
        .epub-content p {
            margin-bottom: 1em;
            text-align: justify;
        }
        .epub-content .chapter {
            page-break-before: always;
        }
        /* 响应式设计 */
        @media (max-width: 768px) {
            body {
                padding: 10px;
            }
            .preview-content {
                padding: 20px;
            }
        }
    </style>
    {% if custom_css %}
    <style>
        {{ custom_css }}
    </style>
    {% endif %}
</head>
<body>
    <div class="preview-header">
        <h1>{{ title }}</h1>
        <div class="preview-meta">
            文件路径: {{ file_path }} | 文件类型: {{ file_type }} | 文件大小: {{ file_size }}
        </div>
    </div>
    
    {% if error %}
    <div class="error-message">
        <strong>预览错误:</strong> {{ error }}
    </div>
    {% else %}
    <div class="file-info">
        <strong>文件信息:</strong> {{ file_info }}
    </div>
    
    <div class="preview-content epub-content">
        {{ content | safe }}
    </div>
    {% endif %}
    
    <script>
        // 处理相对链接
        document.addEventListener('DOMContentLoaded', function() {
            const links = document.querySelectorAll('a[href]');
            links.forEach(link => {
                const href = link.getAttribute('href');
                if (href && !href.startsWith('http') && !href.startsWith('#')) {
                    link.addEventListener('click', function(e) {
                        e.preventDefault();
                        alert('预览模式下无法跳转到其他文件: ' + href);
                    });
                }
            });
            
            // 处理图片加载错误
            const images = document.querySelectorAll('img');
            images.forEach(img => {
                img.addEventListener('error', function() {
                    this.style.display = 'none';
                    const placeholder = document.createElement('div');
                    placeholder.style.cssText = 'background:#f0f0f0;padding:20px;text-align:center;color:#666;border:1px dashed #ccc;';
                    placeholder.textContent = '图片加载失败: ' + this.src;
                    this.parentNode.insertBefore(placeholder, this);
                });
            });
        });
    </script>
</body>
</html>
        """
        return Template(template_content)
    
    async def generate_preview(
        self,
        session_id: str,
        file_path: str,
        base_url: Optional[str] = None
    ) -> str:
        """生成文件预览HTML
        
        Args:
            session_id: 会话ID
            file_path: 文件路径（可以是完整路径或文件名）
            base_url: 基础URL（用于处理相对路径）
            
        Returns:
            str: 预览HTML内容
        """
        # 生成缓存键
        cache_key = f"{session_id}:{file_path}"
        
        # 检查缓存
        cached_result = self._cache.get(cache_key)
        if cached_result:
            return cached_result
        
        async with self.performance_context("generate_preview", session_id=session_id, file_path=file_path):
            try:
                # 尝试解析文件路径 - 如果是简单文件名，需要查找完整路径
                resolved_file_path = await self._resolve_file_path(session_id, file_path)
                
                # 获取文件内容
                file_content = await epub_service.get_file_content(session_id, resolved_file_path)
                
                # 根据文件类型生成预览
                file_extension = Path(file_content.path).suffix.lower()
                mime_type = file_content.mime_type.lower() if file_content.mime_type else ""
                
                if (mime_type.startswith('text/html') or 
                    file_extension in ['.html', '.xhtml', '.htm']):
                    preview_html = await self._generate_html_preview(
                        file_content, session_id, base_url
                    )
                elif (mime_type.startswith('text/xml') or mime_type.startswith('application/xml') or
                      file_extension in ['.xml', '.opf', '.ncx']):
                    preview_html = await self._generate_xml_preview(file_content)
                elif (mime_type.startswith('text/css') or file_extension == '.css'):
                    preview_html = await self._generate_css_preview(file_content)
                elif (mime_type.startswith('text/') or file_extension in ['.txt', '.md']):
                    preview_html = await self._generate_text_preview(file_content)
                else:
                    preview_html = await self._generate_default_preview(file_content)
                
                # 缓存结果
                self._cache[cache_key] = preview_html
                
                return preview_html
                
            except Exception as e:
                self.log_error("Failed to generate preview", e, session_id=session_id, file_path=file_path)
                
                # 生成错误预览
                error_html = self.preview_template.render(
                    title="预览错误",
                    file_path=file_path,
                    file_type="未知",
                    file_size="未知",
                    file_info="无法获取文件信息",
                    error=f"生成预览失败: {str(e)}",
                    content="",
                    custom_css=""
                )
                
                return error_html
    
    async def _resolve_file_path(self, session_id: str, file_path: str) -> str:
        """解析文件路径，如果是简单文件名则查找完整路径"""
        try:
            # 如果已经是完整路径（包含目录分隔符），直接返回
            if '/' in file_path or '\\' in file_path:
                return file_path
            
            # 如果是简单文件名，需要在EPUB结构中查找
            from services.session_service import session_service
            session = await session_service.get_session(session_id)
            
            if not session:
                raise ValueError(f"Session not found: {session_id}")
            
            # 获取会话目录
            session_dir = session.get('extracted_path')
            if not session_dir:
                raise ValueError(f"No extracted path found for session: {session_id}")
            
            # 在EPUB目录中递归查找文件
            import os
            epub_dir = os.path.join(session_dir, "epub")
            
            for root, dirs, files in os.walk(epub_dir):
                if file_path in files:
                    # 返回相对于epub目录的路径
                    full_path = os.path.join(root, file_path)
                    relative_path = os.path.relpath(full_path, epub_dir)
                    # 统一使用正斜杠
                    return relative_path.replace('\\', '/')
            
            # 如果找不到文件，返回原始路径（让后续处理报错）
            self.log_warning(f"File not found in EPUB structure: {file_path}")
            return file_path
            
        except Exception as e:
            self.log_error(f"Failed to resolve file path: {file_path}", e)
            return file_path
    
    async def _generate_html_preview(
        self,
        file_content,
        session_id: str,
        base_url: Optional[str] = None
    ) -> str:
        """生成HTML文件预览"""
        try:
            # 解析HTML内容
            soup = BeautifulSoup(file_content.content, 'html.parser')
            
            # 提取标题
            title_elem = soup.find('title')
            title = title_elem.get_text() if title_elem else Path(file_content.path).name
            
            # 提取CSS样式
            custom_css = ""
            style_tags = soup.find_all('style')
            for style_tag in style_tags:
                if style_tag.string:
                    custom_css += style_tag.string + "\n"
            
            # 处理外部CSS链接
            link_tags = soup.find_all('link', rel='stylesheet')
            for link_tag in link_tags:
                href = link_tag.get('href')
                if href:
                    try:
                        # 尝试加载CSS文件
                        css_content = await self._load_css_file(session_id, href, file_content.path)
                        if css_content:
                            custom_css += css_content + "\n"
                    except Exception as e:
                        self.log_warning("Failed to load CSS file", href=href, error=str(e))
            
            # 提取body内容
            body = soup.find('body')
            if body:
                content = str(body)
                # 移除body标签，只保留内容
                content = re.sub(r'^<body[^>]*>', '', content)
                content = re.sub(r'</body>$', '', content)
            else:
                # 如果没有body标签，使用整个内容
                content = file_content.content
            
            # 处理图片路径
            content = await self._process_image_paths(content, session_id, file_content.path, base_url)
            
            # 处理链接
            content = self._process_links(content, base_url)
            
            # 生成文件信息
            file_info = f"HTML文档，编码: {file_content.encoding}，大小: {self._format_file_size(file_content.size)}"
            
            return self.preview_template.render(
                title=title,
                file_path=file_content.path,
                file_type="HTML",
                file_size=self._format_file_size(file_content.size),
                file_info=file_info,
                content=content,
                custom_css=custom_css,
                error=None
            )
            
        except Exception as e:
            self.log_error("Failed to generate HTML preview", e)
            raise
    
    async def _generate_xml_preview(self, file_content) -> str:
        """生成XML文件预览"""
        try:
            # 格式化XML内容
            from xml.dom import minidom
            
            try:
                dom = minidom.parseString(file_content.content)
                formatted_xml = dom.toprettyxml(indent="  ")
                # 移除空行
                formatted_xml = '\n'.join(line for line in formatted_xml.split('\n') if line.strip())
            except Exception:
                # 如果解析失败，使用原始内容
                formatted_xml = file_content.content
            
            # HTML转义
            import html
            escaped_content = html.escape(formatted_xml)
            
            content = f"<pre><code>{escaped_content}</code></pre>"
            
            file_info = f"XML文档，编码: {file_content.encoding}，大小: {self._format_file_size(file_content.size)}"
            
            return self.preview_template.render(
                title=Path(file_content.path).name,
                file_path=file_content.path,
                file_type="XML",
                file_size=self._format_file_size(file_content.size),
                file_info=file_info,
                content=content,
                custom_css="",
                error=None
            )
            
        except Exception as e:
            self.log_error("Failed to generate XML preview", e)
            raise
    
    async def _generate_css_preview(self, file_content) -> str:
        """生成CSS文件预览"""
        try:
            # HTML转义CSS内容
            import html
            escaped_content = html.escape(file_content.content)
            
            content = f"<pre><code>{escaped_content}</code></pre>"
            
            file_info = f"CSS样式表，编码: {file_content.encoding}，大小: {self._format_file_size(file_content.size)}"
            
            return self.preview_template.render(
                title=Path(file_content.path).name,
                file_path=file_content.path,
                file_type="CSS",
                file_size=self._format_file_size(file_content.size),
                file_info=file_info,
                content=content,
                custom_css="",
                error=None
            )
            
        except Exception as e:
            self.log_error("Failed to generate CSS preview", e)
            raise
    
    async def _generate_text_preview(self, file_content) -> str:
        """生成文本文件预览"""
        try:
            # HTML转义文本内容
            import html
            escaped_content = html.escape(file_content.content)
            
            # 保留换行
            escaped_content = escaped_content.replace('\n', '<br>')
            
            content = f"<div style='white-space: pre-wrap; font-family: monospace;'>{escaped_content}</div>"
            
            file_info = f"文本文件，编码: {file_content.encoding}，大小: {self._format_file_size(file_content.size)}"
            
            return self.preview_template.render(
                title=Path(file_content.path).name,
                file_path=file_content.path,
                file_type="文本",
                file_size=self._format_file_size(file_content.size),
                file_info=file_info,
                content=content,
                custom_css="",
                error=None
            )
            
        except Exception as e:
            self.log_error("Failed to generate text preview", e)
            raise
    
    async def _generate_default_preview(self, file_content) -> str:
        """生成默认文件预览"""
        try:
            # 尝试作为文本显示
            content_preview = file_content.content[:1000]  # 只显示前1000个字符
            if len(file_content.content) > 1000:
                content_preview += "\n\n... (内容已截断)"
            
            # HTML转义
            import html
            escaped_content = html.escape(content_preview)
            escaped_content = escaped_content.replace('\n', '<br>')
            
            content = f"<div style='white-space: pre-wrap; font-family: monospace; background: #f8f9fa; padding: 15px; border-radius: 4px;'>{escaped_content}</div>"
            
            file_info = f"二进制或未知格式文件，编码: {file_content.encoding}，大小: {self._format_file_size(file_content.size)}"
            
            return self.preview_template.render(
                title=Path(file_content.path).name,
                file_path=file_content.path,
                file_type="其他",
                file_size=self._format_file_size(file_content.size),
                file_info=file_info,
                content=content,
                custom_css="",
                error=None
            )
            
        except Exception as e:
            self.log_error("Failed to generate default preview", e)
            raise
    
    async def _load_css_file(self, session_id: str, css_path: str, current_file_path: str) -> Optional[str]:
        """加载CSS文件内容"""
        try:
            # 解析相对路径
            if not css_path.startswith('/'):
                current_dir = os.path.dirname(current_file_path)
                css_path = os.path.join(current_dir, css_path).replace('\\', '/')
            
            # 移除开头的斜杠，确保路径格式正确
            if css_path.startswith('/'):
                css_path = css_path[1:]
            
            # 获取CSS文件内容
            css_content = await epub_service.get_file_content(session_id, css_path)
            return css_content.content
            
        except Exception as e:
            self.log_warning("Failed to load CSS file", css_path=css_path, error=str(e))
            return None
    
    async def _process_image_paths(self, content: str, session_id: str, current_file_path: str, base_url: Optional[str]) -> str:
        """处理图片路径"""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            for img in soup.find_all('img'):
                src = img.get('src')
                if src and not src.startswith('http') and not src.startswith('data:'):
                    # 处理相对路径
                    if not src.startswith('/'):
                        current_dir = os.path.dirname(current_file_path)
                        img_path = os.path.join(current_dir, src).replace('\\', '/')
                    else:
                        img_path = src
                    
                    # 移除开头的斜杠，确保路径格式正确
                    if img_path.startswith('/'):
                        img_path = img_path[1:]
                    
                    # 构建二进制文件API URL
                    binary_url = f"/api/v1/files/binary?session_id={session_id}&file_path={img_path}"
                    img['src'] = binary_url
                    
                    # 添加加载错误处理属性
                    img['data-original-src'] = src
                    img['data-img-path'] = img_path
                    img['loading'] = 'lazy'
                    
                    # 添加CSS类用于样式控制
                    existing_class = img.get('class', [])
                    if isinstance(existing_class, str):
                        existing_class = existing_class.split()
                    existing_class.append('epub-image')
                    img['class'] = ' '.join(existing_class)
            
            return str(soup)
            
        except Exception as e:
            self.log_warning("Failed to process image paths", error=str(e))
            return content
    
    def _process_links(self, content: str, base_url: Optional[str]) -> str:
        """处理链接"""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # 跳过外部链接和锚点链接
                if href.startswith('http') or href.startswith('#'):
                    continue
                
                # 为内部链接添加提示
                link['title'] = f"预览模式下无法跳转: {href}"
                link['style'] = "color: #666; text-decoration: none; cursor: not-allowed;"
            
            return str(soup)
            
        except Exception as e:
            self.log_warning("Failed to process links", error=str(e))
            return content
    
    def _format_file_size(self, size: int) -> str:
        """格式化文件大小"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"
    
    async def clear_preview_cache(self, session_id: Optional[str] = None):
        """清理预览缓存
        
        Args:
            session_id: 会话ID，如果提供则只清理该会话的缓存
        """
        if session_id:
            # 清理特定会话的缓存
            pattern = f".*{session_id}.*"
            self.clear_cache(pattern)
        else:
            # 清理所有缓存
            self.clear_cache()
        
        self.log_info("Preview cache cleared", session_id=session_id)


# 创建全局服务实例
preview_service = PreviewService()


# 导出
__all__ = ["PreviewService", "preview_service"]