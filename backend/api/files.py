"""文件操作API"""

import os
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from backend.models.schemas import (
    ApiResponse, ErrorResponse, ResponseStatus, ErrorCode,
    FileContent, SaveFileRequest, ExportRequest, FileNode
)
from backend.services.epub_service import epub_service
from backend.services.text_service import text_service
from backend.services.session_service import session_service
from backend.services.preview_service import preview_service
from backend.core.config import settings
from backend.core.security import security_validator
from backend.core.logging import performance_logger, security_logger

# 创建路由器
router = APIRouter(prefix="/files", tags=["文件操作"])

# 创建限流器
limiter = Limiter(key_func=get_remote_address)

# 添加限流异常处理


@router.get(
    "/content",
    response_model=ApiResponse[FileContent],
    summary="获取文件内容",
    description="获取指定文件的内容"
)
@limiter.limit("30/minute")
async def get_file_content(
    request: Request,
    session_id: str = Query(..., description="会话ID"),
    file_path: str = Query(..., description="文件路径")
) -> ApiResponse[FileContent]:
    """获取文件内容
    
    Args:
        request: FastAPI请求对象
        session_id: 会话ID
        file_path: 文件路径
        
    Returns:
        ApiResponse[FileContent]: 文件内容响应
    """
    try:
        # 验证会话
        session_info = await session_service.get_session(session_id)
        if not session_info:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    status=ResponseStatus.ERROR,
                    error_code=ErrorCode.SESSION_NOT_FOUND,
                    message="会话不存在",
                    timestamp=performance_logger.get_current_time()
                ).model_dump()
            )
        
        # 验证文件路径
        if not security_validator.validate_file_path(file_path):
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    status=ResponseStatus.ERROR,
                    error_code=ErrorCode.FILE_INVALID_PATH,
                    message="文件路径无效",
                    timestamp=performance_logger.get_current_time()
                ).model_dump()
            )
        
        async with performance_logger.async_timer("get_file_content"):
            # 检查文件类型并获取内容
            file_type = session_info.metadata.get("file_type", "epub")
            
            if file_type == "text":
                # TEXT文件处理
                from pathlib import Path
                session_dir = session_info.metadata.get("session_dir")
                if not session_dir:
                    raise HTTPException(status_code=500, detail="会话目录不存在")
                
                full_file_path = Path(session_dir) / file_path
                file_content = await text_service.read_text_file(full_file_path)
            else:
                # EPUB文件处理
                file_content = await epub_service.get_file_content(session_id, file_path)
            
            return ApiResponse(
                status=ResponseStatus.SUCCESS,
                message="文件内容获取成功",
                data=file_content
            )
            
    except HTTPException:
        raise
    except Exception as e:
        security_logger.log_error(
            "Failed to get file content",
            e,
            session_id=session_id,
            file_path=file_path
        )
        
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                status=ResponseStatus.ERROR,
                error_code=ErrorCode.FILE_READ_FAILED,
                message="获取文件内容失败",
                details={"error": str(e)},
                timestamp=performance_logger.get_current_time()
            ).model_dump()
        )


@router.post(
    "/save",
    response_model=ApiResponse[Dict[str, Any]],
    summary="保存文件",
    description="保存修改后的文件内容"
)
@limiter.limit("20/minute")
async def save_file(
    request: Request,
    save_request: SaveFileRequest
) -> ApiResponse[Dict[str, Any]]:
    """保存文件
    
    Args:
        request: FastAPI请求对象
        save_request: 保存请求
        
    Returns:
        ApiResponse[Dict[str, Any]]: 保存结果
    """
    try:
        # 验证会话
        session_info = await session_service.get_session(save_request.session_id)
        if not session_info:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    status=ResponseStatus.ERROR,
                    error_code=ErrorCode.SESSION_NOT_FOUND,
                    message="会话不存在",
                    timestamp=performance_logger.get_current_time()
                ).model_dump()
            )
        
        # 验证文件路径
        if not security_validator.validate_file_path(save_request.file_path):
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    status=ResponseStatus.ERROR,
                    error_code=ErrorCode.FILE_INVALID_PATH,
                    message="文件路径无效",
                    timestamp=performance_logger.get_current_time()
                ).model_dump()
            )
        
        async with performance_logger.async_timer("save_file"):
            # 检查文件类型并保存
            file_type = session_info.metadata.get("file_type", "epub")
            
            if file_type == "text":
                # TEXT文件处理
                from pathlib import Path
                session_dir = session_info.metadata.get("session_dir")
                if not session_dir:
                    raise HTTPException(status_code=500, detail="会话目录不存在")
                
                full_file_path = Path(session_dir) / save_request.file_path
                await text_service.write_text_file(
                    full_file_path, 
                    save_request.content, 
                    save_request.encoding or 'utf-8'
                )
                
                # 获取文件信息
                file_stat = full_file_path.stat()
                result = {
                    "size": file_stat.st_size,
                    "last_modified": file_stat.st_mtime
                }
            else:
                # EPUB文件处理
                result = await epub_service.save_file_content(
                    session_id=save_request.session_id,
                    file_path=save_request.file_path,
                    content=save_request.content,
                    encoding=save_request.encoding
                )
            
            # 清理相关缓存
            await preview_service.clear_preview_cache(save_request.session_id)
            
            # 记录操作
            security_logger.log_info(
                "File saved successfully",
                session_id=save_request.session_id,
                file_path=save_request.file_path,
                content_length=len(save_request.content)
            )
            
            return ApiResponse(
                status=ResponseStatus.SUCCESS,
                message="文件保存成功",
                data={
                    "file_path": save_request.file_path,
                    "size": result.get("size", 0),
                    "last_modified": result.get("last_modified"),
                    "encoding": save_request.encoding
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        security_logger.log_error(
            "Failed to save file",
            e,
            session_id=save_request.session_id,
            file_path=save_request.file_path
        )
        
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                status=ResponseStatus.ERROR,
                error_code=ErrorCode.FILE_SAVE_FAILED,
                message="文件保存失败",
                details={"error": str(e)},
                timestamp=performance_logger.get_current_time()
            ).model_dump()
        )


