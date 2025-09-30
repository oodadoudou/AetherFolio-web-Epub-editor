"""文本文件服务"""

import os
import re
import html
import uuid
import hashlib
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timedelta

from services.base import BaseService
from db.models.schemas import (
    ReplaceRule, ReplaceResult, FileContent, UploadResponse, FileContentResponse,
    FileNode, BookMetadata, FileInfo
)
from db.models.file import FileType
from models.session import Session
from services.session_service import session_service
from fastapi import HTTPException
from core.config import settings
from core.security import security_validator


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
        # 初始化文件内容存储字典，用于存储每个会话的文件内容
        self.file_contents = {}
    
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
                # 使用统一的文本会话目录路径
                session_dir = Path("backend/sessions/text") / session_id
                
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
                # 使用统一的文本会话目录路径
                session_dir = Path("backend/sessions/text") / session_id
                
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
    
    async def process_upload(self, temp_file_path: str, filename: str, user_id: str) -> UploadResponse:
         """处理文本文件上传
         
         Args:
             temp_file_path: 临时文件路径
             filename: 文件名
             user_id: 用户ID
             
         Returns:
             UploadResponse: 上传响应
         """
         try:
             # 获取文件大小
             file_size = os.path.getsize(temp_file_path)
             
             # 读取文本文件
             file_path = Path(temp_file_path)
             file_content = await self.read_text_file(file_path)
             
             # 创建会话记录
             session_metadata = {
                 'original_filename': filename,
                 'file_size': file_size,
                 'title': Path(filename).stem,
                 'author': 'Unknown',
                 'language': 'zh',
                 'file_type': 'txt',
                 'file_count': 1
             }
             session_id = await session_service.create_session(session_metadata)
             
             # 获取会话目录路径
             session_dir = Path(session_service.get_session_dir(session_id, 'txt'))
             session_dir.mkdir(parents=True, exist_ok=True)
             
             # 将文件内容保存到会话目录
             target_file_path = session_dir / filename
             await self.write_text_file(target_file_path, file_content.content, file_content.encoding)
             
             # 将文件内容存储到内存中，用于跨文件搜索
             if session_id not in self.file_contents:
                 self.file_contents[session_id] = {}
             self.file_contents[session_id][filename] = file_content.content.encode('utf-8')
             
             # 创建简单的文件树（只有一个文件）
             file_node = FileNode(
                 name=filename,
                 path=filename,
                 type=FileType.FILE,
                 size=file_content.size
             )
             file_tree = [file_node]
             
             # 创建简单的元数据
             metadata = BookMetadata(
                 title=Path(filename).stem,
                 author="Unknown",
                 language="zh",
                 description="Text file upload"
             )
             
             # 创建文件信息
             
             # 计算文件校验和
             with open(temp_file_path, 'rb') as f:
                 file_hash = hashlib.sha256(f.read()).hexdigest()
             
             file_info = FileInfo(
                 filename=filename,
                 size=file_size,
                 type="TEXT",
                 mime_type="text/plain",
                 encoding=file_content.encoding,
                 checksum=file_hash
             )
             
             # 返回上传响应
             return UploadResponse(
                 session_id=session_id,
                 file_tree=file_tree,
                 metadata=metadata,
                 original_filename=filename,
                 file_size=file_size,
                 message="文本文件上传成功",
                 file_info=file_info
             )
             
         except HTTPException:
             raise
         except Exception as e:
             self.log_error("Failed to process upload", e, user_id=user_id)
             raise HTTPException(
                 status_code=500,
                 detail="处理上传失败"
             )
    
    async def get_file_content(self, session_id: str, file_path: str, user_id: str) -> FileContentResponse:
        """获取文件内容
        
        Args:
            session_id: 会话ID
            file_path: 文件路径
            user_id: 用户ID
            
        Returns:
            FileContentResponse: 文件内容响应
        """
        try:
            # 获取会话信息
            session = await session_service.get_session(session_id)
            if not session:
                raise HTTPException(status_code=404, detail="会话不存在")
            
            # 获取会话目录路径
            session_dir = Path(session_service.get_session_dir(session_id, 'txt'))
            target_file_path = session_dir / file_path
            
            # 检查文件是否存在
            if not target_file_path.exists():
                raise HTTPException(status_code=404, detail="文件不存在")
            
            # 读取文件内容
            file_content = await self.read_text_file(target_file_path)
            
            return FileContentResponse(
                content=file_content.content,
                encoding=file_content.encoding,
                size=file_content.size,
                mime_type=file_content.mime_type,
                last_modified=file_content.last_modified
            )
            
        except HTTPException:
            raise
        except Exception as e:
            self.log_error("Failed to get file content", e, session_id=session_id, user_id=user_id)
            raise HTTPException(
                status_code=500,
                detail="获取文件内容失败"
            )
    
    async def save_file_content(self, session_id: str, file_path: str, content: str, user_id: str) -> bool:
        """保存文件内容
        
        Args:
            session_id: 会话ID
            file_path: 文件路径
            content: 文件内容
            user_id: 用户ID
            
        Returns:
            bool: 是否保存成功
        """
        try:
            # 获取会话信息
            session = await session_service.get_session(session_id)
            if not session:
                raise HTTPException(status_code=404, detail="会话不存在")
            
            # 获取会话目录路径
            session_dir = Path(session_service.get_session_dir(session_id, 'txt'))
            target_file_path = session_dir / file_path
            
            # 确保目录存在
            target_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存文件内容
            await self.write_text_file(target_file_path, content)
            
            # 同时更新内存中的文件内容
            if session_id not in self.file_contents:
                self.file_contents[session_id] = {}
            self.file_contents[session_id][file_path] = content.encode('utf-8')
            
            self.log_info("File content saved to disk", session_id=session_id, file_path=file_path, size=len(content))
            
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            self.log_error("Failed to save file content", e, session_id=session_id, user_id=user_id)
            raise HTTPException(
                status_code=500,
                detail="保存文件内容失败"
            )
    
    async def _cleanup(self):
        """清理服务资源"""
        # TextService 没有需要特别清理的资源
        # 调用父类的清理方法
        await super()._cleanup()


# 创建全局服务实例
text_service = TextService()


# 导出
__all__ = ["TextService", "text_service", "TextReplacement"]