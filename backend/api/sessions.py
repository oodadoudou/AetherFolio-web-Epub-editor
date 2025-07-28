"""会话管理API"""

from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from backend.models.schemas import (
    ApiResponse, ErrorResponse, ResponseStatus, ErrorCode,
    SessionInfo, HealthCheck, BookMetadata
)
from backend.models.session import Session
from backend.services.session_service import session_service
from backend.services.epub_service import epub_service
from backend.services.preview_service import preview_service
from backend.core.config import settings
from backend.core.logging import performance_logger, security_logger

# 创建路由器
router = APIRouter(prefix="/sessions", tags=["会话管理"])

# 创建限流器
limiter = Limiter(key_func=get_remote_address)

# 添加限流异常处理

async def convert_session_to_session_info(session: Session) -> SessionInfo:
    """将Session转换为SessionInfo
    
    Args:
        session: Session实例
        
    Returns:
        SessionInfo: 转换后的SessionInfo实例
    """
    try:
        # 获取文件树
        file_tree = await epub_service.get_file_tree(session.session_id)
        
        # 构建书籍元数据
        metadata = BookMetadata(
            title=session.metadata.get('title', session.original_filename or 'Unknown'),
            author=session.metadata.get('author', 'Unknown'),
            language=session.metadata.get('language', 'zh'),
            publisher=session.metadata.get('publisher', ''),
            publication_date=session.metadata.get('publication_date', ''),
            description=session.metadata.get('description', ''),
            isbn=session.metadata.get('isbn', ''),
            cover_image=session.metadata.get('cover_image', ''),
            tags=session.metadata.get('tags', []),
            series=session.metadata.get('series', ''),
            series_index=session.metadata.get('series_index'),
            custom_metadata=session.metadata.get('custom_metadata', {})
        )
        
        return SessionInfo(
            session_id=session.session_id,
            file_tree=file_tree,
            metadata=metadata,
            created_time=session.upload_time,
            last_accessed=session.last_accessed,
            original_filename=session.original_filename
        )
    except Exception as e:
        # 如果获取文件树失败，创建空的SessionInfo
        metadata = BookMetadata(
            title=session.original_filename or 'Unknown',
            author='Unknown',
            language='zh'
        )
        
        return SessionInfo(
            session_id=session.session_id,
            file_tree=[],
            metadata=metadata,
            created_time=session.upload_time,
            last_accessed=session.last_accessed,
            original_filename=session.original_filename
        )


@router.get(
    "/{session_id}",
    response_model=ApiResponse[SessionInfo],
    summary="获取会话信息",
    description="获取指定会话的详细信息"
)
@limiter.limit("30/minute")
async def get_session(
    request: Request,
    session_id: str
) -> ApiResponse[SessionInfo]:
    """获取会话信息
    
    Args:
        request: FastAPI请求对象
        session_id: 会话ID
        
    Returns:
        ApiResponse[SessionInfo]: 会话信息响应
    """
    try:
        async with performance_logger.async_timer("get_session"):
            # 获取会话信息
            session = await session_service.get_session(session_id)
            
            if not session:
                raise HTTPException(
                    status_code=404,
                    detail=ErrorResponse(
                        status=ResponseStatus.ERROR,
                        error_code=ErrorCode.SESSION_NOT_FOUND,
                        message="会话不存在",
                        timestamp=performance_logger.get_current_time()
                    ).model_dump()
                )
            
            # 转换为SessionInfo
            session_info = await convert_session_to_session_info(session)
            
            return ApiResponse(
                status=ResponseStatus.SUCCESS,
                message="会话信息获取成功",
                data=session_info
            )
            
    except HTTPException:
        raise
    except Exception as e:
        security_logger.log_error(
            "Failed to get session",
            e,
            session_id=session_id
        )
        
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                status=ResponseStatus.ERROR,
                error_code=ErrorCode.GENERAL_ERROR,
                message="获取会话信息失败",
                details={"error": str(e)},
                timestamp=performance_logger.get_current_time()
            ).model_dump()
        )