@router.get(
    "/tree",
    response_model=ApiResponse[List[FileNode]],
    summary="获取文件树",
    description="获取EPUB文件的目录结构"
)
@limiter.limit("20/minute")
async def get_file_tree(
    request: Request,
    session_id: str = Query(..., description="会话ID")
) -> ApiResponse[List[FileNode]]:
    """获取文件树
    
    Args:
        request: FastAPI请求对象
        session_id: 会话ID
        
    Returns:
        ApiResponse[FileNode]: 文件树响应
    """
    try:
        # 验证会话
        session_info = await session_service.get_session(session_id)
        if not session_info:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    status=ResponseStatus.ERROR,
                    error_code=ErrorCode.SESSION_NOT_FOUND,
                    message="会话不存在",
                    timestamp=performance_logger.get_current_time()
                ).model_dump()
            )
        
        async with performance_logger.async_timer("get_file_tree"):
            # 获取文件树
            file_tree = await epub_service.get_file_tree(session_id)
            
            return ApiResponse(
                status=ResponseStatus.SUCCESS,
                message="文件树获取成功",
                data=file_tree
            )
            
    except HTTPException:
        raise
    except Exception as e:
        security_logger.log_error(
            "Failed to get file tree",
            e,
            session_id=session_id
        )
        
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                status=ResponseStatus.ERROR,
                error_code=ErrorCode.GENERAL_ERROR,
                message="获取文件树失败",
                details={"error": str(e)},
                timestamp=performance_logger.get_current_time()
            ).model_dump()
        )


@router.post(
    "/export",
    summary="导出EPUB",
    description="导出编辑后的EPUB文件"
)
@limiter.limit("5/minute")
async def export_epub(
    request: Request,
    export_request: ExportRequest
):
    """导出EPUB文件
    
    Args:
        request: FastAPI请求对象
        export_request: 导出请求
        
    Returns:
        StreamingResponse: EPUB文件流
    """
    try:
        # 验证会话
        session_info = await session_service.get_session(export_request.session_id)
        if not session_info:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    status=ResponseStatus.ERROR,
                    error_code=ErrorCode.SESSION_NOT_FOUND,
                    message="会话不存在",
                    timestamp=performance_logger.get_current_time()
                ).model_dump()
            )
        
        async with performance_logger.async_timer("export_epub"):
            # 导出EPUB文件
            epub_stream = await epub_service.export_epub(
                session_id=export_request.session_id,
                output_filename=export_request.output_filename
            )
            
            # 生成文件名
            filename = export_request.output_filename or f"edited_{session_info.metadata.get('original_filename', 'book.epub')}"
            if not filename.endswith('.epub'):
                filename += '.epub'
            
            # 记录导出操作
            security_logger.log_info(
                "EPUB exported successfully",
                session_id=export_request.session_id,
                filename=filename
            )
            
            return StreamingResponse(
                epub_stream,
                media_type="application/epub+zip",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}",
                    "Cache-Control": "no-cache"
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        security_logger.log_error(
            "Failed to export EPUB",
            e,
            session_id=export_request.session_id
        )
        
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                status=ResponseStatus.ERROR,
                error_code=ErrorCode.EPUB_EXPORT_FAILED,
                message="EPUB导出失败",
                details={"error": str(e)},
                timestamp=performance_logger.get_current_time()
            ).model_dump()
        )


