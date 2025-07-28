"""会话模型"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    """会话状态枚举"""
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    SUSPENDED = "suspended"


class Session(BaseModel):
    """会话模型"""
    
    session_id: str = Field(..., description="会话ID")
    epub_path: str = Field(..., description="EPUB文件路径")
    upload_time: datetime = Field(..., description="上传时间")
    last_accessed: datetime = Field(default_factory=datetime.now, description="最后访问时间")
    expires_at: datetime = Field(..., description="过期时间")
    status: SessionStatus = Field(default=SessionStatus.ACTIVE, description="会话状态")
    original_filename: Optional[str] = Field(None, description="原始文件名")
    file_size: Optional[int] = Field(None, description="文件大小")
    extracted_path: Optional[str] = Field(None, description="解压路径")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    
    def __init__(self, **data):
        if 'expires_at' not in data:
            data['expires_at'] = datetime.now() + timedelta(hours=1)  # 默认1小时过期
        super().__init__(**data)
    
    def is_expired(self) -> bool:
        """检查会话是否过期"""
        return datetime.now() > self.expires_at
    
    def extend_session(self, hours: int = 1) -> None:
        """延长会话时间"""
        self.expires_at = datetime.now() + timedelta(hours=hours)
        self.last_accessed = datetime.now()
    
    def touch(self) -> None:
        """更新最后访问时间"""
        self.last_accessed = datetime.now()
    
    def terminate(self) -> None:
        """终止会话"""
        self.status = SessionStatus.TERMINATED
    
    def suspend(self) -> None:
        """暂停会话"""
        self.status = SessionStatus.SUSPENDED
    
    def activate(self) -> None:
        """激活会话"""
        self.status = SessionStatus.ACTIVE
        self.touch()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "epub_path": self.epub_path,
            "upload_time": self.upload_time.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "status": self.status.value,
            "original_filename": self.original_filename,
            "file_size": self.file_size,
            "extracted_path": self.extracted_path,
            "metadata": self.metadata,
            "is_expired": self.is_expired()
        }
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SessionStats(BaseModel):
    """会话统计模型"""
    
    total_sessions: int = Field(..., description="总会话数")
    active_sessions: int = Field(..., description="活跃会话数")
    expired_sessions: int = Field(..., description="过期会话数")
    terminated_sessions: int = Field(..., description="已终止会话数")
    average_session_duration: float = Field(..., description="平均会话时长（秒）")
    total_files_processed: int = Field(..., description="处理的文件总数")
    total_storage_used: int = Field(..., description="使用的存储空间（字节）")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_sessions": self.total_sessions,
            "active_sessions": self.active_sessions,
            "expired_sessions": self.expired_sessions,
            "terminated_sessions": self.terminated_sessions,
            "average_session_duration": self.average_session_duration,
            "total_files_processed": self.total_files_processed,
            "total_storage_used": self.total_storage_used
        }


class SessionListResponse(BaseModel):
    """会话列表响应模型"""
    
    sessions: list[Session] = Field(..., description="会话列表")
    total_count: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页")
    page_size: int = Field(..., description="页大小")
    has_next: bool = Field(..., description="是否有下一页")
    has_prev: bool = Field(..., description="是否有上一页")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "sessions": [session.to_dict() for session in self.sessions],
            "total_count": self.total_count,
            "page": self.page,
            "page_size": self.page_size,
            "has_next": self.has_next,
            "has_prev": self.has_prev
        }