@router.put(
    "/{session_id}/extend",
    response_model=ApiResponse[SessionInfo],
    summary="延长会话",
    description="延长会话的有效期"
)
@limiter.limit("10/minute")
async def extend_session(
    request: Request,
    session_id: str
) -> ApiResponse[SessionInfo]:
    """延长会话
    
    Args:
        request: FastAPI请求对象
        session_id: 会话ID
        
    Returns:
        ApiResponse[SessionInfo]: 更新后的会话信息
    """
    try:
        async with performance_logger.async_timer("extend_session"):
            # 延长会话
            success = await session_service.extend_session(session_id)
            
            if not success:
                raise HTTPException(
                    status_code=404,
                    detail=ErrorResponse(
                        status=ResponseStatus.ERROR,
                        error_code=ErrorCode.SESSION_NOT_FOUND,
                        message="会话不存在",
                        timestamp=performance_logger.get_current_time()
                    ).model_dump()
                )
            
            # 获取更新后的会话信息
            session = await session_service.get_session(session_id)
            session_info = await convert_session_to_session_info(session)
            
            security_logger.log_info(
                "Session extended",
                session_id=session_id,
                new_expires_at=session.expires_at.isoformat()
            )
            
            return ApiResponse(
                status=ResponseStatus.SUCCESS,
                message="会话延长成功",
                data=session_info
            )
            
    except HTTPException:
        raise
    except Exception as e:
        security_logger.log_error(
            "Failed to extend session",
            e,
            session_id=session_id
        )
        
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                status=ResponseStatus.ERROR,
                error_code=ErrorCode.GENERAL_ERROR,
                message="延长会话失败",
                details={"error": str(e)},
                timestamp=performance_logger.get_current_time()
            ).model_dump()
        )


@router.delete(
    "/{session_id}",
    response_model=ApiResponse[Dict[str, Any]],
    summary="删除会话",
    description="删除会话及其相关数据"
)
@limiter.limit("10/minute")
async def delete_session(
    request: Request,
    session_id: str
) -> ApiResponse[Dict[str, Any]]:
    """删除会话
    
    Args:
        request: FastAPI请求对象
        session_id: 会话ID
        
    Returns:
        ApiResponse[Dict[str, Any]]: 删除结果
    """
    try:
        async with performance_logger.async_timer("delete_session"):
            # 获取会话信息（用于记录）
            session = await session_service.get_session(session_id)
            
            if not session:
                raise HTTPException(
                    status_code=404,
                    detail=ErrorResponse(
                        status=ResponseStatus.ERROR,
                        error_code=ErrorCode.SESSION_NOT_FOUND,
                        message="会话不存在",
                        timestamp=performance_logger.get_current_time()
                    ).model_dump()
                )
            
            # 清理相关缓存和数据
            await preview_service.clear_preview_cache(session_id)
            await epub_service.clear_file_cache(session_id)
            
            # 删除会话
            success = await session_service.delete_session(session_id)
            
            if success:
                security_logger.log_info(
                    "Session deleted",
                    session_id=session_id,
                    original_filename=session.original_filename
                )
                
                return ApiResponse(
                    status=ResponseStatus.SUCCESS,
                    message="会话删除成功",
                    data={"session_id": session_id}
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=ErrorResponse(
                        status=ResponseStatus.ERROR,
                        error_code=ErrorCode.GENERAL_ERROR,
                        message="会话删除失败",
                        timestamp=performance_logger.get_current_time()
                    ).model_dump()
                )
            
    except HTTPException:
        raise
    except Exception as e:
        security_logger.log_error(
            "Failed to delete session",
            e,
            session_id=session_id
        )
        
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                status=ResponseStatus.ERROR,
                error_code=ErrorCode.GENERAL_ERROR,
                message="删除会话失败",
                details={"error": str(e)},
                timestamp=performance_logger.get_current_time()
            ).model_dump()
        )


@router.get(
    "/",
    response_model=ApiResponse[List[SessionInfo]],
    summary="获取所有会话",
    description="获取所有活跃会话的列表（管理员功能）"
)
@limiter.limit("5/minute")
async def list_sessions(
    request: Request
) -> ApiResponse[List[SessionInfo]]:
    """获取所有会话
    
    Args:
        request: FastAPI请求对象
        
    Returns:
        ApiResponse[List[SessionInfo]]: 会话列表响应
    """
    try:
        async with performance_logger.async_timer("list_sessions"):
            # 获取所有会话
            sessions = await session_service.list_sessions()
            
            # 转换为SessionInfo列表
            session_infos = []
            for session in sessions:
                try:
                    session_info = await convert_session_to_session_info(session)
                    session_infos.append(session_info)
                except Exception as e:
                    # 如果转换失败，跳过这个会话
                    security_logger.log_error(
                        "Failed to convert session to session_info",
                        e,
                        session_id=session.session_id
                    )
                    continue
            
            return ApiResponse(
                status=ResponseStatus.SUCCESS,
                message=f"获取到{len(session_infos)}个活跃会话",
                data=session_infos
            )
            
    except Exception as e:
        security_logger.log_error(
            "Failed to list sessions",
            e
        )
        
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                status=ResponseStatus.ERROR,
                error_code=ErrorCode.GENERAL_ERROR,
                message="获取会话列表失败",
                details={"error": str(e)},
                timestamp=performance_logger.get_current_time()
            ).model_dump()
        )


