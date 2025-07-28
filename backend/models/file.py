"""文件模型"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum
import mimetypes
import os


class FileType(str, Enum):
    """文件类型枚举"""
    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"


class FileCategory(str, Enum):
    """文件分类枚举"""
    TEXT = "text"
    HTML = "html"
    CSS = "css"
    JAVASCRIPT = "javascript"
    IMAGE = "image"
    FONT = "font"
    AUDIO = "audio"
    VIDEO = "video"
    ARCHIVE = "archive"
    DOCUMENT = "document"
    OTHER = "other"


class FileNode(BaseModel):
    """文件节点模型"""
    
    name: str = Field(..., description="文件名")
    path: str = Field(..., description="文件路径")
    type: FileType = Field(..., description="文件类型")
    size: Optional[int] = Field(None, description="文件大小（字节）")
    mime_type: Optional[str] = Field(None, description="MIME类型")
    category: Optional[FileCategory] = Field(None, description="文件分类")
    encoding: Optional[str] = Field(None, description="文件编码")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    modified_at: Optional[datetime] = Field(None, description="修改时间")
    accessed_at: Optional[datetime] = Field(None, description="访问时间")
    permissions: Optional[str] = Field(None, description="文件权限")
    is_hidden: bool = Field(default=False, description="是否隐藏文件")
    is_readonly: bool = Field(default=False, description="是否只读")
    checksum: Optional[str] = Field(None, description="文件校验和")
    children: List['FileNode'] = Field(default_factory=list, description="子文件/目录")
    parent_path: Optional[str] = Field(None, description="父目录路径")
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.mime_type and self.type == FileType.FILE:
            self.mime_type = self._guess_mime_type()
        if not self.category:
            self.category = self._guess_category()
    
    def _guess_mime_type(self) -> Optional[str]:
        """猜测MIME类型"""
        if self.type != FileType.FILE:
            return None
        mime_type, _ = mimetypes.guess_type(self.name)
        return mime_type
    
    def _guess_category(self) -> FileCategory:
        """猜测文件分类"""
        if self.type == FileType.DIRECTORY:
            return FileCategory.OTHER
        
        if not self.mime_type:
            return FileCategory.OTHER
        
        mime_lower = self.mime_type.lower()
        
        if mime_lower.startswith('text/'):
            if 'html' in mime_lower:
                return FileCategory.HTML
            elif 'css' in mime_lower:
                return FileCategory.CSS
            elif 'javascript' in mime_lower:
                return FileCategory.JAVASCRIPT
            else:
                return FileCategory.TEXT
        elif mime_lower.startswith('image/'):
            return FileCategory.IMAGE
        elif mime_lower.startswith('audio/'):
            return FileCategory.AUDIO
        elif mime_lower.startswith('video/'):
            return FileCategory.VIDEO
        elif mime_lower.startswith('font/') or 'font' in mime_lower:
            return FileCategory.FONT
        elif mime_lower in ['application/zip', 'application/x-rar', 'application/x-tar']:
            return FileCategory.ARCHIVE
        elif mime_lower in ['application/pdf', 'application/msword']:
            return FileCategory.DOCUMENT
        else:
            return FileCategory.OTHER
    
    def add_child(self, child: 'FileNode') -> None:
        """添加子节点"""
        child.parent_path = self.path
        self.children.append(child)
    
    def remove_child(self, child_name: str) -> bool:
        """移除子节点"""
        for i, child in enumerate(self.children):
            if child.name == child_name:
                del self.children[i]
                return True
        return False
    
    def find_child(self, name: str) -> Optional['FileNode']:
        """查找子节点"""
        for child in self.children:
            if child.name == name:
                return child
        return None
    
    def find_by_path(self, path: str) -> Optional['FileNode']:
        """根据路径查找节点"""
        if self.path == path:
            return self
        
        for child in self.children:
            result = child.find_by_path(path)
            if result:
                return result
        
        return None
    
    def get_all_files(self, category: Optional[FileCategory] = None) -> List['FileNode']:
        """获取所有文件"""
        files = []
        
        if self.type == FileType.FILE:
            if category is None or self.category == category:
                files.append(self)
        
        for child in self.children:
            files.extend(child.get_all_files(category))
        
        return files
    
    def get_size_recursive(self) -> int:
        """递归获取大小"""
        total_size = self.size or 0
        for child in self.children:
            total_size += child.get_size_recursive()
        return total_size
    
    def is_text_file(self) -> bool:
        """判断是否为文本文件"""
        return self.category in [FileCategory.TEXT, FileCategory.HTML, FileCategory.CSS, FileCategory.JAVASCRIPT]
    
    def is_editable(self) -> bool:
        """判断是否可编辑"""
        return self.type == FileType.FILE and self.is_text_file() and not self.is_readonly
    
    def get_extension(self) -> str:
        """获取文件扩展名"""
        if self.type != FileType.FILE:
            return ""
        return os.path.splitext(self.name)[1].lower()
    
    def get_relative_path(self, base_path: str) -> str:
        """获取相对路径"""
        if self.path.startswith(base_path):
            return self.path[len(base_path):].lstrip('/')
        return self.path
    
    def to_dict(self, include_children: bool = True) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "name": self.name,
            "path": self.path,
            "type": self.type.value,
            "size": self.size,
            "mime_type": self.mime_type,
            "category": self.category.value if self.category else None,
            "encoding": self.encoding,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
            "accessed_at": self.accessed_at.isoformat() if self.accessed_at else None,
            "permissions": self.permissions,
            "is_hidden": self.is_hidden,
            "is_readonly": self.is_readonly,
            "checksum": self.checksum,
            "parent_path": self.parent_path,
            "extension": self.get_extension(),
            "is_text_file": self.is_text_file(),
            "is_editable": self.is_editable()
        }
        
        if include_children:
            result["children"] = [child.to_dict(include_children) for child in self.children]
        else:
            result["has_children"] = len(self.children) > 0
            result["children_count"] = len(self.children)
        
        return result
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FileContent(BaseModel):
    """文件内容模型"""
    
    path: str = Field(..., description="文件路径")
    content: str = Field(..., description="文件内容")
    encoding: str = Field(default="utf-8", description="编码格式")
    mime_type: str = Field(..., description="MIME类型")
    size: int = Field(..., description="文件大小")
    checksum: Optional[str] = Field(None, description="文件校验和")
    last_modified: Optional[datetime] = Field(None, description="最后修改时间")
    is_binary: bool = Field(default=False, description="是否为二进制文件")
    line_count: Optional[int] = Field(None, description="行数")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "path": self.path,
            "content": self.content,
            "encoding": self.encoding,
            "mime_type": self.mime_type,
            "size": self.size,
            "checksum": self.checksum,
            "last_modified": self.last_modified.isoformat() if self.last_modified else None,
            "is_binary": self.is_binary,
            "line_count": self.line_count
        }
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FileOperation(BaseModel):
    """文件操作模型"""
    
    operation_type: str = Field(..., description="操作类型")
    source_path: str = Field(..., description="源路径")
    target_path: Optional[str] = Field(None, description="目标路径")
    timestamp: datetime = Field(default_factory=datetime.now, description="操作时间")
    user_id: Optional[str] = Field(None, description="用户ID")
    session_id: Optional[str] = Field(None, description="会话ID")
    success: bool = Field(default=True, description="是否成功")
    error_message: Optional[str] = Field(None, description="错误消息")
    metadata: Optional[Dict[str, Any]] = Field(None, description="操作元数据")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "operation_type": self.operation_type,
            "source_path": self.source_path,
            "target_path": self.target_path,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "session_id": self.session_id,
            "success": self.success,
            "error_message": self.error_message,
            "metadata": self.metadata
        }
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FileStats(BaseModel):
    """文件统计模型"""
    
    total_files: int = Field(default=0, description="总文件数")
    total_directories: int = Field(default=0, description="总目录数")
    total_size: int = Field(default=0, description="总大小")
    file_types: Dict[str, int] = Field(default_factory=dict, description="文件类型统计")
    categories: Dict[str, int] = Field(default_factory=dict, description="分类统计")
    largest_file: Optional[str] = Field(None, description="最大文件")
    smallest_file: Optional[str] = Field(None, description="最小文件")
    newest_file: Optional[str] = Field(None, description="最新文件")
    oldest_file: Optional[str] = Field(None, description="最旧文件")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_files": self.total_files,
            "total_directories": self.total_directories,
            "total_size": self.total_size,
            "file_types": self.file_types,
            "categories": self.categories,
            "largest_file": self.largest_file,
            "smallest_file": self.smallest_file,
            "newest_file": self.newest_file,
            "oldest_file": self.oldest_file
        }


class FileSearchResult(BaseModel):
    """文件搜索结果模型"""
    
    files: List[FileNode] = Field(..., description="匹配的文件列表")
    total_count: int = Field(..., description="总匹配数")
    search_time: float = Field(..., description="搜索耗时（秒）")
    query: str = Field(..., description="搜索查询")
    filters: Optional[Dict[str, Any]] = Field(None, description="搜索过滤器")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "files": [file.to_dict() for file in self.files],
            "total_count": self.total_count,
            "search_time": self.search_time,
            "query": self.query,
            "filters": self.filters
        }