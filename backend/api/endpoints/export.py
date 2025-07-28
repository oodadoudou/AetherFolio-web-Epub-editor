# Export endpoint
# Handles EPUB export and download

import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import Dict, Any

from backend.services.session_service import session_service
from backend.services.epub_service import epub_service
from backend.core.config import settings
from backend.core.logging import security_logger

router = APIRouter(prefix="/export", tags=["export"])


@router.get(
    "/{session_id}",
    summary="下载处理后的EPUB",
    description="下载经过批量替换处理的EPUB文件"
)
async def download_processed_epub(session_id: str):
    """下载处理后的EPUB文件
    
    Args:
        session_id: 会话ID
        
    Returns:
        FileResponse: EPUB文件
    """
    try:
        # 验证会话
        session_info = await session_service.get_session(session_id)
        if not session_info:
            raise HTTPException(
                status_code=404,
                detail={"success": False, "error": "会话不存在"}
            )
        
        # 获取处理后的EPUB文件路径
        epub_path = os.path.join(settings.session_dir, session_id, "processed.epub")
        
        # 如果处理后的文件不存在，尝试使用原始文件
        if not os.path.exists(epub_path):
            epub_path = os.path.join(settings.session_dir, session_id, "original.epub")
        
        if not os.path.exists(epub_path):
            raise HTTPException(
                status_code=404,
                detail={"success": False, "error": "EPUB文件不存在"}
            )
        
        # 记录下载操作
        security_logger.log_info(
            "EPUB file downloaded",
            session_id=session_id,
            file_path=epub_path
        )
        
        # 返回文件
        return FileResponse(
            path=epub_path,
            filename=f"processed_{session_id}.epub",
            media_type="application/epub+zip"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        security_logger.log_error(
            "Failed to download EPUB file",
            e,
            session_id=session_id
        )
        
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": "下载失败"}
        )