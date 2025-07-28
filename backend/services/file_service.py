# File Service
# Handles file system operations

import os
import shutil
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from backend.services.base import BaseService


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
                self.log_error(f"Dangerous path detected: {file_path}")
                return False
            
            # 检查绝对路径到系统敏感目录
            sensitive_paths = [
                "/etc", "/bin", "/sbin", "/usr/bin", "/usr/sbin",
                "C:\\Windows", "C:\\Program Files", "C:\\System32"
            ]
            
            normalized_path = os.path.normpath(file_path).lower()
            for sensitive in sensitive_paths:
                if normalized_path.startswith(sensitive.lower()):
                    self.log_error(f"Access to sensitive path denied: {file_path}")
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
                from backend.models.schemas import FileContent
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
                
                # 检测文件编码
                detected_encoding = await self.detect_file_encoding(file_path)
                
                # 尝试使用检测到的编码读取文件
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


# 创建全局服务实例
file_service = FileService()


# 导出
__all__ = ["FileService", "file_service"]