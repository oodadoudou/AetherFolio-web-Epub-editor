"""文件导出API路由"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional
import urllib.parse

from services.file_service import file_service
from core.logging import performance_logger

router = APIRouter(prefix="/api/v1/export", tags=["export"])


@router.get("/{session_id}")
async def export_file(
    session_id: str,
    format: Optional[str] = Query("original", description="导出格式: original, epub, txt")
):
    """导出文件"""
    try:
        result = await file_service.export_file(
            session_id=session_id,
            format=format
        )
        
        performance_logger.info(
            f"File exported",
            extra={
                "session_id": session_id,
                "format": format
            }
        )
        
        # 对文件名进行URL编码以支持中文字符
        encoded_filename = urllib.parse.quote(result.filename, safe='')
        
        return StreamingResponse(
            result.content_stream,
            media_type=result.media_type,
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
        
    except FileNotFoundError as e:
        performance_logger.warning(f"Export failed - not found: {str(e)}")
        raise HTTPException(status_code=404, detail="会话或文件不存在")
    except ValueError as e:
        performance_logger.warning(f"Export failed - invalid request: {str(e)}")
        raise HTTPException(status_code=400, detail="请求参数无效")
    except Exception as e:
        performance_logger.error(f"Export failed: {str(e)}")
        raise HTTPException(status_code=500, detail="文件导出失败")