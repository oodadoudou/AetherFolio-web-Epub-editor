"""文件备份API路由"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import json
import shutil
from pathlib import Path
from datetime import datetime

from services.session_service import session_service
from core.config import settings
from core.logging import performance_logger

router = APIRouter(prefix="/api/v1", tags=["backup"])


class BackupFileInfo(BaseModel):
    """备份文件信息模型"""
    backup_path: str
    original_path: str
    created_at: str
    size: int


class BackupService:
    """备份服务类"""
    
    @staticmethod
    def get_backup_dir(session_id: str) -> Path:
        """获取备份目录"""
        # 使用session_service获取正确的会话目录
        session_dir = session_service.get_session_dir(session_id, "unknown")
        backup_dir = session_dir / ".backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir
    
    @staticmethod
    def create_backup(session_id: str, file_path: str, content: str) -> str:
        """创建备份文件"""
        backup_dir = BackupService.get_backup_dir(session_id)
        
        # 生成备份文件名：原文件名_时间戳.bak
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = Path(file_path).name
        backup_filename = f"{file_name}_{timestamp}.bak"
        backup_path = backup_dir / backup_filename
        
        # 保存备份内容
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 保存备份元数据
        metadata = {
            "original_path": file_path,
            "backup_path": str(backup_path.relative_to(backup_dir.parent)),
            "created_at": datetime.now().isoformat(),
            "size": len(content.encode('utf-8'))
        }
        
        metadata_path = backup_path.with_suffix('.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        return str(backup_path.relative_to(backup_dir.parent))
    
    @staticmethod
    def list_backups(session_id: str) -> List[BackupFileInfo]:
        """列出所有备份文件"""
        backup_dir = BackupService.get_backup_dir(session_id)
        backups = []
        
        for metadata_file in backup_dir.glob("*.json"):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                backups.append(BackupFileInfo(
                    backup_path=metadata["backup_path"],
                    original_path=metadata["original_path"],
                    created_at=metadata["created_at"],
                    size=metadata["size"]
                ))
            except Exception as e:
                performance_logger.warning(f"Failed to read backup metadata: {e}")
                continue
        
        # 按创建时间排序
        backups.sort(key=lambda x: x.created_at, reverse=True)
        return backups
    
    @staticmethod
    def get_backup_content(session_id: str, backup_path: str) -> str:
        """获取备份文件内容"""
        # 使用session_service获取正确的会话目录
        session_dir = session_service.get_session_dir(session_id, "unknown")
        full_backup_path = session_dir / backup_path
        
        if not full_backup_path.exists():
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")
        
        with open(full_backup_path, 'r', encoding='utf-8') as f:
            return f.read()


@router.get("/backup-files")
async def get_backup_files(session_id: str = Query(..., description="会话ID")):
    """获取备份文件列表"""
    try:
        # 验证会话是否存在
        session = await session_service.get_session(session_id)
        if not session:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "会话不存在"
                }
            )
        
        # 获取备份文件列表
        backups = BackupService.list_backups(session_id)
        
        return JSONResponse(
            content={
                "success": True,
                "backup_files": [backup.model_dump() for backup in backups],
                "total_count": len(backups)
            }
        )
        
    except Exception as e:
        performance_logger.error(
            f"Failed to get backup files: {str(e)}",
            extra={"session_id": session_id}
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "获取备份文件列表失败"
            }
        )


@router.get("/backup-content")
async def get_backup_content(
    session_id: str = Query(..., description="会话ID"),
    backup_path: str = Query(..., description="备份文件路径")
):
    """获取备份文件内容"""
    try:
        # 验证会话是否存在
        session = await session_service.get_session(session_id)
        if not session:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "会话不存在"
                }
            )
        
        # 获取备份文件内容
        content = BackupService.get_backup_content(session_id, backup_path)
        
        return JSONResponse(
            content={
                "success": True,
                "content": content,
                "backup_path": backup_path
            }
        )
        
    except FileNotFoundError as e:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": str(e)
            }
        )
    except Exception as e:
        performance_logger.error(
            f"Failed to get backup content: {str(e)}",
            extra={"session_id": session_id, "backup_path": backup_path}
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "获取备份文件内容失败"
            }
        )