"""搜索替换API路由"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from services.search_replace_service import search_replace_service
from core.logging import performance_logger
from db.models.schemas import SearchReplaceRequest, SearchReplaceResponse

router = APIRouter(prefix="/api/v1/search-replace", tags=["search-replace"])


@router.post("/search", response_model=SearchReplaceResponse)
async def search_text(
    request: SearchReplaceRequest
):
    """搜索文本"""
    try:
        result = await search_replace_service.search_text(
            session_id=request.session_id,
            search_term=request.search_term,
            case_sensitive=request.case_sensitive,
            use_regex=request.use_regex,
            file_path=request.file_path
        )
        
        performance_logger.info(
            f"Text search completed",
            extra={
                "session_id": request.session_id,
                "matches_found": len(result.matches)
            }
        )
        
        return result
        
    except Exception as e:
        performance_logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail="搜索失败")


@router.post("/replace", response_model=SearchReplaceResponse)
async def replace_text(
    request: SearchReplaceRequest
):
    """替换文本"""
    try:
        result = await search_replace_service.replace_text(
            session_id=request.session_id,
            search_term=request.search_term,
            replace_term=request.replace_term,
            case_sensitive=request.case_sensitive,
            use_regex=request.use_regex,
            file_path=request.file_path,
            replace_all=request.replace_all
        )
        
        performance_logger.info(
            f"Text replace completed",
            extra={
                "session_id": request.session_id,
                "replacements_made": result.replacements_made
            }
        )
        
        return result
        
    except Exception as e:
        performance_logger.error(f"Replace failed: {str(e)}")
        raise HTTPException(status_code=500, detail="替换失败")