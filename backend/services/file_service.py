# File Service
# Handles file system operations

import os
import shutil
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import HTTPException
from services.base import BaseService


class FileService(BaseService):
    """Service for handling file system operations"""
    
    def __init__(self):
        super().__init__("file")
    
    async def _initialize(self):
        """初始化文件服务"""
        await super()._initialize()
        self.log_info("File service initialized")
    
    async def read_file(self, file_path: str) -> str:
        """Read file content"""
        async with self.performance_context("read_file"):
            try:
                file_path_obj = Path(file_path)
                if not file_path_obj.exists():
                    raise FileNotFoundError(f"File not found: {file_path}")
                
                if not file_path_obj.is_file():
                    raise ValueError(f"Path is not a file: {file_path}")
                
                # Try different encodings
                encodings = ['utf-8', 'gbk', 'gb2312', 'latin1']
                for encoding in encodings:
                    try:
                        content = file_path_obj.read_text(encoding=encoding)
                        self.log_info(f"File read successfully: {file_path}", encoding=encoding)
                        return content
                    except UnicodeDecodeError:
                        continue
                
                raise ValueError(f"Cannot decode file with supported encodings: {file_path}")
                
            except Exception as e:
                self.log_error(f"Failed to read file: {file_path}", e)
                raise
    
    async def write_file(self, file_path: str, content: str) -> bool:
        """Write file content"""
        async with self.performance_context("write_file"):
            try:
                file_path_obj = Path(file_path)
                
                # Create parent directories if they don't exist
                file_path_obj.parent.mkdir(parents=True, exist_ok=True)
                
                # Write content to file
                file_path_obj.write_text(content, encoding='utf-8')
                
                self.log_info(f"File written successfully: {file_path}", size=len(content))
                return True
                
            except Exception as e:
                self.log_error(f"Failed to write file: {file_path}", e)
                raise
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete file"""
        async with self.performance_context("delete_file"):
            try:
                file_path_obj = Path(file_path)
                if not file_path_obj.exists():
                    raise FileNotFoundError(f"File not found: {file_path}")
                
                if not file_path_obj.is_file():
                    raise ValueError(f"Path is not a file: {file_path}")
                
                file_path_obj.unlink()
                
                self.log_info(f"File deleted successfully: {file_path}")
                return True
                
            except Exception as e:
                self.log_error(f"Failed to delete file: {file_path}", e)
                raise
    
    async def rename_file(self, old_path: str, new_path: str) -> bool:
        """Rename file"""
        async with self.performance_context("rename_file"):
            try:
                old_path_obj = Path(old_path)
                new_path_obj = Path(new_path)
                
                if not old_path_obj.exists():
                    raise FileNotFoundError(f"Source file not found: {old_path}")
                
                if new_path_obj.exists():
                    raise FileExistsError(f"Target file already exists: {new_path}")
                
                # Create parent directories if they don't exist
                new_path_obj.parent.mkdir(parents=True, exist_ok=True)
                
                old_path_obj.rename(new_path_obj)
                
                self.log_info(f"File renamed successfully: {old_path} -> {new_path}")
                return True
                
            except Exception as e:
                self.log_error(f"Failed to rename file: {old_path} -> {new_path}", e)
                raise
    
    async def copy_file(self, source_path: str, dest_path: str) -> bool:
        """Copy file"""
        async with self.performance_context("copy_file"):
            try:
                source_path_obj = Path(source_path)
                dest_path_obj = Path(dest_path)
                
                if not source_path_obj.exists():
                    raise FileNotFoundError(f"Source file not found: {source_path}")
                
                if not source_path_obj.is_file():
                    raise ValueError(f"Source path is not a file: {source_path}")
                
                # Create parent directories if they don't exist
                dest_path_obj.parent.mkdir(parents=True, exist_ok=True)
                
                shutil.copy2(source_path_obj, dest_path_obj)
                
                self.log_info(f"File copied successfully: {source_path} -> {dest_path}")
                return True
                
            except Exception as e:
                self.log_error(f"Failed to copy file: {source_path} -> {dest_path}", e)
                raise
    
    async def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get file information"""
        async with self.performance_context("get_file_info"):
            try:
                file_path_obj = Path(file_path)
                if not file_path_obj.exists():
                    raise FileNotFoundError(f"File not found: {file_path}")
                
                stat = file_path_obj.stat()
                
                info = {
                    "path": str(file_path_obj.absolute()),
                    "name": file_path_obj.name,
                    "size": stat.st_size,
                    "modified_time": stat.st_mtime,
                    "created_time": stat.st_ctime,
                    "is_file": file_path_obj.is_file(),
                    "is_directory": file_path_obj.is_dir(),
                    "is_symlink": file_path_obj.is_symlink(),
                    "suffix": file_path_obj.suffix,
                    "stem": file_path_obj.stem
                }
                
                self.log_info(f"File info retrieved: {file_path}")
                return info
                
            except Exception as e:
                self.log_error(f"Failed to get file info: {file_path}", e)
                raise
    
    async def list_directory(self, dir_path: str) -> List[str]:
        """List directory contents"""
        async with self.performance_context("list_directory"):
            try:
                dir_path_obj = Path(dir_path)
                if not dir_path_obj.exists():
                    raise FileNotFoundError(f"Directory not found: {dir_path}")
                
                if not dir_path_obj.is_dir():
                    raise ValueError(f"Path is not a directory: {dir_path}")
                
                items = [item.name for item in dir_path_obj.iterdir()]
                items.sort()
                
                self.log_info(f"Directory listed: {dir_path}", item_count=len(items))
                return items
                
            except Exception as e:
                self.log_error(f"Failed to list directory: {dir_path}", e)
                raise
    
    async def list_files(self, dir_path: str) -> List[Dict[str, Any]]:
        """List files in directory with detailed information"""
        async with self.performance_context("list_files"):
            try:
                dir_path_obj = Path(dir_path)
                if not dir_path_obj.exists():
                    raise FileNotFoundError(f"Directory not found: {dir_path}")
                
                if not dir_path_obj.is_dir():
                    raise ValueError(f"Path is not a directory: {dir_path}")
                
                files = []
                for item in dir_path_obj.iterdir():
                    try:
                        stat = item.stat()
                        file_info = {
                            "name": item.name,
                            "path": str(item.absolute()),
                            "size": stat.st_size,
                            "modified_time": stat.st_mtime,
                            "is_file": item.is_file(),
                            "is_directory": item.is_dir(),
                            "suffix": item.suffix if item.is_file() else None
                        }
                        files.append(file_info)
                    except (OSError, PermissionError) as e:
                        self.log_error(f"Error accessing item: {item}", e)
                        continue
                
                # Sort by name
                files.sort(key=lambda x: x['name'])
                
                self.log_info(f"Files listed: {dir_path}", file_count=len(files))
                return files
                
            except Exception as e:
                self.log_error(f"Failed to list files: {dir_path}", e)
                raise
    
    async def create_directory(self, dir_path: str) -> bool:
        """Create directory"""
        async with self.performance_context("create_directory"):
            try:
                dir_path_obj = Path(dir_path)
                
                if dir_path_obj.exists():
                    if dir_path_obj.is_dir():
                        self.log_info(f"Directory already exists: {dir_path}")
                        return True
                    else:
                        raise FileExistsError(f"Path exists but is not a directory: {dir_path}")
                
                dir_path_obj.mkdir(parents=True, exist_ok=True)
                
                self.log_info(f"Directory created successfully: {dir_path}")
                return True
                
            except Exception as e:
                self.log_error(f"Failed to create directory: {dir_path}", e)
                raise
    
    async def remove_directory(self, dir_path: str) -> bool:
        """Remove directory"""
        async with self.performance_context("remove_directory"):
            try:
                dir_path_obj = Path(dir_path)
                if not dir_path_obj.exists():
                    raise FileNotFoundError(f"Directory not found: {dir_path}")
                
                if not dir_path_obj.is_dir():
                    raise ValueError(f"Path is not a directory: {dir_path}")
                
                shutil.rmtree(dir_path_obj)
                
                self.log_info(f"Directory removed successfully: {dir_path}")
                return True
                
            except Exception as e:
                self.log_error(f"Failed to remove directory: {dir_path}", e)
                raise
    
    async def file_exists(self, file_path: str) -> bool:
        """Check if file exists"""
        async with self.performance_context("file_exists"):
            try:
                file_path_obj = Path(file_path)
                exists = file_path_obj.exists() and file_path_obj.is_file()
                
                self.log_info(f"File existence check: {file_path}", exists=exists)
                return exists
                
            except Exception as e:
                self.log_error(f"Failed to check file existence: {file_path}", e)
                return False
    
    async def get_file_size(self, file_path: str) -> int:
        """Get file size in bytes"""
        async with self.performance_context("get_file_size"):
            try:
                file_path_obj = Path(file_path)
                if not file_path_obj.exists():
                    raise FileNotFoundError(f"File not found: {file_path}")
                
                if not file_path_obj.is_file():
                    raise ValueError(f"Path is not a file: {file_path}")
                
                size = file_path_obj.stat().st_size
                
                self.log_info(f"File size retrieved: {file_path}", size=size)
                return size
                
            except Exception as e:
                self.log_error(f"Failed to get file size: {file_path}", e)
                raise
    
    def validate_path(self, file_path: str) -> bool:
        """Validate file path for security"""
        try:
            # 检查路径遍历攻击
            if ".." in file_path or "~" in file_path:
                error = ValueError(f"Dangerous path detected: {file_path}")
                self.log_error(f"Dangerous path detected: {file_path}", error)
                return False
            
            # 检查绝对路径到系统敏感目录
            sensitive_paths = [
                "/etc", "/bin", "/sbin", "/usr/bin", "/usr/sbin",
                "C:\\Windows", "C:\\Program Files", "C:\\System32"
            ]
            
            normalized_path = os.path.normpath(file_path).lower()
            for sensitive in sensitive_paths:
                if normalized_path.startswith(sensitive.lower()):
                    error = PermissionError(f"Access to sensitive path denied: {file_path}")
                    self.log_error(f"Access to sensitive path denied: {file_path}", error)
                    return False
            
            self.log_info(f"Path validation passed: {file_path}")
            return True
            
        except Exception as e:
            self.log_error(f"Path validation error: {file_path}", e)
            return False
    
    def is_allowed_file_type(self, file_path: str) -> bool:
        """Check if file type is allowed"""
        try:
            file_path_obj = Path(file_path)
            extension = file_path_obj.suffix.lower()
            
            # 允许的文件扩展名
            allowed_extensions = {
                ".txt", ".md", ".html", ".xhtml", ".css", ".js",
                ".json", ".xml", ".epub", ".png", ".jpg", ".jpeg",
                ".gif", ".svg", ".webp", ".pdf", ".zip"
            }
            
            # 禁止的文件扩展名
            disallowed_extensions = {
                ".exe", ".bat", ".sh", ".php", ".asp", ".jsp",
                ".py", ".rb", ".pl", ".cgi", ".dll", ".so"
            }
            
            if extension in disallowed_extensions:
                self.log_error(f"Disallowed file type: {file_path}", extension=extension)
                return False
            
            if extension in allowed_extensions:
                self.log_info(f"Allowed file type: {file_path}", extension=extension)
                return True
            
            # 对于未知扩展名，默认允许但记录警告
            self.log_info(f"Unknown file type, allowing: {file_path}", extension=extension)
            return True
            
        except Exception as e:
            self.log_error(f"File type validation error: {file_path}", e)
            return False
    
    async def get_file_content_enhanced(self, file_path: str, chunk_size: Optional[int] = None, chunk_offset: int = 0) -> 'FileContent':
        """增强的文件内容获取方法
        
        Args:
            file_path: 文件路径
            chunk_size: 分块大小（字节），None表示读取整个文件
            chunk_offset: 分块偏移量（字节）
            
        Returns:
            FileContent: 文件内容对象
        """
        async with self.performance_context("get_file_content_enhanced"):
            try:
                from db.models.schemas import FileContent
                import mimetypes
                import chardet
                
                file_path_obj = Path(file_path)
                if not file_path_obj.exists():
                    raise FileNotFoundError(f"File not found: {file_path}")
                
                if not file_path_obj.is_file():
                    raise ValueError(f"Path is not a file: {file_path}")
                
                # 获取文件信息
                file_size = file_path_obj.stat().st_size
                
                # 检测MIME类型
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type:
                    # 根据扩展名推断MIME类型
                    extension = file_path_obj.suffix.lower()
                    mime_map = {
                        '.html': 'text/html',
                        '.xhtml': 'application/xhtml+xml',
                        '.css': 'text/css',
                        '.js': 'application/javascript',
                        '.json': 'application/json',
                        '.xml': 'application/xml',
                        '.txt': 'text/plain',
                        '.md': 'text/markdown',
                        '.epub': 'application/epub+zip'
                    }
                    mime_type = mime_map.get(extension, 'application/octet-stream')
                
                # 检查是否为文本文件
                is_text_file = mime_type.startswith('text/') or mime_type in [
                    'application/json', 'application/xml', 'application/xhtml+xml',
                    'application/javascript', 'application/css'
                ]
                
                if not is_text_file:
                    # 对于二进制文件，返回基本信息
                    return FileContent(
                        path=str(file_path_obj.relative_to(file_path_obj.parent.parent) if file_path_obj.parent.parent.exists() else file_path_obj.name),
                        content="[Binary file - content not displayed]",
                        mime_type=mime_type,
                        size=file_size,
                        encoding="binary",
                        is_binary=True
                    )
                
                # 读取文件内容（文本文件）
                content = ""
                detected_encoding = "utf-8"
                
                # 首先尝试检测编码
                try:
                    with open(file_path, 'rb') as f:
                        # 读取前1024字节用于编码检测
                        sample = f.read(min(1024, file_size))
                        if sample:
                            detection_result = chardet.detect(sample)
                            if detection_result['encoding'] and detection_result['confidence'] > 0.7:
                                detected_encoding = detection_result['encoding']
                except Exception as e:
                    self.log_error(f"Encoding detection failed: {file_path}", e)
                
                # 如果需要分块读取
                if chunk_size is not None and chunk_size > 0:
                    try:
                        with open(file_path, 'r', encoding=detected_encoding, errors='replace') as f:
                            f.seek(chunk_offset)
                            content = f.read(chunk_size)
                    except UnicodeDecodeError:
                        # 尝试其他编码
                        for encoding in ['utf-8', 'gbk', 'gb2312', 'latin1']:
                            try:
                                with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                                    f.seek(chunk_offset)
                                    content = f.read(chunk_size)
                                detected_encoding = encoding
                                break
                            except UnicodeDecodeError:
                                continue
                        else:
                            # 如果所有编码都失败，以二进制方式读取
                            with open(file_path, 'rb') as f:
                                f.seek(chunk_offset)
                                binary_content = f.read(chunk_size)
                                content = binary_content.decode('utf-8', errors='replace')
                                detected_encoding = 'utf-8'
                else:
                    # 读取整个文件
                    try:
                        with open(file_path, 'r', encoding=detected_encoding, errors='replace') as f:
                            content = f.read()
                    except UnicodeDecodeError:
                        # 尝试其他编码
                        for encoding in ['utf-8', 'gbk', 'gb2312', 'latin1']:
                            try:
                                with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                                    content = f.read()
                                detected_encoding = encoding
                                break
                            except UnicodeDecodeError:
                                continue
                        else:
                            # 如果所有编码都失败，以二进制方式读取
                            with open(file_path, 'rb') as f:
                                binary_content = f.read()
                                content = binary_content.decode('utf-8', errors='replace')
                                detected_encoding = 'utf-8'
                
                # 计算实际内容大小
                actual_size = len(content.encode(detected_encoding))
                
                self.log_info(
                    f"File content retrieved: {file_path}",
                    size=actual_size,
                    encoding=detected_encoding,
                    mime_type=mime_type,
                    chunk_size=chunk_size,
                    chunk_offset=chunk_offset
                )
                
                return FileContent(
                    path=str(file_path_obj.relative_to(file_path_obj.parent.parent) if file_path_obj.parent.parent.exists() else file_path_obj.name),
                    content=content,
                    mime_type=mime_type,
                    size=file_size,
                    encoding=detected_encoding,
                    is_binary=False,
                    chunk_info={
                        "chunk_size": chunk_size,
                        "chunk_offset": chunk_offset,
                        "total_size": file_size,
                        "content_size": actual_size
                    } if chunk_size is not None else None
                )
                
            except Exception as e:
                self.log_error(f"Failed to get file content: {file_path}", e)
                raise
    
    async def read_file_with_encoding(self, file_path: str) -> tuple[str, str]:
        """读取文件内容并返回内容和编码
        
        Args:
            file_path: 文件路径
            
        Returns:
            tuple[str, str]: (文件内容, 编码)
        """
        async with self.performance_context("read_file_with_encoding"):
            try:
                file_path_obj = Path(file_path)
                if not file_path_obj.exists():
                    raise FileNotFoundError(f"File not found: {file_path}")
                
                if not file_path_obj.is_file():
                    raise ValueError(f"Path is not a file: {file_path}")
                
                # 检查文件大小，对于大文件使用流式读取
                file_size = file_path_obj.stat().st_size
                max_memory_size = 50 * 1024 * 1024  # 50MB内存限制
                
                # 检测文件编码
                detected_encoding = await self.detect_file_encoding(file_path)
                
                # 对于大文件，使用流式读取避免内存溢出
                if file_size > max_memory_size:
                    self.log_info(f"Large file detected ({file_size / 1024 / 1024:.1f}MB), using streaming read: {file_path}")
                    
                    # 流式读取大文件
                    content_chunks = []
                    chunk_size = 8192  # 8KB chunks
                    
                    try:
                        with open(file_path, 'r', encoding=detected_encoding, errors='replace') as f:
                            while True:
                                chunk = f.read(chunk_size)
                                if not chunk:
                                    break
                                content_chunks.append(chunk)
                        
                        content = ''.join(content_chunks)
                        self.log_info(f"Large file read with streaming: {file_path}", encoding=detected_encoding, size_mb=file_size / 1024 / 1024)
                        return content, detected_encoding
                        
                    except UnicodeDecodeError:
                        # 如果检测到的编码失败，尝试其他编码
                        encodings = ['utf-8', 'gbk', 'gb2312', 'latin1']
                        for encoding in encodings:
                            try:
                                content_chunks = []
                                with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                                    while True:
                                        chunk = f.read(chunk_size)
                                        if not chunk:
                                            break
                                        content_chunks.append(chunk)
                                
                                content = ''.join(content_chunks)
                                self.log_info(f"Large file read with fallback encoding: {file_path}", encoding=encoding)
                                return content, encoding
                            except UnicodeDecodeError:
                                continue
                        
                        raise ValueError(f"Cannot decode large file with supported encodings: {file_path}")
                else:
                    # 小文件使用原有的一次性读取方式
                    try:
                        content = file_path_obj.read_text(encoding=detected_encoding)
                        self.log_info(f"File read with encoding: {file_path}", encoding=detected_encoding)
                        return content, detected_encoding
                    except UnicodeDecodeError:
                        # 如果检测到的编码失败，尝试其他编码
                        encodings = ['utf-8', 'gbk', 'gb2312', 'latin1']
                        for encoding in encodings:
                            try:
                                content = file_path_obj.read_text(encoding=encoding)
                                self.log_info(f"File read with fallback encoding: {file_path}", encoding=encoding)
                                return content, encoding
                            except UnicodeDecodeError:
                                continue
                        
                        raise ValueError(f"Cannot decode file with supported encodings: {file_path}")
                
            except Exception as e:
                self.log_error(f"Failed to read file with encoding: {file_path}", e)
                raise

    async def detect_file_encoding(self, file_path: str) -> str:
        """检测文件编码
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 检测到的编码名称
        """
        async with self.performance_context("detect_file_encoding"):
            try:
                import chardet
                
                file_path_obj = Path(file_path)
                if not file_path_obj.exists() or not file_path_obj.is_file():
                    raise FileNotFoundError(f"File not found: {file_path}")
                
                # 读取文件样本进行编码检测
                with open(file_path, 'rb') as f:
                    sample = f.read(min(8192, file_path_obj.stat().st_size))
                
                if not sample:
                    return 'utf-8'  # 空文件默认为utf-8
                
                detection_result = chardet.detect(sample)
                encoding = detection_result.get('encoding', 'utf-8')
                confidence = detection_result.get('confidence', 0)
                
                # 如果置信度太低，使用默认编码
                if confidence < 0.7:
                    encoding = 'utf-8'
                
                self.log_info(
                    f"File encoding detected: {file_path}",
                    encoding=encoding,
                    confidence=confidence
                )
                
                return encoding
                
            except Exception as e:
                self.log_error(f"Failed to detect file encoding: {file_path}", e)
                return 'utf-8'  # 默认返回utf-8
    
    async def get_file_type_info(self, file_path: str) -> Dict[str, Any]:
        """获取文件类型信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict[str, Any]: 文件类型信息
        """
        async with self.performance_context("get_file_type_info"):
            try:
                import mimetypes
                
                file_path_obj = Path(file_path)
                if not file_path_obj.exists():
                    raise FileNotFoundError(f"File not found: {file_path}")
                
                # 基本信息
                extension = file_path_obj.suffix.lower()
                mime_type, encoding = mimetypes.guess_type(file_path)
                
                # 如果MIME类型未知，根据扩展名推断
                if not mime_type:
                    extension_map = {
                        '.html': 'text/html',
                        '.xhtml': 'application/xhtml+xml',
                        '.css': 'text/css',
                        '.js': 'application/javascript',
                        '.json': 'application/json',
                        '.xml': 'application/xml',
                        '.txt': 'text/plain',
                        '.md': 'text/markdown',
                        '.epub': 'application/epub+zip',
                        '.png': 'image/png',
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.gif': 'image/gif',
                        '.svg': 'image/svg+xml',
                        '.pdf': 'application/pdf'
                    }
                    mime_type = extension_map.get(extension, 'application/octet-stream')
                
                # 判断文件类别
                is_text = mime_type.startswith('text/') or mime_type in [
                    'application/json', 'application/xml', 'application/xhtml+xml',
                    'application/javascript'
                ]
                is_image = mime_type.startswith('image/')
                is_archive = mime_type in ['application/zip', 'application/epub+zip']
                
                file_info = {
                    'extension': extension,
                    'mime_type': mime_type,
                    'encoding': encoding,
                    'is_text': is_text,
                    'is_image': is_image,
                    'is_archive': is_archive,
                    'is_binary': not is_text,
                    'category': self._get_file_category(mime_type)
                }
                
                self.log_info(f"File type info retrieved: {file_path}", **file_info)
                return file_info
                
            except Exception as e:
                self.log_error(f"Failed to get file type info: {file_path}", e)
                raise
    
    def _get_file_category(self, mime_type: str) -> str:
        """根据MIME类型获取文件类别"""
        if mime_type.startswith('text/'):
            return 'text'
        elif mime_type.startswith('image/'):
            return 'image'
        elif mime_type.startswith('audio/'):
            return 'audio'
        elif mime_type.startswith('video/'):
            return 'video'
        elif mime_type in ['application/json', 'application/xml', 'application/xhtml+xml']:
            return 'structured_text'
        elif mime_type in ['application/zip', 'application/epub+zip']:
            return 'archive'
        elif mime_type == 'application/pdf':
            return 'document'
        else:
            return 'binary'
    
    async def _cleanup(self):
        """清理服务资源"""
        # FileService 没有需要特别清理的资源
        await super()._cleanup()
    
    async def get_file_tree(self, session_id: str):
        """获取文件树结构
        
        Args:
            session_id: 会话ID
            
        Returns:
            FileTreeResponse: 文件树响应
        """
        async with self.performance_context("get_file_tree", session_id=session_id):
            try:
                from db.models.schemas import FileTreeResponse, FileNode, FileType
                from services.session_service import session_service
                from services.epub_service import epub_service
                from core.config import settings
                
                # 获取会话信息
                session = await session_service.get_session(session_id)
                self.log_info(f"Session lookup result for {session_id}: {session is not None}")
                if not session:
                    error = FileNotFoundError(f"Session not found: {session_id}")
                    self.log_error(f"Session not found: {session_id}", error)
                    raise HTTPException(
                        status_code=404,
                        detail={
                            "status": "error",
                            "error_code": "SESSION_NOT_FOUND",
                            "message": "会话不存在或已过期"
                        }
                    )
                
                # 根据文件类型获取文件树
                file_type = session['session_metadata'].get("file_type") if session.get('session_metadata') else None
                
                # 如果metadata中没有file_type，根据文件扩展名判断
                if not file_type and session.get('original_filename'):
                    file_ext = Path(session['original_filename']).suffix.lower()
                    if file_ext == '.epub':
                        file_type = 'epub'
                    elif file_ext in ['.txt', '.md']:
                        file_type = 'text'
                    else:
                        file_type = 'text'  # 默认为text类型
                
                if file_type == "text":
                    # 处理TEXT文件 - 从内存中获取文件信息
                    from services.text_service import text_service
                    
                    # 检查text_service中是否有该会话的文件内容
                    if not hasattr(text_service, 'file_contents') or session_id not in text_service.file_contents:
                        raise HTTPException(
                            status_code=404,
                            detail={
                                "status": "error",
                                "error_code": "FILE_NOT_FOUND",
                                "message": "会话文件内容不存在"
                            }
                        )
                    
                    # 从内存中构建TEXT文件的文件树
                    file_tree = []
                    file_contents = text_service.file_contents[session_id]
                    
                    for filename, content_bytes in file_contents.items():
                        file_size = len(content_bytes)
                        file_ext = Path(filename).suffix.lower()
                        
                        file_node = FileNode(
                            name=filename,
                            path=filename,  # 相对路径
                            type=FileType.TEXT if file_ext in ['.txt', '.md'] else FileType.FILE,
                            size=file_size,
                            mime_type="text/plain" if file_ext in ['.txt', '.md'] else None,
                            modified_time=datetime.now()  # 使用当前时间作为修改时间
                        )
                        file_tree.append(file_node)
                    
                    self.log_info(f"Text file tree retrieved from memory", session_id=session_id, file_count=len(file_tree))
                    
                else:
                    # 处理EPUB文件，调用epub_service
                    file_tree = await epub_service.get_file_tree(session_id)
                    self.log_info(f"EPUB file tree retrieved", session_id=session_id)
                
                # 计算统计信息
                total_files = len(file_tree)
                total_size = sum(node.size for node in file_tree if node.size)
                
                return FileTreeResponse(
                    success=True,
                    file_tree=file_tree,
                    total_files=total_files,
                    total_size=total_size
                )
                
            except HTTPException:
                raise
            except Exception as e:
                self.log_error(f"Failed to get file tree", e, session_id=session_id)
                raise HTTPException(
                    status_code=500,
                    detail={
                        "status": "error",
                        "error_code": "INTERNAL_ERROR",
                        "message": "获取文件树失败"
                    }
                )


    async def get_file_content(self, session_id: str, file_path: str) -> 'FileContent':
        """根据会话ID和文件路径获取文件内容
        
        Args:
            session_id: 会话ID
            file_path: 文件路径
            
        Returns:
            FileContent: 文件内容对象
        """
        async with self.performance_context("get_file_content", session_id=session_id, file_path=file_path):
            try:
                from db.models.schemas import FileContent
                from services.session_service import session_service
                from core.security import security_validator
                import mimetypes
                import os
                
                # 获取会话信息
                session = await session_service.get_session(session_id)
                if not session:
                    raise FileNotFoundError(f"Session not found: {session_id}")
                
                # 获取会话的文件根目录
                base_dir = None
                
                # 对于EPUB文件，使用extracted_path + epub子目录
                if session.get('extracted_path') and os.path.exists(session['extracted_path']):
                    epub_dir = os.path.join(session['extracted_path'], 'epub')
                    if os.path.exists(epub_dir):
                        base_dir = epub_dir
                        self.log_info(f"Using EPUB extracted path: {base_dir}", session_id=session_id)
                    else:
                        base_dir = session['extracted_path']
                        self.log_info(f"Using EPUB extracted path (no epub subdir): {base_dir}", session_id=session_id)
                
                # 获取文件类型
                file_type = session['session_metadata'].get("file_type") if session.get('session_metadata') else None
                
                # 如果metadata中没有file_type，根据文件扩展名判断
                if not file_type and session.get('original_filename'):
                    file_ext = Path(session['original_filename']).suffix.lower()
                    if file_ext == '.epub':
                        file_type = 'epub'
                    elif file_ext in ['.txt', '.md']:
                        file_type = 'text'
                    else:
                        file_type = 'text'  # 默认为text类型
                
                # 对于TEXT文件，从内存中获取文件内容
                if file_type == "text":
                    from services.text_service import text_service
                    
                    # 检查text_service中是否有该会话的文件内容
                    if not hasattr(text_service, 'file_contents') or session_id not in text_service.file_contents:
                        raise FileNotFoundError(f"Session file contents not found in memory: {session_id}")
                    
                    file_contents = text_service.file_contents[session_id]
                    if file_path not in file_contents:
                        raise FileNotFoundError(f"File not found in session: {file_path}")
                    
                    # 从内存中获取文件内容
                    content_bytes = file_contents[file_path]
                    content = content_bytes.decode('utf-8')
                    
                    # 构建FileContent对象
                    file_path_obj = Path(file_path)
                    return FileContent(
                        path=file_path,
                        content=content,
                        mime_type="text/plain" if file_path_obj.suffix.lower() in ['.txt'] else "text/markdown",
                        size=len(content_bytes),
                        encoding="utf-8",
                        is_binary=False
                    )
                
                # 对于EPUB文件，使用文件系统路径
                if not base_dir:
                    # 对于EPUB文件，尝试从epub_service获取文件内容
                    if file_type == "epub":
                        from services.epub_service import epub_service
                        try:
                            return await epub_service.get_file_content(session_id, file_path)
                        except Exception as epub_error:
                            self.log_error(f"Failed to get EPUB file content from epub_service", epub_error, session_id=session_id, file_path=file_path)
                            raise FileNotFoundError(f"EPUB file not found: {file_path}")
                    
                    # 对于其他类型，检查是否有extracted_path
                    error_msg = f"No base directory available for file type: {file_type}"
                    self.log_error(error_msg, FileNotFoundError(error_msg), session_id=session_id, file_path=file_path)
                    raise FileNotFoundError(f"No valid base directory found for session: {session_id}")
                
                if not base_dir:
                    raise FileNotFoundError(f"No valid base directory found for session: {session_id}")
                
                # 安全路径验证和构建完整路径
                safe_path = security_validator.sanitize_path(file_path, base_dir)
                
                if not os.path.exists(safe_path) or not os.path.isfile(safe_path):
                    error_msg = f"File not found: {safe_path}"
                    self.log_error(error_msg, FileNotFoundError(error_msg), session_id=session_id, file_path=file_path)
                    raise FileNotFoundError(f"File not found: {file_path}")
                
                # 使用现有的get_file_content_enhanced方法
                return await self.get_file_content_enhanced(safe_path)
                
            except Exception as e:
                self.log_error(f"Failed to get file content: {file_path}", e, session_id=session_id)
                raise


    async def export_file(self, session_id: str, format: str = "original"):
        """导出文件
        
        Args:
            session_id: 会话ID
            format: 导出格式 (original, epub, txt)
            
        Returns:
            ExportResult: 包含content_stream、media_type和filename的导出结果
        """
        async with self.performance_context("export_file", session_id=session_id, format=format):
            try:
                from services.session_service import session_service
                from services.epub_service import epub_service
                from services.text_service import text_service
                import tempfile
                import os
                from pathlib import Path
                import io
                
                # 获取会话信息
                session = await session_service.get_session(session_id)
                if not session:
                    raise FileNotFoundError(f"Session not found: {session_id}")
                
                self.log_info(f"Exporting file for session: {session_id}", format=format)
                
                # 根据格式和会话类型进行导出
                session_file_type = session['session_metadata'].get("file_type") if session.get('session_metadata') else None
                if format == "epub" or (format == "original" and session_file_type == "epub"):
                    # 导出EPUB文件
                    self.log_info(f"Starting EPUB export for session: {session_id}", session_id=session_id)
                    
                    # 验证会话状态 - 移除对extracted_path的强依赖
                    if not session.get('session_metadata', {}).get('file_type') == 'epub':
                        self.log_error(f"Session is not an EPUB session", session_id=session_id)
                        raise FileNotFoundError(f"Session is not an EPUB session: {session_id}")
                    
                    # 创建临时输出文件
                    temp_output_path = None
                    try:
                        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as temp_file:
                            temp_output_path = temp_file.name
                        
                        self.log_info(f"Created temporary file: {temp_output_path}", session_id=session_id)
                        
                        # 使用epub_service导出
                        output_path = await epub_service.export_epub(session_id, temp_output_path)
                        
                        # 验证导出文件是否存在且有内容
                        if not os.path.exists(output_path):
                            raise FileNotFoundError(f"Export failed - output file not created: {output_path}")
                        
                        file_size = os.path.getsize(output_path)
                        if file_size == 0:
                            raise ValueError(f"Export failed - output file is empty: {output_path}")
                        
                        self.log_info(f"EPUB export successful, file size: {file_size} bytes", session_id=session_id)
                        
                        # 读取导出的文件内容
                        with open(output_path, 'rb') as f:
                            file_content = f.read()
                        
                        # 创建文件流
                        content_stream = io.BytesIO(file_content)
                        
                        # 确定文件名
                        original_filename = session.get('original_filename', 'export')
                        if original_filename.endswith('.epub'):
                            filename = original_filename
                        else:
                            filename = f"{Path(original_filename).stem}.epub"
                        
                        result = ExportResult(
                            content_stream=content_stream,
                            media_type="application/epub+zip",
                            filename=filename
                        )
                        
                        self.log_info(f"EPUB export completed successfully", 
                                     session_id=session_id, 
                                     export_filename=filename, 
                                     size=len(file_content),
                                     temp_file=temp_output_path)
                        return result
                        
                    except Exception as e:
                        self.log_error(f"EPUB export failed", e, session_id=session_id, temp_file=temp_output_path)
                        raise
                        
                    finally:
                        # 确保临时文件被清理
                        if temp_output_path and os.path.exists(temp_output_path):
                            try:
                                os.unlink(temp_output_path)
                                self.log_info(f"Cleaned up temporary file: {temp_output_path}", session_id=session_id)
                            except Exception as cleanup_error:
                                self.log_error(f"Failed to cleanup temporary file: {temp_output_path}", cleanup_error, session_id=session_id)
                
                elif format == "txt" or (format == "original" and session_file_type == "text"):
                    # 导出文本文件
                    session_dir = session_service.get_session_dir(session_id, "text")
                    
                    if not session_dir.exists():
                        raise FileNotFoundError(f"Session directory not found: {session_dir}")
                    
                    # 查找文本文件
                    text_files = list(session_dir.glob("*.txt")) + list(session_dir.glob("*.md"))
                    if not text_files:
                        raise FileNotFoundError(f"No text files found in session: {session_id}")
                    
                    # 使用第一个找到的文件
                    text_file = text_files[0]
                    
                    # 读取文件内容
                    with open(text_file, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                    
                    # 创建文件流
                    content_stream = io.BytesIO(file_content.encode('utf-8'))
                    
                    # 确定文件名和MIME类型
                    filename = session.get('original_filename') or text_file.name
                    if text_file.suffix == '.md':
                        media_type = "text/markdown"
                    else:
                        media_type = "text/plain"
                    
                    result = ExportResult(
                        content_stream=content_stream,
                        media_type=media_type,
                        filename=filename
                    )
                    
                    self.log_info(f"Text export completed", session_id=session_id, export_filename=filename, size=len(file_content))
                    return result
                
                else:
                    raise ValueError(f"Unsupported export format: {format}")
                    
            except Exception as e:
                self.log_error(f"Failed to export file: {session_id}", e, format=format)
                raise


class ExportResult:
    """导出结果类"""
    
    def __init__(self, content_stream, media_type: str, filename: str):
        import io
        self.content_stream = content_stream
        self.media_type = media_type
        self.filename = filename


# 创建全局服务实例
file_service = FileService()


# 导出
__all__ = ["FileService", "file_service", "ExportResult"]