from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from typing import Dict, Any, Optional
import os
import shutil
import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime
from pathlib import Path

from backend.models.schemas import ApiResponse, ResponseStatus, SaveFileRequest
from backend.core.exceptions import BaseAppException, SessionError, FileOperationError, ValidationError
from backend.services.session_service import session_service
from backend.services.file_service import file_service
from backend.core.security import security_validator
from backend.core.config import settings

# 创建路由器
router = APIRouter(tags=["save-file"])

# 创建限流器
limiter = Limiter(key_func=get_remote_address)

# 文件锁字典，用于并发控制
file_locks: Dict[str, asyncio.Lock] = {}


class FileBackupManager:
    """文件备份管理器"""
    
    def __init__(self, backup_dir: str = None):
        self.backup_dir = backup_dir or os.path.join(settings.temp_dir, "backups")
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def _get_backup_path(self, session_id: str, file_path: str, timestamp: str) -> str:
        """获取备份文件路径"""
        # 创建安全的文件名
        safe_filename = file_path.replace("/", "_").replace("\\", "_")
        backup_filename = f"{session_id}_{safe_filename}_{timestamp}.bak"
        return os.path.join(self.backup_dir, backup_filename)
    
    async def create_backup(self, session_id: str, file_path: str, content: str, encoding: str = "utf-8") -> str:
        """创建文件备份"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_path = self._get_backup_path(session_id, file_path, timestamp)
        
        try:
            with open(backup_path, 'w', encoding=encoding) as f:
                f.write(content)
            
            logging.info(f"File backup created for session {session_id}, file {file_path}, backup {backup_path}")
            
            return backup_path
        except Exception as e:
            logging.error(f"Failed to create backup for session {session_id}, file {file_path}: {str(e)}")
            raise
    
    async def cleanup_old_backups(self, session_id: str, max_backups: int = 10):
        """清理旧备份文件"""
        try:
            backup_files = []
            for filename in os.listdir(self.backup_dir):
                if filename.startswith(f"{session_id}_") and filename.endswith(".bak"):
                    file_path = os.path.join(self.backup_dir, filename)
                    backup_files.append((file_path, os.path.getmtime(file_path)))
            
            # 按修改时间排序，保留最新的备份
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            # 删除超出限制的备份
            for file_path, _ in backup_files[max_backups:]:
                os.remove(file_path)
                
        except Exception as e:
            logging.error(f"Failed to cleanup old backups for session {session_id}: {str(e)}")


class FileHistoryManager:
    """文件修改历史管理器"""
    
    def __init__(self, history_dir: str = None):
        self.history_dir = history_dir or os.path.join(settings.temp_dir, "history")
        os.makedirs(self.history_dir, exist_ok=True)
    
    def _get_history_file(self, session_id: str) -> str:
        """获取历史记录文件路径"""
        return os.path.join(self.history_dir, f"{session_id}_history.json")
    
    async def add_history_record(self, session_id: str, file_path: str, 
                               backup_path: str, content_hash: str, 
                               file_size: int, encoding: str):
        """添加历史记录"""
        history_file = self._get_history_file(session_id)
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "file_path": file_path,
            "backup_path": backup_path,
            "content_hash": content_hash,
            "file_size": file_size,
            "encoding": encoding,
            "version": 1
        }
        
        try:
            # 读取现有历史记录
            history = []
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            
            # 计算版本号
            file_history = [h for h in history if h["file_path"] == file_path]
            if file_history:
                record["version"] = max(h["version"] for h in file_history) + 1
            
            # 添加新记录
            history.append(record)
            
            # 保存历史记录
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logging.error(f"Failed to add history record for session {session_id}, file {file_path}: {str(e)}")
            raise


# 创建管理器实例
backup_manager = FileBackupManager()
history_manager = FileHistoryManager()


def get_file_lock(lock_key: str) -> asyncio.Lock:
    """获取文件锁"""
    if lock_key not in file_locks:
        file_locks[lock_key] = asyncio.Lock()
    return file_locks[lock_key]


def calculate_content_hash(content: str) -> str:
    """计算内容哈希值"""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


async def verify_file_integrity(file_path: str, expected_content: str, encoding: str = "utf-8") -> bool:
    """验证文件完整性"""
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            actual_content = f.read()
        return actual_content == expected_content
    except Exception:
        return False


@router.post(
    "/save-file",
    response_model=ApiResponse[Dict[str, Any]],
    summary="保存文件内容",
    description="保存修改后的文件内容，支持备份、版本控制和并发锁"
)
@limiter.limit("30/minute")
async def save_file_content(
    request: Request,
    save_request: SaveFileRequest
) -> ApiResponse[Dict[str, Any]]:
    """保存文件内容
    
    Args:
        request: FastAPI请求对象
        save_request: 保存请求
        
    Returns:
        ApiResponse[Dict[str, Any]]: 保存结果
    """
    # 创建文件锁键
    lock_key = f"{save_request.session_id}:{save_request.file_path}"
    file_lock = get_file_lock(lock_key)
    
    async with file_lock:
        try:
            # 验证会话
            session_info = await session_service.get_session(save_request.session_id)
            if not session_info:
                raise HTTPException(
                    status_code=404,
                    detail="会话不存在"
                )
            
            # 验证文件路径安全性
            if not security_validator.validate_file_path(save_request.file_path):
                raise HTTPException(
                    status_code=400,
                    detail="文件路径无效"
                )
            
            start_time = time.time()
            # 获取原始文件内容（用于备份）
            original_content = None
            original_encoding = save_request.encoding or "utf-8"
            
            try:
                # 尝试获取现有文件内容
                file_content = await file_service.get_file_content_enhanced(
                    save_request.file_path
                )
                original_content = file_content.content
                original_encoding = file_content.encoding or original_encoding
            except Exception:
                # 文件不存在或读取失败，使用空内容
                original_content = ""
            
            # 创建备份
            backup_path = None
            if original_content:
                backup_path = await backup_manager.create_backup(
                    save_request.session_id,
                    save_request.file_path,
                    original_content,
                    original_encoding
                )
            
            # 保存新文件内容
            file_type = session_info.metadata.get("file_type", "epub")
            
            if file_type == "text":
                # TEXT文件处理
                session_dir = session_info.metadata.get("session_dir")
                if not session_dir:
                    raise HTTPException(status_code=500, detail="会话目录不存在")
                
                full_file_path = Path(session_dir) / save_request.file_path
                
                # 确保目录存在
                os.makedirs(full_file_path.parent, exist_ok=True)
                
                # 保存文件
                with open(full_file_path, 'w', encoding=original_encoding) as f:
                    f.write(save_request.content)
                
                # 获取文件信息
                file_stat = full_file_path.stat()
                file_size = file_stat.st_size
                last_modified = file_stat.st_mtime
                
            else:
                # EPUB文件处理
                from backend.services.epub_service import epub_service
                result = await epub_service.save_file_content(
                    session_id=save_request.session_id,
                    file_path=save_request.file_path,
                    content=save_request.content,
                    encoding=original_encoding
                )
                
                # 获取文件信息
                file_size = len(save_request.content.encode(original_encoding))
                last_modified = datetime.now().timestamp()
            
            # 验证文件完整性
            integrity_check = await verify_file_integrity(
                str(full_file_path) if file_type == "text" else save_request.file_path,
                save_request.content,
                original_encoding
            )
            
            if not integrity_check:
                logging.warning(f"File integrity check failed for session {save_request.session_id}, file {save_request.file_path}")
            
            # 计算内容哈希
            content_hash = calculate_content_hash(save_request.content)
            
            # 记录修改历史
            await history_manager.add_history_record(
                save_request.session_id,
                save_request.file_path,
                backup_path or "",
                content_hash,
                file_size,
                original_encoding
            )
            
            # 清理旧备份
            await backup_manager.cleanup_old_backups(save_request.session_id)
            
            # 清理预览缓存
            from backend.services.preview_service import preview_service
            await preview_service.clear_preview_cache(save_request.session_id)
            
            # 记录操作日志
            logging.info(f"File saved successfully for session {save_request.session_id}, file {save_request.file_path}, backup: {backup_path}, hash: {content_hash}")
            
            return ApiResponse(
                status=ResponseStatus.SUCCESS,
                message="文件保存成功",
                data={
                    "file_path": save_request.file_path,
                    "size": file_size,
                    "last_modified": last_modified,
                    "encoding": original_encoding,
                    "content_hash": content_hash,
                    "backup_created": backup_path is not None,
                    "backup_path": backup_path,
                    "integrity_verified": integrity_check,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logging.error(f"Failed to save file for session {save_request.session_id}, file {save_request.file_path}: {str(e)}")
            
            raise HTTPException(
                status_code=500,
                detail=f"文件保存失败: {str(e)}"
            )


@router.get(
    "/file-history/{session_id}",
    response_model=ApiResponse[Dict[str, Any]],
    summary="获取文件修改历史",
    description="获取指定会话的文件修改历史记录"
)
@limiter.limit("10/minute")
async def get_file_history(
    request: Request,
    session_id: str,
    file_path: str = None
) -> ApiResponse[Dict[str, Any]]:
    """获取文件修改历史
    
    Args:
        request: FastAPI请求对象
        session_id: 会话ID
        file_path: 可选的文件路径过滤
        
    Returns:
        ApiResponse[Dict[str, Any]]: 历史记录
    """
    try:
        # 验证会话
        session_info = await session_service.get_session(session_id)
        if not session_info:
            raise HTTPException(
                status_code=404,
                detail="会话不存在"
            )
        
        history_file = history_manager._get_history_file(session_id)
        
        if not os.path.exists(history_file):
            return ApiResponse(
                status=ResponseStatus.SUCCESS,
                message="暂无修改历史",
                data={"history": []}
            )
        
        # 读取历史记录
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
        
        # 过滤特定文件的历史记录
        if file_path:
            history = [h for h in history if h["file_path"] == file_path]
        
        # 按时间倒序排列
        history.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return ApiResponse(
            status=ResponseStatus.SUCCESS,
            message="获取历史记录成功",
            data={
                "history": history,
                "total_count": len(history)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        security_logger.log_error(
            "Failed to get file history",
            e,
            session_id=session_id
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"获取历史记录失败: {str(e)}"
        )