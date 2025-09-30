"""安全验证模块"""

import os
import re
import hashlib
import mimetypes
import uuid
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from fastapi import HTTPException, UploadFile
from .exceptions import FileValidationError
from .logging import security_monitor


class SecurityValidator:
    """安全验证器"""
    
    # 允许的文件扩展名
    ALLOWED_EXTENSIONS = {
        '.epub', '.txt', '.html', '.htm', '.xhtml', '.xml',
        '.css', '.js', '.json', '.md', '.markdown'
    }
    
    # 危险的文件扩展名
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.scr', '.pif',
        '.vbs', '.js', '.jar', '.app', '.deb', '.rpm',
        '.dmg', '.pkg', '.msi', '.dll', '.so', '.dylib'
    }
    
    # 允许的MIME类型
    ALLOWED_MIME_TYPES = {
        'application/epub+zip',
        'text/plain',
        'text/html',
        'application/xhtml+xml',
        'text/xml',
        'application/xml',
        'text/css',
        'application/javascript',
        'application/json',
        'text/markdown'
    }
    
    # 危险的文件名模式
    DANGEROUS_PATTERNS = [
        r'\.\.\/',  # 路径遍历
        r'[<>:"|?*\\]',  # Windows非法字符（不包括反斜杠转义）
        r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$',  # Windows保留名
        r'^\.',  # 隐藏文件
    ]
    
    def __init__(self):
        self.max_file_size = 100 * 1024 * 1024  # 100MB
        self.max_filename_length = 255
    
    def sanitize_path(self, file_path: str, base_dir: str) -> str:
        """安全地组合文件路径和基础目录
        
        Args:
            file_path: 相对文件路径
            base_dir: 基础目录路径
        
        Returns:
            str: 安全的完整路径
        
        Raises:
            ValueError: 如果路径不安全
        """
        if not file_path or not base_dir:
            raise ValueError("文件路径和基础目录不能为空")
        
        # 规范化路径
        normalized_base_dir = os.path.normpath(base_dir)
        
        # 移除文件路径开头的斜杠（如果有）
        clean_file_path = file_path
        if clean_file_path.startswith(('/', '\\')):
            clean_file_path = clean_file_path[1:]
        
        # 组合路径并规范化
        full_path = os.path.join(normalized_base_dir, clean_file_path)
        full_path = os.path.normpath(full_path)
        
        # 确保最终路径在基础目录范围内
        try:
            # 获取绝对路径进行比较
            abs_full_path = os.path.abspath(full_path)
            abs_base_dir = os.path.abspath(normalized_base_dir)
            
            # 检查路径是否在基础目录内或其父目录内（允许合法的相对路径）
            # 但要确保不会访问到系统敏感目录
            if not (abs_full_path.startswith(abs_base_dir + os.sep) or abs_full_path == abs_base_dir):
                # 检查是否是合法的EPUB内部相对路径
                # 允许访问EPUB结构内的文件，如../Styles/stylesheet.css
                epub_base = os.path.dirname(abs_base_dir)
                if abs_full_path.startswith(epub_base + os.sep):
                    # 确保不会访问到系统敏感目录
                    sensitive_paths = ['/etc', '/bin', '/sbin', '/usr', '/var', '/root', '/home']
                    for sensitive in sensitive_paths:
                        if abs_full_path.startswith(sensitive):
                            raise ValueError(f"路径访问被拒绝: {file_path}")
                else:
                    raise ValueError(f"路径超出基础目录范围: {file_path}")
        except Exception as e:
            if "路径" in str(e):
                raise e
            raise ValueError(f"路径验证失败: {str(e)}")
        
        return full_path

    def validate_session_id(self, session_id: str) -> bool:
        """验证会话ID格式
        
        Args:
            session_id: 会话ID字符串
        
        Returns:
            bool: 是否为有效的UUID格式
        
        Raises:
            ValueError: 如果session_id格式无效
        """
        if not session_id:
            raise ValueError("会话ID不能为空")
        
        if not isinstance(session_id, str):
            raise ValueError("会话ID必须是字符串")
        
        # 检查长度（标准UUID长度为36字符，包含连字符）
        if len(session_id) != 36:
            raise ValueError("会话ID长度无效")
        
        try:
            # 尝试解析为UUID
            uuid_obj = uuid.UUID(session_id)
            # 确保是有效的UUID格式（版本4）
            if uuid_obj.version != 4:
                raise ValueError("会话ID必须是UUID版本4格式")
            return True
        except ValueError as e:
            if "会话ID" in str(e):
                raise e
            raise ValueError(f"无效的会话ID格式: {session_id}")
    
    def validate_filename(self, filename: str) -> Tuple[bool, List[str]]:
        """验证文件名
        
        Args:
            filename: 文件名
        
        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []
        
        # 检查文件名长度
        if len(filename) > self.max_filename_length:
            errors.append(f"文件名过长，最大长度为 {self.max_filename_length} 字符")
        
        # 检查文件名是否为空
        if not filename.strip():
            errors.append("文件名不能为空")
        
        # 检查危险模式
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                errors.append(f"文件名包含不安全字符或模式: {pattern}")
        
        # 检查文件扩展名
        file_ext = Path(filename).suffix.lower()
        if file_ext in self.DANGEROUS_EXTENSIONS:
            errors.append(f"不允许的文件类型: {file_ext}")
        
        if file_ext not in self.ALLOWED_EXTENSIONS:
            errors.append(f"不支持的文件类型: {file_ext}")
        
        return len(errors) == 0, errors
    
    def validate_file_size(self, file_size: int) -> Tuple[bool, List[str]]:
        """验证文件大小
        
        Args:
            file_size: 文件大小（字节）
        
        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []
        
        if file_size <= 0:
            errors.append("文件大小无效")
        elif file_size > self.max_file_size:
            max_mb = self.max_file_size / (1024 * 1024)
            errors.append(f"文件过大，最大允许 {max_mb:.1f}MB")
        
        return len(errors) == 0, errors
    
    def validate_mime_type(self, filename: str, content: bytes = None) -> Tuple[bool, List[str]]:
        """验证MIME类型
        
        Args:
            filename: 文件名
            content: 文件内容（可选）
        
        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []
        
        # 基于文件名猜测MIME类型
        mime_type, _ = mimetypes.guess_type(filename)
        
        if mime_type and mime_type not in self.ALLOWED_MIME_TYPES:
            errors.append(f"不允许的文件类型: {mime_type}")
        
        # 如果有文件内容，进行更详细的检查
        if content:
            # 检查文件头
            if filename.lower().endswith('.epub'):
                if not content.startswith(b'PK'):
                    errors.append("EPUB文件格式无效")
            elif filename.lower().endswith(('.txt', '.html', '.htm', '.xml', '.css', '.js')):
                try:
                    content.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        content.decode('gbk')
                    except UnicodeDecodeError:
                        errors.append("文本文件编码无效")
        
        return len(errors) == 0, errors
    
    def validate_file_content(self, content: bytes, filename: str) -> Tuple[bool, List[str]]:
        """验证文件内容
        
        Args:
            content: 文件内容
            filename: 文件名
        
        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []
        
        # 检查是否包含恶意脚本
        content_str = ""
        try:
            content_str = content.decode('utf-8', errors='ignore')
        except:
            try:
                content_str = content.decode('gbk', errors='ignore')
            except:
                pass
        
        if content_str:
            # 检查危险的脚本模式
            dangerous_patterns = [
                r'<script[^>]*>.*?</script>',
                r'javascript:',
                r'vbscript:',
                r'on\w+\s*=',
                r'eval\s*\(',
                r'document\.write',
                r'innerHTML\s*='
            ]
            
            for pattern in dangerous_patterns:
                if re.search(pattern, content_str, re.IGNORECASE | re.DOTALL):
                    errors.append(f"文件包含潜在的恶意脚本: {pattern}")
        
        return len(errors) == 0, errors
    
    def validate_upload_file(self, file: UploadFile) -> Tuple[bool, List[str]]:
        """验证上传文件
        
        Args:
            file: 上传的文件
        
        Returns:
            (是否有效, 错误信息列表)
        """
        all_errors = []
        
        # 验证文件名
        valid, errors = self.validate_filename(file.filename)
        all_errors.extend(errors)
        
        # 验证文件大小
        if hasattr(file, 'size') and file.size is not None:
            valid, errors = self.validate_file_size(file.size)
            all_errors.extend(errors)
        
        # 验证MIME类型
        valid, errors = self.validate_mime_type(file.filename)
        all_errors.extend(errors)
        
        return len(all_errors) == 0, all_errors


