"""文件内容获取 API 端点

BE-04: 获取文件内容功能
- 根据会话ID和文件路径获取指定文件的内容
- 验证会话ID的有效性和文件路径的安全性
- 支持多种文件类型：HTML、XHTML、CSS、TXT、XML等
- 自动检测文件编码并正确解码
- 返回文件内容、文件类型、编码信息
- 实现文件访问权限控制，防止路径遍历攻击
- 支持大文件的分块读取
"""

import os
import mimetypes
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.models.schemas import (
    ApiResponse, 
    ResponseStatus, 
    ErrorCode, 
    ErrorResponse,
    FileContent
)
from backend.core.logging import performance_logger, security_logger
from backend.core.security import security_validator
from backend.services.session_service import session_service
from backend.services.file_service import file_service

# 创建路由器
router = APIRouter(tags=["文件内容"])

# 创建限流器
limiter = Limiter(key_func=get_remote_address)


@router.get(
    "/file-content",
    response_model=ApiResponse[FileContent],
    summary="获取文件内容",
    description="根据会话ID和文件路径获取指定文件的内容，支持多种文件类型和编码自动检测"
)
@limiter.limit("60/minute")
async def get_file_content(
    request: Request,
    session_id: str = Query(..., description="会话ID"),
    file_path: str = Query(..., description="文件路径（相对于会话目录）"),
    chunk_size: Optional[int] = Query(None, description="分块大小（字节），用于大文件读取"),
    chunk_offset: Optional[int] = Query(0, description="分块偏移量（字节）")
) -> ApiResponse[FileContent]:
    """获取文件内容
    
    Args:
        request: FastAPI请求对象
        session_id: 会话ID
        file_path: 文件路径（相对于会话目录）
        chunk_size: 分块大小（可选，用于大文件读取）
        chunk_offset: 分块偏移量（默认为0）
        
    Returns:
        ApiResponse[FileContent]: 文件内容响应
        
    Raises:
        HTTPException: 当会话不存在、文件不存在或访问被拒绝时
    """
    try:
        # 验证会话ID
        session_info = await session_service.get_session(session_id)
        if not session_info:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": "会话不存在"
                }
            )
        
        # 验证文件路径安全性
        if not security_validator.validate_file_path(file_path):
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "路径不安全：文件路径无效或包含危险字符"
                }
            )
        
        # 获取会话目录
        session_dir = None
        print(f"DEBUG: session_info.metadata: {session_info.metadata}")
        
        # 尝试从session_data中获取metadata
        metadata = await session_service.get_session_data(session_id, "metadata")
        print(f"DEBUG: metadata from session_data: {metadata}")
        
        if metadata:
            file_type = metadata.get("file_type", "").upper()
            print(f"DEBUG: file_type: {file_type}")
            if file_type == "TEXT":
                # 对于TEXT文件，构建会话目录路径
                from backend.core.config import settings
                session_dir = os.path.join(settings.session_dir, session_id)
                print(f"DEBUG: TEXT session_dir: {session_dir}")
            else:
                # EPUB 文件的临时目录
                from backend.services.epub_service import epub_service
                temp_dir = await epub_service._get_temp_dir(session_id)
                session_dir = temp_dir
                print(f"DEBUG: EPUB session_dir: {session_dir}")
        elif hasattr(session_info, 'metadata') and session_info.metadata:
            # 回退到旧的metadata获取方式
            file_type = session_info.metadata.get("file_type", "").upper()
            print(f"DEBUG: fallback file_type: {file_type}")
            if file_type == "TEXT":
                session_dir = session_info.metadata.get("session_dir")
                print(f"DEBUG: session_dir from session_info.metadata: {session_dir}")
                # 如果metadata中没有session_dir，尝试构建默认路径
                if not session_dir:
                    from backend.core.config import settings
                    session_dir = os.path.join(settings.session_dir, session_id)
                    print(f"DEBUG: constructed session_dir: {session_dir}")
            else:
                # EPUB 文件的临时目录
                from backend.services.epub_service import epub_service
                temp_dir = await epub_service._get_temp_dir(session_id)
                session_dir = temp_dir
                print(f"DEBUG: EPUB session_dir: {session_dir}")
        else:
            # 如果没有metadata，尝试从session_info获取base_path
            session_dir = getattr(session_info, 'base_path', None)
            print(f"DEBUG: fallback session_dir: {session_dir}")
        
        if not session_dir or not os.path.exists(session_dir):
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": "会话目录不存在"
                }
            )
        
        # 构建完整文件路径并验证安全性
        full_file_path = security_validator.sanitize_path(file_path, session_dir)
        
        # 验证文件是否在会话目录内（防止路径遍历攻击）
        try:
            session_path = Path(session_dir).resolve()
            file_path_obj = Path(full_file_path).resolve()
            
            # 检查文件路径是否在会话目录内
            if not str(file_path_obj).startswith(str(session_path)):
                raise HTTPException(
                    status_code=403,
                    detail={
                        "success": False,
                        "error": "路径不安全：文件访问被拒绝"
                    }
                )
        except Exception as e:
            security_logger.log_error(
                "Path validation failed",
                e,
                session_id=session_id,
                file_path=file_path
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "文件路径验证失败"
                }
            )
        
        # 检查文件是否存在
        if not os.path.exists(full_file_path) or not os.path.isfile(full_file_path):
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": "文件不存在"
                }
            )
        
        async with performance_logger.async_timer("get_file_content"):
            # 使用增强的文件服务获取文件内容
            file_content = await file_service.get_file_content_enhanced(
                file_path=full_file_path,
                chunk_size=chunk_size,
                chunk_offset=chunk_offset or 0
            )
            
            # 记录成功操作
            security_logger.log_info(
                "File content retrieved successfully",
                session_id=session_id,
                file_path=file_path,
                file_size=file_content.size,
                mime_type=file_content.mime_type,
                encoding=file_content.encoding
            )
            
            return ApiResponse(
                status=ResponseStatus.SUCCESS,
                message="文件内容获取成功",
                data=file_content
            )
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"DEBUG: Exception in get_file_content: {str(e)}")
        print(f"DEBUG: Traceback: {error_traceback}")
        
        security_logger.log_error(
            "Failed to get file content",
            e,
            session_id=session_id,
            file_path=file_path
        )
        
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "获取文件内容失败"
            }
        )