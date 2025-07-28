"""会话管理服务"""

import asyncio
import time
import uuid
import json
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta

from backend.services.base import BaseService
from backend.models.session import Session
from backend.models.schemas import ResponseStatus, ErrorCode
from backend.core.config import settings
from backend.core.security import security_validator


class SessionService(BaseService):
    """会话管理服务"""
    
    def __init__(self):
        super().__init__("session")
        self.sessions: Dict[str, Session] = {}
        self.session_data: Dict[str, Dict[str, Any]] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._redis_client = None
    
    async def _initialize(self):
        """初始化服务"""
        # 尝试连接Redis（可选）
        try:
            import redis.asyncio as redis
            self._redis_client = redis.from_url(
                settings.redis_url,
                db=settings.redis_db,
                password=settings.redis_password,
                decode_responses=True
            )
            # 测试连接
            await self._redis_client.ping()
            self.log_info("Redis connected successfully")
        except Exception as e:
            self.log_warning("Redis connection failed, using memory storage", error=str(e))
            self._redis_client = None
        
        # 启动清理任务
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_sessions())
        self.log_info("Session service initialized")
    
    async def _cleanup(self):
        """清理服务"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self._redis_client:
            await self._redis_client.close()
        
        self.sessions.clear()
        self.session_data.clear()
        self.log_info("Session service cleaned up")
    
    async def create_session(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """创建新会话
        
        Args:
            metadata: 会话元数据
            
        Returns:
            str: 会话ID
        """
        # 检查会话数量限制
        if len(self.sessions) >= settings.max_sessions:
            # 清理过期会话
            await self._cleanup_expired_sessions_sync()
            
            # 如果仍然超过限制，拒绝创建
            if len(self.sessions) >= settings.max_sessions:
                raise Exception("会话数量已达上限")
        
        # 生成会话ID
        session_id = str(uuid.uuid4())
        
        # 创建会话信息
        now = datetime.now()
        session = Session(
            session_id=session_id,
            epub_path=metadata.get('extraction_path', '') if metadata else '',
            upload_time=now,
            last_accessed=now,
            expires_at=now + timedelta(seconds=settings.session_timeout),
            original_filename=metadata.get('original_filename') if metadata else None,
            file_size=metadata.get('file_size') if metadata else None,
            extracted_path=metadata.get('extraction_path') if metadata else None,
            metadata=metadata or {}
        )
        
        # 存储会话
        await self._store_session(session_id, session)
        
        self.log_info("Session created", session_id=session_id)
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话信息
        
        Args:
            session_id: 会话ID
            
        Returns:
            Optional[Session]: 会话信息
        """
        try:
            security_validator.validate_session_id(session_id)
        except Exception:
            # 如果会话ID验证失败，返回None而不是抛出异常
            return None
        
        session = await self._load_session(session_id)
        if not session:
            return None
        
        # 检查会话是否过期
        if session.expires_at < datetime.now():
            await self.delete_session(session_id)
            return None
        
        # 更新最后访问时间
        session.last_accessed = datetime.now()
        await self._store_session(session_id, session)
        
        return session
    
    async def update_session(self, session_id: str, metadata: Dict[str, Any]) -> bool:
        """更新会话元数据
        
        Args:
            session_id: 会话ID
            metadata: 新的元数据
            
        Returns:
            bool: 是否更新成功
        """
        session = await self.get_session(session_id)
        if not session:
            return False
        
        # 更新元数据
        session.metadata.update(metadata)
        session.last_accessed = datetime.now()
        
        # 存储更新后的会话
        await self._store_session(session_id, session)
        
        self.log_info("Session updated", session_id=session_id)
        return True
    
    async def extend_session(self, session_id: str, extend_seconds: Optional[int] = None) -> bool:
        """延长会话有效期
        
        Args:
            session_id: 会话ID
            extend_seconds: 延长秒数，默认使用配置的超时时间
            
        Returns:
            bool: 是否延长成功
        """
        session = await self.get_session(session_id)
        if not session:
            return False
        
        # 延长过期时间
        extend_time = extend_seconds or settings.session_timeout
        session.expires_at = datetime.now() + timedelta(seconds=extend_time)
        session.last_accessed = datetime.now()
        
        # 存储更新后的会话
        await self._store_session(session_id, session)
        
        self.log_info("Session extended", session_id=session_id, extend_seconds=extend_time)
        return True
    
    async def delete_session(self, session_id: str) -> bool:
        """删除会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            # 从存储中删除
            if self._redis_client:
                await self._redis_client.delete(f"session:{session_id}")
                await self._redis_client.delete(f"session_data:{session_id}")
            
            # 从内存中删除
            self.sessions.pop(session_id, None)
            self.session_data.pop(session_id, None)
            
            self.log_info("Session deleted", session_id=session_id)
            return True
            
        except Exception as e:
            self.log_error("Failed to delete session", e, session_id=session_id)
            return False
    
    async def set_session_data(self, session_id: str, key: str, value: Any) -> bool:
        """设置会话数据
        
        Args:
            session_id: 会话ID
            key: 数据键
            value: 数据值
            
        Returns:
            bool: 是否设置成功
        """
        session = await self.get_session(session_id)
        if not session:
            return False
        
        try:
            # 获取或创建会话数据
            if session_id not in self.session_data:
                self.session_data[session_id] = {}
            
            self.session_data[session_id][key] = value
            
            # 如果使用Redis，同步到Redis
            if self._redis_client:
                data_key = f"session_data:{session_id}"
                await self._redis_client.hset(data_key, key, json.dumps(value, default=str))
                await self._redis_client.expire(data_key, settings.session_timeout)
            
            return True
            
        except Exception as e:
            self.log_error("Failed to set session data", e, session_id=session_id, key=key)
            return False
    
    async def get_session_data(self, session_id: str, key: str, default: Any = None) -> Any:
        """获取会话数据
        
        Args:
            session_id: 会话ID
            key: 数据键
            default: 默认值
            
        Returns:
            Any: 数据值
        """
        session = await self.get_session(session_id)
        if not session:
            return default
        
        try:
            # 先从内存获取
            if session_id in self.session_data and key in self.session_data[session_id]:
                return self.session_data[session_id][key]
            
            # 如果使用Redis，从Redis获取
            if self._redis_client:
                data_key = f"session_data:{session_id}"
                value = await self._redis_client.hget(data_key, key)
                if value is not None:
                    try:
                        parsed_value = json.loads(value)
                        # 同步到内存
                        if session_id not in self.session_data:
                            self.session_data[session_id] = {}
                        self.session_data[session_id][key] = parsed_value
                        return parsed_value
                    except json.JSONDecodeError:
                        return value
            
            return default
            
        except Exception as e:
            self.log_error("Failed to get session data", e, session_id=session_id, key=key)
            return default
    
    async def delete_session_data(self, session_id: str, key: str) -> bool:
        """删除会话数据
        
        Args:
            session_id: 会话ID
            key: 数据键
            
        Returns:
            bool: 是否删除成功
        """
        try:
            # 从内存删除
            if session_id in self.session_data:
                self.session_data[session_id].pop(key, None)
            
            # 从Redis删除
            if self._redis_client:
                data_key = f"session_data:{session_id}"
                await self._redis_client.hdel(data_key, key)
            
            return True
            
        except Exception as e:
            self.log_error("Failed to delete session data", e, session_id=session_id, key=key)
            return False
    
    async def list_sessions(self) -> List[Session]:
        """列出所有活跃会话
        
        Returns:
            List[Session]: 会话信息列表
        """
        sessions = []
        now = datetime.now()
        
        # 从内存获取
        for session in self.sessions.values():
            if session and session.expires_at and session.expires_at > now:
                sessions.append(session)
        
        # 如果使用Redis，还需要从Redis获取
        if self._redis_client:
            try:
                keys = await self._redis_client.keys("session:*")
                for key in keys:
                    session_id = key.split(":", 1)[1]
                    if session_id not in self.sessions:
                        session = await self._load_session(session_id)
                        if session and session.expires_at and session.expires_at > now:
                            sessions.append(session)
            except Exception as e:
                self.log_error("Failed to list Redis sessions", e)
        
        return sessions
    
    async def _store_session(self, session_id: str, session: Session):
        """存储会话信息"""
        # 存储到内存
        self.sessions[session_id] = session
        
        # 存储到Redis
        if self._redis_client:
            try:
                session_key = f"session:{session_id}"
                session_data = {
                    "session_id": session.session_id,
                    "created_at": session.upload_time.isoformat(),
                    "last_accessed": session.last_accessed.isoformat(),
                    "expires_at": session.expires_at.isoformat(),
                    "epub_path": session.epub_path,
                    "original_filename": session.original_filename or "",
                    "file_size": str(session.file_size or 0),
                    "extracted_path": session.extracted_path or "",
                    "metadata": json.dumps(session.metadata)
                }
                
                await self._redis_client.hset(session_key, mapping=session_data)
                await self._redis_client.expire(session_key, settings.session_timeout)
                
            except Exception as e:
                self.log_error("Failed to store session to Redis", e, session_id=session_id)
    
    async def _load_session(self, session_id: str) -> Optional[Session]:
        """加载会话信息"""
        # 先从内存获取
        if session_id in self.sessions:
            return self.sessions[session_id]
        
        # 从Redis获取
        if self._redis_client:
            try:
                session_key = f"session:{session_id}"
                session_data = await self._redis_client.hgetall(session_key)
                
                if session_data and all(key in session_data for key in ["session_id", "created_at", "last_accessed", "expires_at"]):
                    # 安全地解析时间字段
                    try:
                        upload_time = datetime.fromisoformat(session_data["created_at"])
                        last_accessed = datetime.fromisoformat(session_data["last_accessed"])
                        expires_at = datetime.fromisoformat(session_data["expires_at"])
                    except (ValueError, TypeError) as e:
                        self.log_error("Failed to parse datetime fields", e, session_id=session_id)
                        return None
                    
                    # 安全地解析元数据
                    try:
                        metadata = json.loads(session_data.get("metadata", "{}"))
                    except (json.JSONDecodeError, TypeError):
                        metadata = {}
                    
                    session = Session(
                        session_id=session_data["session_id"],
                        epub_path=session_data.get("epub_path", ""),
                        upload_time=upload_time,
                        last_accessed=last_accessed,
                        expires_at=expires_at,
                        original_filename=session_data.get("original_filename") or None,
                        file_size=int(session_data.get("file_size", 0)) or None,
                        extracted_path=session_data.get("extracted_path") or None,
                        metadata=metadata
                    )
                    
                    # 同步到内存
                    self.sessions[session_id] = session
                    return session
                    
            except Exception as e:
                self.log_error("Failed to load session from Redis", e, session_id=session_id)
        
        return None
    
    async def _cleanup_expired_sessions(self):
        """定期清理过期会话"""
        while True:
            try:
                await asyncio.sleep(settings.cleanup_interval)
                await self._cleanup_expired_sessions_sync()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log_error("Error in session cleanup task", e)
    
    async def _cleanup_expired_sessions_sync(self):
        """同步清理过期会话"""
        now = datetime.now()
        expired_sessions = []
        
        # 查找过期会话
        for session_id, session in self.sessions.items():
            if session and session.expires_at and session.expires_at < now:
                expired_sessions.append(session_id)
        
        # 删除过期会话
        for session_id in expired_sessions:
            await self.delete_session(session_id)
        
        if expired_sessions:
            self.log_info("Cleaned up expired sessions", count=len(expired_sessions))
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """获取会话统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        now = datetime.now()
        active_sessions = 0
        total_sessions = len(self.sessions)
        
        for session in self.sessions.values():
            if session and session.expires_at and session.expires_at > now:
                active_sessions += 1
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "expired_sessions": total_sessions - active_sessions,
            "max_sessions": settings.max_sessions,
            "session_timeout": settings.session_timeout,
            "cleanup_interval": settings.cleanup_interval,
            "redis_enabled": self._redis_client is not None
        }
    
    async def cleanup_expired_sessions(self) -> int:
        """Public method to cleanup expired sessions.
        
        Returns:
            int: Number of sessions cleaned up
        """
        now = datetime.now()
        expired_sessions = []
        
        # 查找过期会话
        for session_id, session in self.sessions.items():
            if session and session.expires_at and session.expires_at < now:
                expired_sessions.append(session_id)
        
        # 删除过期会话
        for session_id in expired_sessions:
            await self.delete_session(session_id)
        
        if expired_sessions:
            self.log_info("Cleaned up expired sessions", count=len(expired_sessions))
        
        return len(expired_sessions)


# 创建全局服务实例
session_service = SessionService()


# 导出
__all__ = ["SessionService", "session_service"]