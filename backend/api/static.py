"""静态资源API路由"""

import os
import mimetypes
from pathlib import Path
from fastapi import APIRouter, HTTPException, Path as FastAPIPath
from fastapi.responses import Response
from typing import Optional

from services.session_service import session_service
from core.logging import performance_logger

router = APIRouter(prefix="/api/v1/static", tags=["static"])


@router.get("/epub/{session_id}/{file_path:path}")
async def get_epub_static_file(
    session_id: str = FastAPIPath(..., description="会话ID"),
    file_path: str = FastAPIPath(..., description="文件路径")
):
    """获取EPUB文件中的静态资源（图片、CSS等）
    
    Args:
        session_id: 会话ID
        file_path: 相对于EPUB根目录的文件路径
        
    Returns:
        文件内容的二进制响应
    """
    try:
        # 获取会话信息
        session = await session_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 构建文件的完整路径
        session_dir = session_service.get_session_dir(session_id, "epub")
        epub_dir = session_dir / "epub"
        
        # 安全检查：确保文件路径在EPUB目录内
        full_file_path = epub_dir / file_path
        try:
            # 解析路径，防止路径遍历攻击
            resolved_path = full_file_path.resolve()
            epub_dir_resolved = epub_dir.resolve()
            
            # 检查文件是否在允许的目录内
            if not str(resolved_path).startswith(str(epub_dir_resolved)):
                raise HTTPException(status_code=403, detail="访问被拒绝")
        except (OSError, ValueError):
            raise HTTPException(status_code=400, detail="无效的文件路径")
        
        # 检查文件是否存在
        if not resolved_path.exists() or not resolved_path.is_file():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 读取文件内容
        try:
            with open(resolved_path, 'rb') as f:
                content = f.read()
        except IOError:
            raise HTTPException(status_code=500, detail="文件读取失败")
        
        # 确定MIME类型
        mime_type, _ = mimetypes.guess_type(str(resolved_path))
        if mime_type is None:
            # 根据文件扩展名设置默认MIME类型
            ext = resolved_path.suffix.lower()
            if ext in ['.jpg', '.jpeg']:
                mime_type = 'image/jpeg'
            elif ext == '.png':
                mime_type = 'image/png'
            elif ext == '.gif':
                mime_type = 'image/gif'
            elif ext == '.svg':
                mime_type = 'image/svg+xml'
            elif ext == '.css':
                mime_type = 'text/css'
            elif ext == '.js':
                mime_type = 'application/javascript'
            elif ext in ['.html', '.xhtml']:
                mime_type = 'text/html'
            elif ext == '.xml':
                mime_type = 'application/xml'
            else:
                mime_type = 'application/octet-stream'
        
        performance_logger.info(
            f"Static file served",
            extra={
                "session_id": session_id,
                "file_path": file_path,
                "mime_type": mime_type,
                "size": len(content)
            }
        )
        
        # 返回文件内容
        return Response(
            content=content,
            media_type=mime_type,
            headers={
                "Cache-Control": "public, max-age=3600",  # 缓存1小时
                "Content-Length": str(len(content))
            }
        )
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        performance_logger.error(
            f"Error serving static file: {str(e)}",
            extra={
                "session_id": session_id,
                "file_path": file_path
            }
        )
        raise HTTPException(status_code=500, detail="服务器内部错误")