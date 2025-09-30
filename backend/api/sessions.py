"""会话基本操作API路由

只提供基本的会话创建和删除功能，不包含历史会话管理接口
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any

from services.session_service import session_service
from core.logging import performance_logger

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.post("/")
async def create_session(metadata: Optional[Dict[str, Any]] = None):
    """创建新会话"""
    try:
        session_id = await session_service.create_session(metadata)
        
        performance_logger.info(
            f"Session created: {session_id}"
        )
        
        return JSONResponse(
            status_code=201,
            content={
                "session_id": session_id,
                "created_at": "2025-08-01T20:28:41.000Z",
                "status": "active"
            }
        )
        
    except Exception as e:
        performance_logger.error(f"Create session failed: {str(e)}")
        raise HTTPException(status_code=500, detail="创建会话失败")


@router.get("/{session_id}/status")
async def get_session_status(session_id: str):
    """检查会话状态"""
    try:
        session = await session_service.get_session(session_id)
        
        if not session:
            return JSONResponse(
                status_code=404,
                content={
                    "exists": False,
                    "status": "not_found",
                    "message": "会话不存在或已过期"
                }
            )
        
        return JSONResponse(
            content={
                "exists": True,
                "status": session.get("status", "unknown"),
                "last_accessed": session.get("last_accessed").isoformat() if session.get("last_accessed") else None,
                "message": "会话有效"
            }
        )
        
    except Exception as e:
        performance_logger.error(f"Check session status failed: {str(e)}")
        raise HTTPException(status_code=500, detail="检查会话状态失败")


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    try:
        await session_service.delete_session(session_id)
        
        performance_logger.info(
            f"Session deleted",
            extra={"session_id": session_id}
        )
        
        return JSONResponse(
            content={"success": True, "message": "会话删除成功"}
        )
        
    except Exception as e:
        performance_logger.error(f"Delete session failed: {str(e)}")
        raise HTTPException(status_code=500, detail="删除会话失败")