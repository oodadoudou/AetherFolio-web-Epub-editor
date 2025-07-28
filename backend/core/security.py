"""安全验证模块"""

import os
import re
# import magic  # 暂时注释掉，避免依赖问题
import hashlib
from pathlib import Path
from typing import Optional, List, Tuple
from fastapi import HTTPException, UploadFile
from backend.core.config import settings
from backend.models.schemas import ErrorCode


class SecurityValidator:
    """安全验证器"""
    
    # 危险文件扩展名
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js',
        '.jar', '.app', '.deb', '.pkg', '.dmg', '.iso', '.msi', '.dll',
        '.so', '.dylib', '.sh', '.ps1', '.php', '.asp', '.jsp'
    }
    
    # 允许的文件名字符（包含中文、韩文、日文等Unicode字符）
    ALLOWED_FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9._\-\s\u4e00-\u9fff\uac00-\ud7af\u3040-\u309f\u30a0-\u30ff]+$')
    
    # 路径遍历模式
    PATH_TRAVERSAL_PATTERNS = [
        r'\.\.', 
        r'\\\.\.\\',
        r'/\.\./',
        r'%2e%2e',
        r'%252e%252e',
        r'%c0%ae%c0%ae',
        r'%c1%9c',
        r'\\',
        r'//',
        r'\.\./',
        r'\.\.\\\\',
        r'%2F%2E%2E%2F',
        r'%5C%2E%2E%5C',
        r'\\u002e\\u002e',
        r'\\x2e\\x2e',
        r'%u002e%u002e'
    ]
    
    @classmethod
    def validate_file_path(cls, file_path: str) -> bool:
        """验证文件路径安全性
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 路径是否安全
            
        Raises:
            SecurityError: 当路径不安全时抛出异常
        """
        from backend.core.exceptions import SecurityError
        
        if not file_path:
            raise SecurityError("File path cannot be empty")
            
        # 检查路径遍历攻击
        for pattern in cls.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, file_path, re.IGNORECASE):
                raise SecurityError(f"Path traversal attack detected: {file_path}")
        
        # 检查绝对路径（更严格的检测）
        if os.path.isabs(file_path) or file_path.startswith('/') or (len(file_path) > 1 and file_path[1] == ':'):
            raise SecurityError("Absolute paths are not allowed")
        
        # 检查Windows驱动器路径
        if re.match(r'^[a-zA-Z]:\\', file_path):
            raise SecurityError("Windows drive paths are not allowed")
            
        # 检查路径长度（更严格的限制）
        if len(file_path) > 255:
            raise SecurityError("File path too long")
        
        # 检查超长路径攻击
        if len(file_path) > 1000:
            raise SecurityError("Extremely long path detected - possible attack")
        
        # 检查重复路径遍历模式
        if file_path.count('../') > 20 or file_path.count('..\\') > 20:
            raise SecurityError("Excessive path traversal patterns detected")
            
        # 检查路径深度
        if file_path.count('/') > 10 or file_path.count('\\') > 10:
            raise SecurityError("File path depth exceeds limit")
        
        # 检查NULL字节注入
        if '\x00' in file_path or '\0' in file_path:
            raise SecurityError(f"NULL byte injection detected: {repr(file_path)}")
        
        # 检查危险字符
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*']
        for char in dangerous_chars:
            if char in file_path:
                raise SecurityError(f"File path contains dangerous character: {repr(char)}")
        
        # 检查Windows保留名称
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
        filename = os.path.basename(file_path).upper().split('.')[0]
        if filename in reserved_names:
            raise SecurityError(f"File name uses reserved name: {filename}")
            
        return True
    
    @classmethod
    def validate_filename(cls, filename: str) -> bool:
        """验证文件名安全性
        
        Args:
            filename: 文件名
            
        Returns:
            bool: 文件名是否安全
        """
        if not filename:
            return False
            
        # 检查文件名长度
        if len(filename) > 255:
            return False
            
        # 检查危险字符
        if not cls.ALLOWED_FILENAME_PATTERN.match(filename):
            return False
            
        # 检查危险扩展名
        file_ext = Path(filename).suffix.lower()
        if file_ext in cls.DANGEROUS_EXTENSIONS:
            return False
            
        # 检查保留名称（Windows）
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4',
            'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2',
            'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }
        
        name_without_ext = Path(filename).stem.upper()
        if name_without_ext in reserved_names:
            return False
            
        return True
    
    @classmethod
    def get_file_mime_type(cls, file_path: str) -> Optional[str]:
        """获取文件MIME类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            Optional[str]: MIME类型
        """
        try:
            # 基于文件扩展名的简单MIME类型检测
            file_ext = Path(file_path).suffix.lower()
            mime_map = {
                '.epub': 'application/epub+zip',
                '.txt': 'text/plain',
                '.pdf': 'application/pdf',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.html': 'text/html',
                '.css': 'text/css',
                '.xml': 'application/xml'
            }
            return mime_map.get(file_ext)
        except Exception:
            return None
    
    @classmethod
    def validate_file_type(cls, file_path: str, allowed_types: List[str]) -> bool:
        """验证文件类型
        
        Args:
            file_path: 文件路径
            allowed_types: 允许的MIME类型列表
            
        Returns:
            bool: 文件类型是否允许
        """
        # 简单的文件扩展名检查，替代magic库
        try:
            file_ext = Path(file_path).suffix.lower()
            if file_ext == '.epub' and 'application/epub+zip' in allowed_types:
                return True
            elif file_ext == '.txt' and 'text/plain' in allowed_types:
                return True
            elif file_ext == '.pdf' and 'application/pdf' in allowed_types:
                return True
            elif file_ext in ['.jpg', '.jpeg'] and 'image/jpeg' in allowed_types:
                return True
            elif file_ext == '.png' and 'image/png' in allowed_types:
                return True
            return False
        except Exception:
            return False
    
    @classmethod
    def validate_file_size(cls, file_path: str, max_size: int) -> bool:
        """验证文件大小
        
        Args:
            file_path: 文件路径
            max_size: 最大文件大小（字节）
            
        Returns:
            bool: 文件大小是否符合要求
        """
        try:
            file_size = os.path.getsize(file_path)
            return file_size <= max_size
        except OSError:
            return False
    
    @classmethod
    def calculate_file_hash(cls, file_path: str, algorithm: str = 'sha256') -> Optional[str]:
        """计算文件哈希值
        
        Args:
            file_path: 文件路径
            algorithm: 哈希算法
            
        Returns:
            Optional[str]: 文件哈希值
        """
        try:
            hash_obj = hashlib.new(algorithm)
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except Exception:
            return None
    
    @classmethod
    async def validate_upload_file(
        cls,
        file: UploadFile,
        allowed_types: Optional[List[str]] = None,
        max_size: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """验证上传文件
        
        Args:
            file: 上传的文件
            allowed_types: 允许的MIME类型
            max_size: 最大文件大小
            
        Returns:
            Tuple[bool, Optional[str]]: (是否有效, 错误信息)
        """
        if not file:
            return False, "文件不能为空"
            
        # 验证文件名
        if not cls.validate_filename(file.filename):
            return False, "文件名包含非法字符或格式不正确"
            
        # 验证文件大小
        if max_size is None:
            max_size = settings.max_file_size
            
        if file.size and file.size > max_size:
            return False, f"文件大小超过限制（{max_size / 1024 / 1024:.1f}MB）"
            
        # 验证文件类型
        if allowed_types is None:
            allowed_types = settings.allowed_file_types
            
        if file.content_type not in allowed_types:
            return False, f"不支持的文件类型：{file.content_type}"
            
        return True, None
    
    @classmethod
    def sanitize_path(cls, path: str, base_dir: str) -> str:
        """清理和规范化路径
        
        Args:
            path: 原始路径
            base_dir: 基础目录
            
        Returns:
            str: 清理后的安全路径
        """
        # 移除危险字符
        path = re.sub(r'[<>:"|?*]', '', path)
        
        # 规范化路径
        path = os.path.normpath(path)
        
        # 确保路径在基础目录内
        full_path = os.path.join(base_dir, path)
        full_path = os.path.abspath(full_path)
        base_dir = os.path.abspath(base_dir)
        
        if not full_path.startswith(base_dir):
            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "error_code": ErrorCode.INVALID_PATH,
                    "message": "路径不在允许的目录范围内"
                }
            )
            
        return full_path
    
    @classmethod
    def validate_session_id(cls, session_id: str) -> bool:
        """验证会话ID格式
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 会话ID是否有效
        """
        from backend.core.exceptions import SecurityError
        
        if session_id is None:
            raise SecurityError("Session ID cannot be None")
            
        if not isinstance(session_id, str):
            raise SecurityError("Session ID must be a string")
            
        if not session_id or session_id == "":
            raise SecurityError("Session ID cannot be empty")
            
        # 检查长度
        if len(session_id) < 16 or len(session_id) > 64:
            raise SecurityError("Session ID length must be between 16 and 64 characters")
            
        # 检查字符集（只允许字母数字和连字符）
        if not re.match(r'^[a-zA-Z0-9\-_]+$', session_id):
            raise SecurityError("Session ID contains invalid characters")
            
        return True
    
    def sanitize_filename(self, filename: str) -> str:
        """清理文件名"""
        import re
        import os
        
        # 移除路径分隔符
        filename = os.path.basename(filename)
        
        # 替换空格为下划线
        filename = filename.replace(' ', '_')
        
        # 移除危险字符
        filename = re.sub(r'[<>:"|?*\x00-\x1f]', '', filename)
        
        # 移除路径遍历
        filename = filename.replace('..', '')
        
        # 确保不为空
        if not filename:
            filename = 'unnamed_file'
        
        return filename
    
    def validate_content_length(self, content: str, max_length: int = 10000) -> bool:
        """验证内容长度"""
        if len(content) > max_length:
            from backend.core.exceptions import SecurityError
            raise SecurityError(f"内容长度超过限制: {len(content)} > {max_length}")
        return True
    
    @classmethod
    def generate_secure_filename(cls, original_filename: str) -> str:
        """生成安全的文件名
        
        Args:
            original_filename: 原始文件名
            
        Returns:
            str: 安全的文件名
        """
        # 获取文件扩展名
        file_ext = Path(original_filename).suffix
        
        # 生成时间戳和随机字符串
        import time
        import uuid
        
        timestamp = str(int(time.time()))
        random_str = str(uuid.uuid4())[:8]
        
        # 组合安全文件名
        safe_filename = f"{timestamp}_{random_str}{file_ext}"
        
        return safe_filename


