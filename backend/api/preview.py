"""预览API路由"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional

from services.preview_service import preview_service
from services.session_service import session_service
from core.logging import performance_logger

router = APIRouter(prefix="/api/v1", tags=["preview"])


@router.get("/preview")
async def get_preview(
    session_id: str = Query(..., description="会话ID"),
    file_path: str = Query(..., description="文件路径")
):
    """获取文件预览HTML
    
    Args:
        session_id: 会话ID
        file_path: 文件路径
        
    Returns:
        预览HTML内容
    """
    try:
        # 验证会话是否存在
        session = await session_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 生成预览HTML
        preview_html = await preview_service.generate_preview(
            session_id=session_id,
            file_path=file_path
        )
        
        performance_logger.info(
            f"Preview generated",
            extra={
                "session_id": session_id,
                "file_path": file_path
            }
        )
        
        return JSONResponse(
            content={
                "success": True,
                "html": preview_html,
                "file_path": file_path
            }
        )
        
    except HTTPException:
        # 让 HTTPException 直接传递，保持原有的状态码
        raise
    except Exception as e:
        performance_logger.error(f"Preview generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="生成预览失败")


@router.get("/preview/status")
async def get_preview_status(
    session_id: str = Query(..., description="会话ID")
):
    """获取预览服务状态
    
    Args:
        session_id: 会话ID
        
    Returns:
        预览服务状态信息
    """
    try:
        # 验证会话是否存在
        session = await session_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 获取预览缓存状态
        cache_info = preview_service.get_cache_info()
        
        return JSONResponse(
            content={
                "success": True,
                "cache_size": cache_info.get("size", 0),
                "cache_hits": cache_info.get("hits", 0),
                "cache_misses": cache_info.get("misses", 0)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        performance_logger.error(f"Get preview status failed: {str(e)}")
        raise HTTPException(status_code=500, detail="获取预览状态失败")


@router.delete("/preview/cache")
async def clear_preview_cache(
    session_id: str = Query(..., description="会话ID")
):
    """清除预览缓存
    
    Args:
        session_id: 会话ID
        
    Returns:
        操作结果
    """
    try:
        # 验证会话是否存在
        session = await session_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 清除预览缓存
        await preview_service.clear_preview_cache()
        
        performance_logger.info(
            f"Preview cache cleared",
            extra={"session_id": session_id}
        )
        
        return JSONResponse(
            content={
                "success": True,
                "message": "预览缓存已清除"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        performance_logger.error(f"Clear preview cache failed: {str(e)}")
        raise HTTPException(status_code=500, detail="清除预览缓存失败")