@router.post(
    "/export/text",
    summary="导出TEXT文件",
    description="导出编辑后的TEXT文件"
)
@limiter.limit("5/minute")
async def export_text(
    request: Request,
    export_request: ExportRequest
):
    """导出TEXT文件
    
    Args:
        request: FastAPI请求对象
        export_request: 导出请求
        
    Returns:
        StreamingResponse: TEXT文件流
    """
    try:
        # 验证会话
        session_info = await session_service.get_session(export_request.session_id)
        if not session_info:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    status=ResponseStatus.ERROR,
                    error_code=ErrorCode.SESSION_NOT_FOUND,
                    message="会话不存在",
                    timestamp=performance_logger.get_current_time()
                ).model_dump()
            )
        
        # 验证是TEXT文件类型
        file_type = session_info.metadata.get("file_type", "epub")
        if file_type != "text":
            raise HTTPException(
                status_code=400,
                detail="只能导出TEXT文件类型的会话"
            )
        
        async with performance_logger.async_timer("export_text"):
            # 获取会话目录和文件信息
            session_dir = session_info.metadata.get("session_dir")
            if not session_dir:
                raise HTTPException(status_code=500, detail="会话目录不存在")
            
            # 获取原始文件名
            original_filename = session_info.metadata.get("original_filename", "text_file.txt")
            
            # 生成导出文件名
            filename = export_request.output_filename or f"edited_{original_filename}"
            if not any(filename.lower().endswith(ext) for ext in ['.txt', '.text', '.md', '.markdown']):
                filename += '.txt'
            
            # 读取文件内容
            from pathlib import Path
            file_path = Path(session_dir) / original_filename
            
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="文件不存在")
            
            file_content = await text_service.read_text_file(file_path)
            
            # 创建文件流
            def generate_content():
                yield file_content.content.encode(file_content.encoding)
            
            # 记录导出操作
            security_logger.log_info(
                "TEXT file exported successfully",
                session_id=export_request.session_id,
                filename=filename
            )
            
            return StreamingResponse(
                generate_content(),
                media_type="text/plain",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}",
                    "Cache-Control": "no-cache",
                    "Content-Type": f"text/plain; charset={file_content.encoding}"
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        security_logger.log_error(
            "Failed to export TEXT file",
            e,
            session_id=export_request.session_id
        )
        
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                status=ResponseStatus.ERROR,
                error_code=ErrorCode.GENERAL_ERROR,
                message="TEXT文件导出失败",
                details={"error": str(e)},
                timestamp=performance_logger.get_current_time()
            ).model_dump()
        )


