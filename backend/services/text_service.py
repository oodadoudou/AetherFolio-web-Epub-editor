"""文本文件服务"""

import os
import re
import html
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from backend.services.base import BaseService
from backend.models.schemas import (
    ReplaceRule, ReplaceResult, FileContent, FileType
)
from backend.core.config import settings
from backend.core.security import security_validator


@dataclass
class TextReplacement:
    """文本替换记录"""
    position: int
    original_text: str
    replacement_text: str
    rule_description: str


class TextService(BaseService):
    """文本文件服务"""
    
    def __init__(self):
        super().__init__("text")
    
    async def _initialize(self):
        """初始化服务"""
        await super()._initialize()
        self.log_info("Text service initialized")
    
    async def process_text_file(
        self,
        file_path: Path,
        content: str,
        rules: List[ReplaceRule]
    ) -> Tuple[str, List[TextReplacement]]:
        """处理文本文件
        
        Args:
            file_path: 文件路径
            content: 文件内容
            rules: 替换规则列表
            
        Returns:
            Tuple[str, List[TextReplacement]]: (修改后的内容, 替换记录列表)
        """
        async with self.performance_context("process_text_file"):
            try:
                modified_content = content
                all_replacements = []
                
                # 按段落分割处理
                paragraphs = content.split('\n\n')
                processed_paragraphs = []
                current_position = 0
                
                for paragraph_index, paragraph in enumerate(paragraphs):
                    if not paragraph.strip():
                        processed_paragraphs.append(paragraph)
                        current_position += len(paragraph) + 2  # +2 for \n\n
                        continue
                    
                    # 处理当前段落
                    processed_paragraph, paragraph_replacements = await self._process_paragraph(
                        paragraph, rules, current_position
                    )
                    
                    processed_paragraphs.append(processed_paragraph)
                    all_replacements.extend(paragraph_replacements)
                    
                    current_position += len(paragraph) + 2  # +2 for \n\n separator
                
                # 重新组合内容
                final_content = '\n\n'.join(processed_paragraphs)
                
                self.log_info(
                    "Text file processed",
                    file_path=str(file_path),
                    replacements_count=len(all_replacements)
                )
                
                return final_content, all_replacements
                
            except Exception as e:
                self.log_error("Failed to process text file", e, file_path=str(file_path))
                raise
    
    async def _process_paragraph(
        self,
        paragraph: str,
        rules: List[ReplaceRule],
        base_position: int
    ) -> Tuple[str, List[TextReplacement]]:
        """处理单个段落
        
        Args:
            paragraph: 段落内容
            rules: 替换规则列表
            base_position: 基础位置偏移
            
        Returns:
            Tuple[str, List[TextReplacement]]: (处理后的段落, 替换记录列表)
        """
        modified_paragraph = paragraph
        replacements = []
        
        for rule in rules:
            if not rule.enabled:
                continue
            
            # 应用规则
            new_paragraph, rule_replacements = await self._apply_rule_to_text(
                modified_paragraph, rule, base_position
            )
            
            if rule_replacements:
                modified_paragraph = new_paragraph
                replacements.extend(rule_replacements)
        
        return modified_paragraph, replacements
    
    async def _apply_rule_to_text(
        self,
        text: str,
        rule: ReplaceRule,
        base_position: int
    ) -> Tuple[str, List[TextReplacement]]:
        """对文本应用单个替换规则
        
        Args:
            text: 文本内容
            rule: 替换规则
            base_position: 基础位置偏移
            
        Returns:
            Tuple[str, List[TextReplacement]]: (处理后的文本, 替换记录列表)
        """
        replacements = []
        
        try:
            if rule.is_regex:
                # 正则表达式替换
                flags = 0 if rule.case_sensitive else re.IGNORECASE
                pattern = re.compile(rule.original, flags)
                
                def replace_func(match):
                    replacements.append(TextReplacement(
                        position=base_position + match.start(),
                        original_text=match.group(0),
                        replacement_text=rule.replacement,
            rule_description=rule.description or f"{rule.original} → {rule.replacement}"
                    ))
                    return rule.replacement
                
                new_text = pattern.sub(replace_func, text)
                
            else:
                # 普通文本替换
                search_text = rule.original
                replace_text = rule.replacement
                
                if not rule.case_sensitive:
                    # 不区分大小写的替换
                    pattern = re.compile(re.escape(search_text), re.IGNORECASE)
                    
                    def replace_func(match):
                        replacements.append(TextReplacement(
                            position=base_position + match.start(),
                            original_text=match.group(0),
                            replacement_text=replace_text,
                            rule_description=rule.description or f"{search_text} → {replace_text}"
                        ))
                        return replace_text
                    
                    new_text = pattern.sub(replace_func, text)
                else:
                    # 区分大小写的替换
                    new_text = ""
                    pos = 0
                    
                    while True:
                        index = text.find(search_text, pos)
                        if index == -1:
                            new_text += text[pos:]
                            break
                        
                        new_text += text[pos:index] + replace_text
                        replacements.append(TextReplacement(
                            position=base_position + index,
                            original_text=search_text,
                            replacement_text=replace_text,
                            rule_description=rule.description or f"{search_text} → {replace_text}"
                        ))
                        pos = index + len(search_text)
            
            return new_text, replacements
            
        except Exception as e:
            self.log_error("Failed to apply rule to text", e, rule=rule.model_dump())
            return text, []
    
    async def generate_text_report(
        self,
        file_path: str,
        original_content: str,
        modified_content: str,
        replacements: List[TextReplacement]
    ) -> List[Dict[str, str]]:
        """生成文本文件的替换报告
        
        Args:
            file_path: 文件路径
            original_content: 原始内容
            modified_content: 修改后的内容
            replacements: 替换记录列表
            
        Returns:
            List[Dict[str, str]]: 报告数据列表
        """
        async with self.performance_context("generate_text_report"):
            try:
                report_data = []
                
                # 按段落分组处理
                original_paragraphs = original_content.split('\n\n')
                modified_paragraphs = modified_content.split('\n\n')
                
                current_position = 0
                
                for i, (orig_para, mod_para) in enumerate(zip(original_paragraphs, modified_paragraphs)):
                    if orig_para != mod_para:
                        # 找到这个段落中的替换
                        para_replacements = [
                            r for r in replacements
                            if current_position <= r.position < current_position + len(orig_para)
                        ]
                        
                        if para_replacements:
                            # 生成高亮的HTML
                            original_html = html.escape(orig_para)
                            modified_html = html.escape(mod_para)
                            
                            # 为每个替换添加高亮
                            for replacement in para_replacements:
                                orig_esc = html.escape(replacement.original_text)
                                repl_esc = html.escape(replacement.replacement_text)
                                
                                original_html = original_html.replace(
                                    orig_esc,
                                    f'<span class="highlight">{orig_esc}</span>'
                                )
                                modified_html = modified_html.replace(
                                    repl_esc,
                                    f'<span class="highlight">{repl_esc}</span>'
                                )
                            
                            report_data.append({
                                'original': original_html.replace('\n', '<br>'),
                                'modified': modified_html.replace('\n', '<br>'),
                                'position': current_position
                            })
                    
                    current_position += len(orig_para) + 2  # +2 for \n\n
                
                return report_data
                
            except Exception as e:
                self.log_error("Failed to generate text report", e, file_path=file_path)
                return []
    
    async def validate_text_file(self, file_path: Path) -> bool:
        """验证文本文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否为有效的文本文件
        """
        try:
            # 检查文件扩展名
            if file_path.suffix.lower() not in ['.txt', '.text', '.md', '.markdown']:
                return False
            
            # 检查文件大小
            if file_path.stat().st_size > settings.max_file_size:
                return False
            
            # 尝试读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                f.read(1024)  # 读取前1KB检查是否为文本文件
            
            return True
            
        except Exception as e:
            self.log_error("Failed to validate text file", e, file_path=str(file_path))
            return False
    
    async def read_text_file(self, file_path: Path) -> FileContent:
        """读取文本文件内容
        
        Args:
            file_path: 文件路径
            
        Returns:
            FileContent: 文件内容对象
        """
        async with self.performance_context("read_text_file"):
            try:
                # 尝试不同的编码
                encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'latin1']
                content = None
                used_encoding = 'utf-8'
                
                for encoding in encodings:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            content = f.read()
                        used_encoding = encoding
                        break
                    except UnicodeDecodeError:
                        continue
                
                if content is None:
                    raise ValueError("无法解码文件内容")
                
                file_stat = file_path.stat()
                
                return FileContent(
                    path=str(file_path),
                    content=content,
                    encoding=used_encoding,
                    mime_type="text/plain",
                    size=file_stat.st_size,
                    last_modified=datetime.fromtimestamp(file_stat.st_mtime)
                )
                
            except Exception as e:
                self.log_error("Failed to read text file", e, file_path=str(file_path))
                raise
    
    async def write_text_file(self, file_path: Path, content: str, encoding: str = 'utf-8'):
        """写入文本文件
        
        Args:
            file_path: 文件路径
            content: 文件内容
            encoding: 编码格式
        """
        async with self.performance_context("write_text_file"):
            try:
                # 确保目录存在
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 写入文件
                with open(file_path, 'w', encoding=encoding) as f:
                    f.write(content)
                
                self.log_info("Text file written", file_path=str(file_path), size=len(content))
                
            except Exception as e:
                self.log_error("Failed to write text file", e, file_path=str(file_path))
                raise
    
    async def read_file_content(self, session_id: str) -> str:
        """读取会话文件内容
        
        Args:
            session_id: 会话ID
            
        Returns:
            str: 文件内容
        """
        async with self.performance_context("read_file_content"):
            try:
                # 构建会话目录路径
                session_dir = Path(settings.session_dir) / session_id
                
                # 查找文本文件
                text_extensions = ['.txt', '.text', '.md', '.markdown']
                found_file = None
                
                for ext in text_extensions:
                    for file_path in session_dir.glob(f"*{ext}"):
                        found_file = file_path
                        break
                    if found_file:
                        break
                
                if not found_file:
                    raise FileNotFoundError(f"No text file found in session {session_id}")
                
                # 读取文件内容
                file_content = await self.read_text_file(found_file)
                return file_content.content
                
            except Exception as e:
                self.log_error("Failed to read file content", e, session_id=session_id)
                raise
    
    async def write_file_content(self, session_id: str, content: str, filename: str = "content.txt"):
        """写入会话文件内容
        
        Args:
            session_id: 会话ID
            content: 文件内容
            filename: 文件名（可选）
        """
        async with self.performance_context("write_file_content"):
            try:
                # 构建会话目录路径
                session_dir = Path(settings.session_dir) / session_id
                
                # 查找现有文本文件或使用默认文件名
                text_extensions = ['.txt', '.text', '.md', '.markdown']
                target_file = None
                
                # 首先尝试找到现有文件
                for ext in text_extensions:
                    for file_path in session_dir.glob(f"*{ext}"):
                        target_file = file_path
                        break
                    if target_file:
                        break
                
                # 如果没有找到现有文件，使用默认文件名
                if not target_file:
                    target_file = session_dir / filename
                
                # 写入文件内容
                await self.write_text_file(target_file, content)
                
            except Exception as e:
                self.log_error("Failed to write file content", e, session_id=session_id)
                raise
    
    async def _cleanup(self):
        """清理服务资源"""
        # TextService 没有需要特别清理的资源
        # 调用父类的清理方法
        await super()._cleanup()


# 创建全局服务实例
text_service = TextService()


# 导出
__all__ = ["TextService", "text_service", "TextReplacement"]