@router.post(
    "/cleanup",
    response_model=ApiResponse[Dict[str, Any]],
    summary="清理过期会话",
    description="清理所有过期的会话（管理员功能）"
)
@limiter.limit("2/minute")
async def cleanup_expired_sessions(
    request: Request
) -> ApiResponse[Dict[str, Any]]:
    """清理过期会话
    
    Args:
        request: FastAPI请求对象
        
    Returns:
        ApiResponse[Dict[str, Any]]: 清理结果
    """
    try:
        async with performance_logger.async_timer("cleanup_expired_sessions"):
            # 清理过期会话
            cleaned_count = await session_service.cleanup_expired_sessions()
            
            security_logger.log_info(
                "Expired sessions cleaned up",
                cleaned_count=cleaned_count
            )
            
            return ApiResponse(
                status=ResponseStatus.SUCCESS,
                message=f"清理了{cleaned_count}个过期会话",
                data={
                    "cleaned_count": cleaned_count,
                    "cleanup_time": performance_logger.get_current_time()
                }
            )
            
    except Exception as e:
        security_logger.log_error(
            "Failed to cleanup expired sessions",
            e
        )
        
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                status=ResponseStatus.ERROR,
                error_code=ErrorCode.GENERAL_ERROR,
                message="清理过期会话失败",
                details={"error": str(e)},
                timestamp=performance_logger.get_current_time()
            ).model_dump()
        )


@router.get(
    "/{session_id}/stats",
    response_model=ApiResponse[Dict[str, Any]],
    summary="获取会话统计",
    description="获取会话的统计信息"
)
@limiter.limit("20/minute")
async def get_session_stats(
    request: Request,
    session_id: str
) -> ApiResponse[Dict[str, Any]]:
    """获取会话统计
    
    Args:
        request: FastAPI请求对象
        session_id: 会话ID
        
    Returns:
        ApiResponse[Dict[str, Any]]: 会话统计信息
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
        
        async with performance_logger.async_timer("get_session_stats"):
            # 获取文件树统计
            file_tree = await epub_service.get_file_tree(session_id)
            
            def count_files(node):
                """递归计算文件数量"""
                count = 0
                if node.type.value == "file":
                    count = 1
                
                if node.children:
                    for child in node.children:
                        count += count_files(child)
                
                return count
            
            total_files = count_files(file_tree)
            
            # 计算会话持续时间
            from datetime import datetime
            duration_seconds = (datetime.now() - session_info.created_at).total_seconds()
            
            stats = {
                "session_id": session_id,
                "created_at": session_info.created_at.isoformat(),
                "expires_at": session_info.expires_at.isoformat(),
                "duration_seconds": int(duration_seconds),
                "total_files": total_files,
                "original_filename": session_info.metadata.get('original_filename'),
                "file_size": session_info.metadata.get('file_size'),
                "upload_time": session_info.metadata.get('upload_time'),
                "book_metadata": session_info.metadata.get('book_metadata', {})
            }
            
            return ApiResponse(
                status=ResponseStatus.SUCCESS,
                message="会话统计获取成功",
                data=stats
            )
            
    except HTTPException:
        raise
    except Exception as e:
        security_logger.log_error(
            "Failed to get session stats",
            e,
            session_id=session_id
        )
        
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                status=ResponseStatus.ERROR,
                error_code=ErrorCode.GENERAL_ERROR,
                message="获取会话统计失败",
                details={"error": str(e)},
                timestamp=performance_logger.get_current_time()
            ).model_dump()
        )


# 健康检查路由（不在sessions前缀下）
@router.get(
    "/health",
    response_model=ApiResponse[HealthCheck],
    summary="健康检查",
    description="检查服务健康状态",
    include_in_schema=False  # 不在API文档中显示
)
async def health_check() -> ApiResponse[HealthCheck]:
    """健康检查
    
    Returns:
        ApiResponse[HealthCheck]: 健康状态
    """
    try:
        # 检查各个服务的状态
        session_count = len(await session_service.list_sessions())
        
        health_data = HealthCheck(
            status="healthy",
            timestamp=performance_logger.get_current_time(),
            version="1.0.0",
            services={
                "session_service": "healthy",
                "epub_service": "healthy",
                "preview_service": "healthy"
            },
            metrics={
                "active_sessions": session_count,
                "uptime_seconds": 0  # 可以添加实际的运行时间计算
            }
        )
        
        return ApiResponse(
            status=ResponseStatus.SUCCESS,
            message="服务运行正常",
            data=health_data
        )
        
    except Exception as e:
        security_logger.log_error("Health check failed", e)
        
        health_data = HealthCheck(
            status="unhealthy",
            timestamp=performance_logger.get_current_time(),
            version="1.0.0",
            services={
                "session_service": "error",
                "epub_service": "unknown",
                "preview_service": "unknown"
            },
            metrics={}
        )
        
        return ApiResponse(
            status=ResponseStatus.ERROR,
            message="服务异常",
            data=health_data
        )


# 导出路由器
__all__ = ["router"]