class FileValidator:
    """文件验证器"""
    
    def __init__(self):
        self.security_validator = SecurityValidator()
    
    def validate_file_path(self, file_path: str) -> bool:
        """验证文件路径是否安全
        
        Args:
            file_path: 文件路径
        
        Returns:
            是否安全
        """
        # 规范化路径
        normalized_path = os.path.normpath(file_path)
        
        # 检查路径遍历
        if '..' in normalized_path:
            security_monitor.log_security_violation(
                "path_traversal",
                f"尝试路径遍历: {file_path}"
            )
            return False
        
        # 检查绝对路径
        if os.path.isabs(normalized_path):
            security_monitor.log_security_violation(
                "absolute_path",
                f"尝试访问绝对路径: {file_path}"
            )
            return False
        
        return True
    
    def validate_file_operation(self, file_path: str, operation: str, user: str = "unknown") -> bool:
        """验证文件操作
        
        Args:
            file_path: 文件路径
            operation: 操作类型
            user: 用户
        
        Returns:
            是否允许操作
        """
        # 记录文件访问
        security_monitor.log_file_access(file_path, user, operation)
        
        # 验证路径安全性
        if not self.validate_file_path(file_path):
            return False
        
        # 验证文件名
        filename = os.path.basename(file_path)
        valid, errors = self.security_validator.validate_filename(filename)
        
        if not valid:
            security_monitor.log_security_violation(
                "invalid_filename",
                f"无效文件名: {filename}, 错误: {errors}"
            )
            return False
        
        return True
    
    def calculate_file_hash(self, content: bytes) -> str:
        """计算文件哈希值
        
        Args:
            content: 文件内容
        
        Returns:
            SHA256哈希值
        """
        return hashlib.sha256(content).hexdigest()
    
    def validate_epub_file(self, file) -> bool:
        """验证EPUB文件结构
        
        Args:
            file: 上传的文件对象
        
        Returns:
            是否为有效的EPUB文件
        """
        import zipfile
        import tempfile
        
        try:
            # 创建临时文件来保存上传的内容
            with tempfile.NamedTemporaryFile() as temp_file:
                # 重置文件指针到开头
                file.file.seek(0)
                content = file.file.read()
                file.file.seek(0)  # 重置回开头
                
                temp_file.write(content)
                temp_file.flush()
                
                # 尝试打开为ZIP文件
                with zipfile.ZipFile(temp_file.name, 'r') as zip_file:
                    # 检查必需的EPUB文件
                    required_files = [
                        'META-INF/container.xml',
                        'mimetype'
                    ]
                    
                    file_list = zip_file.namelist()
                    
                    # 检查必需文件是否存在
                    for required_file in required_files:
                        if required_file not in file_list:
                            return False
                    
                    # 检查mimetype文件内容
                    try:
                        mimetype_content = zip_file.read('mimetype').decode('utf-8').strip()
                        if mimetype_content != 'application/epub+zip':
                            return False
                    except:
                        return False
                    
                    # 检查container.xml文件
                    try:
                        container_content = zip_file.read('META-INF/container.xml').decode('utf-8')
                        # 简单检查是否包含rootfile元素
                        if 'rootfile' not in container_content.lower():
                            return False
                    except:
                        return False
                    
                    # 检查是否存在.opf文件（内容文档）
                    opf_files = [f for f in file_list if f.endswith('.opf')]
                    if not opf_files:
                        return False
                    
                    return True
                    
        except zipfile.BadZipFile:
            return False
        except Exception:
            return False
    
    def validate_and_sanitize_filename(self, filename: str) -> str:
        """验证并清理文件名
        
        Args:
            filename: 原始文件名
        
        Returns:
            清理后的文件名
        
        Raises:
            FileValidationError: 文件名无效
        """
        valid, errors = self.security_validator.validate_filename(filename)
        
        if not valid:
            raise FileValidationError(f"文件名验证失败: {'; '.join(errors)}")
        
        # 清理文件名
        sanitized = re.sub(r'[^\w\-_\.]', '_', filename)
        sanitized = re.sub(r'_+', '_', sanitized)
        
        return sanitized


# 创建全局验证器实例
security_validator = SecurityValidator()
file_validator = FileValidator()