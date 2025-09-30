"""会话管理服务 - 物理文件存储版本"""

import asyncio
import uuid
import json
import os
import shutil
from pathlib import Path
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from fastapi import HTTPException
from threading import Lock

from services.base import BaseService
from core.config import settings
from core.security import security_validator


class SessionService(BaseService):
    """会话管理服务 - 物理文件存储版本"""
    
    def __init__(self):
        super().__init__("session")
        self._lock = Lock()  # 线程安全锁
        # 使用容器内的data目录
        # 在Docker环境中，数据目录挂载在/app/data
        app_root = Path(__file__).parent.parent  # /app
        self.session_base_dir = app_root / "data" / "session"
        
        # 确保session目录存在
        self.session_base_dir.mkdir(parents=True, exist_ok=True)
        (self.session_base_dir / "epub").mkdir(exist_ok=True)
        (self.session_base_dir / "txt").mkdir(exist_ok=True)
        (self.session_base_dir / "temp").mkdir(exist_ok=True)
        
        self.log_info("会话服务初始化完成（物理文件存储）")
    
    async def _initialize(self):
        """初始化服务"""
        self.log_info("Session service initialized (file storage)")
    
    async def _cleanup(self):
        """清理服务"""
        self.log_info("Session service cleaned up")
    
    async def create_session(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """创建新会话
        
        Args:
            metadata: 会话元数据
            
        Returns:
            str: 会话ID
        """
        # 生成会话ID
        session_id = str(uuid.uuid4())
        
        # 创建会话信息
        now = datetime.utcnow()
        
        try:
            with self._lock:
                # 检查会话数量限制
                active_sessions = await self._get_active_sessions_count()
                
                if active_sessions >= settings.max_sessions:
                    raise Exception("会话数量已达上限")
                
                # 确定文件类型和会话目录
                file_type = metadata.get('file_type', 'unknown') if metadata else 'unknown'
                session_dir = self._get_session_dir_path(session_id, file_type)
                session_dir.mkdir(parents=True, exist_ok=True)
                
                # 创建会话记录（永久有效直到主动删除）
                session_data = {
                    'session_id': session_id,
                    'epub_path': metadata.get('extracted_path', '') if metadata else '',
                    'upload_time': now.isoformat(),
                    'last_accessed': now.isoformat(),
                    'status': 'active',
                    'original_filename': metadata.get('original_filename') if metadata else None,
                    'file_size': metadata.get('file_size') if metadata else None,
                    'extracted_path': str(session_dir) if metadata else None,
                    'session_metadata': metadata or {},
                    'file_type': file_type
                }
                
                # 保存会话数据到文件
                session_file = session_dir / "session.json"
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, ensure_ascii=False, indent=2, default=str)
                
                # 详细的会话创建日志
                self.log_info(f"Session created successfully", 
                             session_id=session_id, 
                             session_dir=str(session_dir),
                             metadata=metadata)
                
                # 立即验证会话是否可以被访问
                if session_file.exists():
                    self.log_info(f"Session creation verified - session accessible", 
                                 session_id=session_id,
                                 status=session_data.get('status'))
                else:
                    self.log_error(f"Session creation failed - session file not accessible", 
                                  session_id=session_id)
                
                return session_id
                
        except Exception as e:
            self.log_error("Failed to create session", e, session_id=session_id)
            raise
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息
        
        Args:
            session_id: 会话ID
            
        Returns:
            Optional[Dict[str, Any]]: 会话信息字典
        """
        try:
            security_validator.validate_session_id(session_id)
        except Exception as e:
            self.log_error(f"Invalid session ID format: {session_id}", e)
            return None
        
        try:
            with self._lock:
                # 查找会话文件
                session_file = self._find_session_file(session_id)
                
                if not session_file or not session_file.exists():
                    self.log_info(f"Session not found in file storage", 
                                 session_id=session_id)
                    return None
                
                # 读取会话数据
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                
                # 检查会话状态
                if session_data.get('status') != 'active':
                    self.log_info(f"Session found but not active", session_id=session_id, status=session_data.get('status'))
                    return None
                
                # 更新最后访问时间
                now = datetime.utcnow()
                session_data['last_accessed'] = now.isoformat()
                
                # 保存更新后的会话数据
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, ensure_ascii=False, indent=2, default=str)
                
                # 转换时间字符串为datetime对象（为了兼容性）
                if isinstance(session_data.get('upload_time'), str):
                    session_data['upload_time'] = datetime.fromisoformat(session_data['upload_time'])
                if isinstance(session_data.get('last_accessed'), str):
                    session_data['last_accessed'] = datetime.fromisoformat(session_data['last_accessed'])
                
                self.log_info(f"Session found and accessed successfully", 
                             session_id=session_id, 
                             last_accessed=now,
                             session_status=session_data.get('status'),
                             original_filename=session_data.get('original_filename'))
                
                return session_data
                
        except Exception as e:
            self.log_error("Failed to get session", e, session_id=session_id)
            return None
    
    def _get_session_dir_path(self, session_id: str, file_type: str) -> Path:
        """获取会话目录路径
        
        Args:
            session_id: 会话ID
            file_type: 文件类型 (epub, txt, temp, unknown)
            
        Returns:
            Path: 会话目录路径
        """
        if file_type in ['epub', 'txt', 'temp']:
            return self.session_base_dir / file_type / session_id
        else:
            return self.session_base_dir / "txt" / session_id  # 默认为txt类型
    
    def _find_session_file(self, session_id: str) -> Optional[Path]:
        """查找会话文件
        
        Args:
            session_id: 会话ID
            
        Returns:
            Optional[Path]: 会话文件路径
        """
        # 在epub、txt和temp目录中查找
        for file_type in ['epub', 'txt', 'temp']:
            session_file = self.session_base_dir / file_type / session_id / "session.json"
            if session_file.exists():
                return session_file
        return None
    
    async def _get_active_sessions_count(self) -> int:
        """获取活跃会话数量
        
        Returns:
            int: 活跃会话数量
        """
        count = 0
        for file_type in ['epub', 'txt']:
            type_dir = self.session_base_dir / file_type
            if type_dir.exists():
                for session_dir in type_dir.iterdir():
                    if session_dir.is_dir():
                        session_file = session_dir / "session.json"
                        if session_file.exists():
                            try:
                                with open(session_file, 'r', encoding='utf-8') as f:
                                    session_data = json.load(f)
                                if session_data.get('status') == 'active':
                                    count += 1
                            except Exception:
                                continue
        return count

    async def update_session(self, session_id: str, metadata: Dict[str, Any]) -> bool:
        """更新会话元数据
        
        Args:
            session_id: 会话ID
            metadata: 新的元数据
            
        Returns:
            bool: 是否更新成功
        """
        try:
            with self._lock:
                session_file = self._find_session_file(session_id)
                if not session_file or not session_file.exists():
                    return False
                
                # 读取现有会话数据
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                
                # 获取现有元数据
                existing_metadata = session_data['session_metadata']
                
                # 更新元数据
                existing_metadata.update(metadata)
                
                # 更新数据
                now = datetime.utcnow()
                session_data['session_metadata'] = existing_metadata
                session_data['last_accessed'] = now.isoformat()
                
                # 保存更新后的会话数据
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, ensure_ascii=False, indent=2, default=str)
                
                self.log_info("Session updated", session_id=session_id)
                return True
                
        except Exception as e:
            self.log_error("Failed to update session", e, session_id=session_id)
            return False
    
    async def extend_session(self, session_id: str, extend_seconds: Optional[int] = None) -> bool:
        """更新会话访问时间（会话永久有效）
        
        Args:
            session_id: 会话ID
            extend_seconds: 保留参数以兼容现有调用
            
        Returns:
            bool: 是否更新成功
        """
        try:
            with self._lock:
                session_file = self._find_session_file(session_id)
                if not session_file or not session_file.exists():
                    return False
                
                # 读取现有会话数据
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                
                # 仅更新最后访问时间
                now = datetime.utcnow()
                session_data['last_accessed'] = now.isoformat()
                
                # 保存更新后的会话数据
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, ensure_ascii=False, indent=2, default=str)
                
                self.log_info("Session accessed", session_id=session_id)
                return True
                
        except Exception as e:
            self.log_error("Failed to update session access time", e, session_id=session_id)
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """删除会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            with self._lock:
                session_file = self._find_session_file(session_id)
                if not session_file or not session_file.exists():
                    return False
                
                # 删除整个会话目录
                session_dir = session_file.parent
                if session_dir.exists():
                    shutil.rmtree(session_dir)
                
                self.log_info("Session deleted", session_id=session_id)
                return True
                
        except Exception as e:
            self.log_error("Failed to delete session", e, session_id=session_id)
            return False
    

    

    
    def _cleanup_expired_sessions_internal(self):
        """内部清理过期会话（不加锁，调用时需要已持有锁）
        基于last_accessed时间清理过期会话
        """
        try:
            from core.config import settings
            
            now = datetime.utcnow()
            cleaned_count = 0
            
            # 遍历所有会话目录
            for file_type in ['epub', 'txt']:
                type_dir = self.session_base_dir / file_type
                if not type_dir.exists():
                    continue
                
                for session_dir in type_dir.iterdir():
                    if not session_dir.is_dir():
                        continue
                    
                    session_file = session_dir / "session.json"
                    if not session_file.exists():
                        continue
                    
                    try:
                        # 读取会话数据
                        with open(session_file, 'r', encoding='utf-8') as f:
                            session_data = json.load(f)
                        
                        # 检查是否过期（基于last_accessed时间）
                        last_accessed_str = session_data.get('last_accessed')
                        if last_accessed_str:
                            last_accessed = datetime.fromisoformat(last_accessed_str)
                            time_diff = (now - last_accessed).total_seconds()
                            if time_diff > settings.session_timeout:
                                # 删除过期会话目录
                                shutil.rmtree(session_dir)
                                cleaned_count += 1
                                self.log_info(f"Session expired: {time_diff:.0f}s > {settings.session_timeout}s", session_id=session_dir.name)
                    
                    except Exception as e:
                        self.log_error(f"Failed to process session {session_dir.name}", e)
                        continue
            
            if cleaned_count > 0:
                self.log_info(f"Cleaned up {cleaned_count} expired sessions")
            
            return cleaned_count
                
        except Exception as e:
            self.log_error("Failed to cleanup expired sessions", e)
            return 0
    

    
    async def cleanup_expired_sessions(self) -> int:
        """手动清理过期会话
        基于last_accessed时间清理过期会话
        
        Returns:
            int: 清理的会话数量
        """
        try:
            with self._lock:
                cleaned_count = self._cleanup_expired_sessions_internal()
                if cleaned_count > 0:
                    self.log_info(f"Manual cleanup completed: {cleaned_count} sessions cleaned")
                return cleaned_count
                
        except Exception as e:
            self.log_error("Failed to cleanup expired sessions", e)
            return 0
    
    def _cleanup_session_files(self, session_id: str):
        """清理会话相关的文件
        
        Args:
            session_id: 会话ID
        """
        try:
            session_file = self._find_session_file(session_id)
            if session_file and session_file.exists():
                session_dir = session_file.parent
                shutil.rmtree(session_dir)
                self.log_info("Session files cleaned up", session_id=session_id)
        except Exception as e:
            self.log_error("Failed to cleanup session files", e, session_id=session_id)
    
    def get_session_dir(self, session_id: str, file_type: str = "unknown") -> str:
        """获取会话目录路径
        
        Args:
            session_id: 会话ID
            file_type: 文件类型 (text, epub, unknown)
            
        Returns:
            str: 会话目录路径
        """
        session_dir = self._get_session_dir_path(session_id, file_type)
        return str(session_dir)
    
    async def get_session_directory(self, session_id: str) -> Optional[str]:
        """获取会话目录路径（异步版本）
        
        Args:
            session_id: 会话ID
            
        Returns:
            Optional[str]: 会话目录路径，如果会话不存在则返回None
        """
        try:
            session_file = self._find_session_file(session_id)
            if session_file and session_file.exists():
                return str(session_file.parent)
            return None
        except Exception as e:
            self.log_error("Failed to get session directory", e, session_id=session_id)
            return None
    
    async def cleanup_session_on_disconnect(self, session_id: str) -> bool:
        """当用户断开连接时清理会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 是否清理成功
        """
        try:
            with self._lock:
                session_file = self._find_session_file(session_id)
                if not session_file or not session_file.exists():
                    return False
                
                # 读取会话数据
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                
                # 标记会话为已断开
                session_data['status'] = 'disconnected'
                session_data['disconnected_at'] = datetime.utcnow().isoformat()
                
                # 保存更新后的会话数据
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, ensure_ascii=False, indent=2, default=str)
                
                # 立即清理会话文件（可选，根据需求决定）
                # 如果希望立即清理，取消下面的注释
                # session_dir = session_file.parent
                # if session_dir.exists():
                #     shutil.rmtree(session_dir)
                
                self.log_info("Session marked as disconnected", session_id=session_id)
                return True
                
        except Exception as e:
            self.log_error("Failed to cleanup session on disconnect", e, session_id=session_id)
            return False
    
    async def cleanup_disconnected_sessions(self, max_age_hours: int = 1) -> int:
        """清理已断开连接的会话
        
        Args:
            max_age_hours: 断开连接后多少小时清理，默认1小时
            
        Returns:
            int: 清理的会话数量
        """
        try:
            with self._lock:
                now = datetime.utcnow()
                cleaned_count = 0
                
                # 遍历所有会话目录
                for file_type in ['epub', 'text']:
                    type_dir = self.session_base_dir / file_type
                    if not type_dir.exists():
                        continue
                    
                    for session_dir in type_dir.iterdir():
                        if not session_dir.is_dir():
                            continue
                        
                        session_file = session_dir / "session.json"
                        if not session_file.exists():
                            continue
                        
                        try:
                            # 读取会话数据
                            with open(session_file, 'r', encoding='utf-8') as f:
                                session_data = json.load(f)
                            
                            # 检查是否为已断开的会话
                            if session_data.get('status') == 'disconnected':
                                disconnected_at_str = session_data.get('disconnected_at')
                                if disconnected_at_str:
                                    disconnected_at = datetime.fromisoformat(disconnected_at_str)
                                    hours_since_disconnect = (now - disconnected_at).total_seconds() / 3600
                                    
                                    if hours_since_disconnect > max_age_hours:
                                        # 删除已断开的会话目录
                                        shutil.rmtree(session_dir)
                                        cleaned_count += 1
                                        self.log_info(f"Disconnected session cleaned: {hours_since_disconnect:.1f}h > {max_age_hours}h", 
                                                     session_id=session_dir.name)
                        
                        except Exception as e:
                            self.log_error(f"Failed to process disconnected session {session_dir.name}", e)
                            continue
                
                if cleaned_count > 0:
                    self.log_info(f"Cleaned up {cleaned_count} disconnected sessions")
                
                return cleaned_count
                
        except Exception as e:
            self.log_error("Failed to cleanup disconnected sessions", e)
            return 0


# 全局会话服务实例
session_service = SessionService()