# 创建全局验证器实例
security_validator = SecurityValidator()


class FileValidator:
    """文件验证器"""
    
    def validate_epub_file(self, file: UploadFile) -> bool:
        """验证EPUB文件"""
        # 检查文件扩展名
        if not file.filename or not file.filename.lower().endswith('.epub'):
            from backend.core.exceptions import FileValidationError
            raise FileValidationError("文件必须是.epub格式")
        
        # 检查MIME类型
        allowed_types = ['application/epub+zip', 'application/zip']
        if file.content_type and file.content_type not in allowed_types:
            from backend.core.exceptions import FileValidationError
            raise FileValidationError(f"不支持的文件类型: {file.content_type}")
        
        return True
    
    @classmethod
    def validate_epub_file_by_path(cls, file_path: str) -> bool:
        """通过路径验证EPUB文件"""
        return SecurityValidator.validate_file_type(file_path, ['application/epub+zip'])
    
    def validate_file_size(self, file: UploadFile, max_size: int = 50 * 1024 * 1024) -> bool:
        """验证文件大小"""
        try:
            # 获取文件大小
            file.file.seek(0, 2)  # 移动到文件末尾
            file_size = file.file.tell()
            file.file.seek(0)  # 重置到文件开头
            
            if file_size > max_size:
                from backend.core.exceptions import FileValidationError
                raise FileValidationError(f"文件大小超过限制: {file_size} > {max_size}")
            
            return True
        except Exception as e:
            if hasattr(e, '__class__') and 'FileValidationError' in str(e.__class__):
                raise
            from backend.core.exceptions import FileValidationError
            raise FileValidationError(f"文件大小验证失败: {str(e)}")
    
    @classmethod
    def validate_file_size_by_path(cls, file_path: str, max_size: int = None) -> bool:
        """通过路径验证文件大小"""
        return SecurityValidator.validate_file_size(file_path, max_size)
    
    def validate_rules_file(self, file: UploadFile) -> bool:
        """验证规则文件"""
        # 检查文件扩展名
        allowed_extensions = ['.txt', '.csv', '.tsv']
        if not file.filename or not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
            from backend.core.exceptions import FileValidationError
            raise FileValidationError(f"不支持的文件扩展名，支持的格式: {', '.join(allowed_extensions)}")
        
        return True
    
    @classmethod
    def validate_rules_file_by_path(cls, file_path: str) -> bool:
        """通过路径验证规则文件"""
        allowed_types = ['text/plain', 'text/csv', 'text/tab-separated-values']
        return SecurityValidator.validate_file_type(file_path, allowed_types)


# 创建全局文件验证器实例
file_validator = FileValidator()