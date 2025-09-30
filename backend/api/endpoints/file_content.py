"""文件内容API路由"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from services.file_service import file_service
from core.logging import performance_logger
from db.models.schemas import FileContentResponse

router = APIRouter(prefix="/api/v1", tags=["file-content"])


@router.get("/file-content", response_model=FileContentResponse)
async def get_file_content(
    session_id: str = Query(..., description="会话ID"),
    file_path: str = Query(..., description="文件路径")
):
    """获取文件内容"""
    try:
        result = await file_service.get_file_content(
            session_id=session_id,
            file_path=file_path
        )
        
        performance_logger.info(
            f"File content retrieved",
            extra={
                "session_id": session_id,
                "file_path": file_path,
                "content_length": len(result.content)
            }
        )
        
        return result
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="文件不存在")
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限访问该文件")
    except Exception as e:
        performance_logger.error(
            f"Get file content failed: {str(e)}",
            extra={
                "session_id": session_id,
                "file_path": file_path
            }
        )
        raise HTTPException(status_code=500, detail="获取文件内容失败")