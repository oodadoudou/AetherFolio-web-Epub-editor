"""文件保存API路由"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from services.epub_service import epub_service
from services.text_service import text_service
from services.session_service import session_service
from core.logging import performance_logger
from .backup import BackupService

router = APIRouter(prefix="/api/v1", tags=["save-file"])


class SaveFileRequest(BaseModel):
    """保存文件请求模型"""
    session_id: str
    file_path: str
    content: str
    encoding: Optional[str] = "utf-8"


@router.post("/save-file")
async def save_file(request: SaveFileRequest):
    """保存文件内容"""
    try:
        # 获取会话信息以确定文件类型
        session = await session_service.get_session(request.session_id)
        if not session:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "会话不存在"
                }
            )
        
        # 确定文件类型
        session_metadata = session.get('session_metadata', {})
        is_text_file = session_metadata.get("file_type") == "text"
        
        # 在保存前创建备份（如果文件已存在）
        backup_created = False
        try:
            # 获取当前文件内容用于备份
            current_content = None
            
            if is_text_file:
                # 对于TEXT文件，直接读取
                from pathlib import Path
                session_dir = Path("backend/sessions") / request.session_id
                current_file_path = session_dir / request.file_path
                if current_file_path.exists():
                    with open(current_file_path, 'r', encoding=request.encoding) as f:
                        current_content = f.read()
            else:
                # 对于EPUB文件，使用epub_service获取内容
                try:
                    file_content_obj = await epub_service.get_file_content(
                        session_id=request.session_id,
                        file_path=request.file_path
                    )
                    if file_content_obj and hasattr(file_content_obj, 'content'):
                        current_content = file_content_obj.content
                        performance_logger.info(
                            f"Retrieved current content for backup: {len(current_content)} chars",
                            extra={
                                "session_id": request.session_id,
                                "file_path": request.file_path
                            }
                        )
                except Exception as e:
                    # 如果获取失败，说明文件可能不存在，不需要备份
                    performance_logger.info(
                        f"Could not retrieve current content for backup: {str(e)}",
                        extra={
                            "session_id": request.session_id,
                            "file_path": request.file_path
                        }
                    )
            
            # 如果有当前内容，创建备份
            if current_content is not None:
                BackupService.create_backup(request.session_id, request.file_path, current_content)
                backup_created = True
                
        except Exception as e:
            # 备份失败不应该阻止保存操作
            performance_logger.warning(
                f"Backup creation failed: {str(e)}",
                extra={
                    "session_id": request.session_id,
                    "file_path": request.file_path
                }
            )
        
        # 根据会话类型选择合适的服务
        if is_text_file:
            # 对于TEXT文件，直接写入session目录
            from pathlib import Path
            from core.config import settings
            import os
            
            session_dir = Path("backend/sessions") / request.session_id
            safe_path = session_dir / request.file_path
            
            # 确保目录存在
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存文件
            with open(safe_path, 'w', encoding=request.encoding) as f:
                f.write(request.content)
            
            # 获取文件信息
            file_stat = os.stat(safe_path)
            result = {
                "size": file_stat.st_size,
                "last_modified": file_stat.st_mtime
            }
        else:
            # 对于EPUB文件，使用epub_service
            result = await epub_service.save_file_content(
                session_id=request.session_id,
                file_path=request.file_path,
                content=request.content,
                encoding=request.encoding
            )
        
        performance_logger.info(
            f"File saved successfully",
            extra={
                "session_id": request.session_id,
                "file_path": request.file_path,
                "content_length": len(request.content)
            }
        )
        
        return JSONResponse(
            content={
                "success": True,
                "message": "文件保存成功",
                "backup_created": backup_created,
                "last_modified": result.get("last_modified")
            }
        )
        
    except FileNotFoundError:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": "文件不存在"
            }
        )
    except PermissionError:
        return JSONResponse(
            status_code=403,
            content={
                "success": False,
                "error": "无权限保存该文件"
            }
        )
    except Exception as e:
        performance_logger.error(
            f"Save file failed: {str(e)}",
            extra={
                "session_id": request.session_id,
                "file_path": request.file_path
            }
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "文件保存失败"
            }
        )