@router.get(
    "/preview/{session_id}/{file_path:path}",
    summary="预览文件",
    description="获取文件的HTML预览"
)
@limiter.limit("30/minute")
async def preview_file(
    request: Request,
    session_id: str,
    file_path: str,
    base_url: Optional[str] = Query(None, description="基础URL")
):
    """预览文件
    
    Args:
        request: FastAPI请求对象
        session_id: 会话ID
        file_path: 文件路径
        base_url: 基础URL
        
    Returns:
        StreamingResponse: HTML预览
    """
    try:
        # 验证会话
        session_info = await session_service.get_session(session_id)
        if not session_info:
            raise HTTPException(
                status_code=404,
                detail="会话不存在"
            )
        
        # 验证文件路径
        if not security_validator.validate_file_path(file_path):
            raise HTTPException(
                status_code=400,
                detail="文件路径无效"
            )
        
        async with performance_logger.async_timer("preview_file"):
            # 生成预览
            preview_html = await preview_service.generate_preview(
                session_id=session_id,
                file_path=file_path,
                base_url=base_url
            )
            
            return StreamingResponse(
                iter([preview_html.encode('utf-8')]),
                media_type="text/html",
                headers={
                    "Cache-Control": "public, max-age=300",  # 缓存5分钟
                    "Content-Type": "text/html; charset=utf-8"
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        security_logger.log_error(
            "Failed to preview file",
            e,
            session_id=session_id,
            file_path=file_path
        )
        
        # 返回错误页面
        error_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>预览错误</title>
    <meta charset="utf-8">
</head>
<body>
    <h1>预览错误</h1>
    <p>无法预览文件: {file_path}</p>
    <p>错误信息: {str(e)}</p>
</body>
</html>
        """
        
        return StreamingResponse(
            iter([error_html.encode('utf-8')]),
            media_type="text/html",
            status_code=500
        )


@router.put(
    "/content",
    response_model=ApiResponse[Dict[str, Any]],
    summary="更新文件内容",
    description="更新指定文件的内容"
)
@limiter.limit("20/minute")
async def update_file_content(
    request: Request,
    save_request: SaveFileRequest
) -> ApiResponse[Dict[str, Any]]:
    """更新文件内容
    
    Args:
        request: FastAPI请求对象
        save_request: 保存请求
        
    Returns:
        ApiResponse[Dict[str, Any]]: 更新结果
    """
    # 复用save_file的逻辑
    return await save_file(request, save_request)


@router.delete(
    "/content",
    response_model=ApiResponse[Dict[str, Any]],
    summary="删除文件",
    description="删除指定文件"
)
@limiter.limit("10/minute")
async def delete_file(
    request: Request,
    session_id: str = Query(..., description="会话ID"),
    file_path: str = Query(..., description="文件路径")
) -> ApiResponse[Dict[str, Any]]:
    """删除文件
    
    Args:
        request: FastAPI请求对象
        session_id: 会话ID
        file_path: 文件路径
        
    Returns:
        ApiResponse[Dict[str, Any]]: 删除结果
    """
    try:
        # 验证会话
        session_info = await session_service.get_session(session_id)
        if not session_info:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    status=ResponseStatus.ERROR,
                    error_code=ErrorCode.SESSION_NOT_FOUND,
                    message="会话不存在",
                    timestamp=performance_logger.get_current_time()
                ).model_dump()
            )
        
        # 验证文件路径
        if not security_validator.validate_file_path(file_path):
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    status=ResponseStatus.ERROR,
                    error_code=ErrorCode.FILE_INVALID_PATH,
                    message="文件路径无效",
                    timestamp=performance_logger.get_current_time()
                ).model_dump()
            )
        
        async with performance_logger.async_timer("delete_file"):
            # 检查文件类型并删除
            file_type = session_info.metadata.get("file_type", "epub")
            
            if file_type == "text":
                # TEXT文件处理
                from pathlib import Path
                session_dir = session_info.metadata.get("session_dir")
                if not session_dir:
                    raise HTTPException(status_code=500, detail="会话目录不存在")
                
                full_file_path = Path(session_dir) / file_path
                if not full_file_path.exists():
                    raise HTTPException(
                        status_code=404,
                        detail=ErrorResponse(
                            status=ResponseStatus.ERROR,
                            error_code=ErrorCode.FILE_NOT_FOUND,
                            message="文件不存在",
                            timestamp=performance_logger.get_current_time()
                        ).model_dump()
                    )
                
                full_file_path.unlink()
                result = {"deleted": True, "file_path": file_path}
            else:
                # EPUB文件处理 - 暂时返回成功但不实际删除
                # 因为EPUB文件结构复杂，删除可能破坏文件完整性
                result = {"deleted": False, "message": "EPUB文件删除暂不支持"}
            
            return ApiResponse(
                status=ResponseStatus.SUCCESS,
                message="文件删除操作完成",
                data=result
            )
            
    except HTTPException:
        raise
    except Exception as e:
        security_logger.log_error(
            "Failed to delete file",
            e,
            session_id=session_id,
            file_path=file_path
        )
        
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                status=ResponseStatus.ERROR,
                error_code=ErrorCode.FILE_DELETE_FAILED,
                message="文件删除失败",
                details={"error": str(e)},
                timestamp=performance_logger.get_current_time()
            ).model_dump()
        )


@router.delete(
    "/cache/{session_id}",
    response_model=ApiResponse[Dict[str, Any]],
    summary="清理缓存",
    description="清理指定会话的文件缓存"
)
async def clear_file_cache(
    session_id: str
) -> ApiResponse[Dict[str, Any]]:
    """清理文件缓存
    
    Args:
        session_id: 会话ID
        
    Returns:
        ApiResponse[Dict[str, Any]]: 清理结果
    """
    try:
        # 验证会话
        session_info = await session_service.get_session(session_id)
        if not session_info:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    status=ResponseStatus.ERROR,
                    error_code=ErrorCode.SESSION_NOT_FOUND,
                    message="会话不存在",
                    timestamp=performance_logger.get_current_time()
                ).model_dump()
            )
        
        # 清理各种缓存
        await preview_service.clear_preview_cache(session_id)
        await epub_service.clear_file_cache(session_id)
        
        security_logger.log_info(
            "File cache cleared",
            session_id=session_id
        )
        
        return ApiResponse(
            status=ResponseStatus.SUCCESS,
            message="缓存清理成功",
            data={"session_id": session_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        security_logger.log_error(
            "Failed to clear file cache",
            e,
            session_id=session_id
        )
        
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                status=ResponseStatus.ERROR,
                error_code=ErrorCode.GENERAL_ERROR,
                message="清理缓存失败",
                details={"error": str(e)},
                timestamp=performance_logger.get_current_time()
            ).model_dump()
        )


# 导出路由器
__all__ = ["router"]