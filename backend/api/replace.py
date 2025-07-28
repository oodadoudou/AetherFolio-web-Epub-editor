"""批量替换API"""

import os
import uuid
from typing import Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request, BackgroundTasks
from fastapi.responses import StreamingResponse, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sse_starlette.sse import EventSourceResponse
from datetime import datetime
import io

from backend.models.schemas import (
    ApiResponse, ErrorResponse, ResponseStatus, ErrorCode,
    BatchReplaceRequest, ReplaceProgress, ReplaceResult
)
from backend.services.replace_service import replace_service
from backend.services.session_service import session_service
from backend.services.report_service import report_service
from backend.core.config import settings
from backend.core.security import security_validator
from backend.core.logging import performance_logger, security_logger

# 创建路由器
router = APIRouter(prefix="/batch-replace", tags=["批量替换"])

# 创建限流器
limiter = Limiter(key_func=get_remote_address)

# 条件性应用速率限制
def _apply_rate_limit(func):
    """条件性应用速率限制"""
    if os.getenv("DISABLE_RATE_LIMIT") == "true":
        return func
    return limiter.limit("5/minute")(func)

# 添加限流异常处理


@router.get(
    "/template",
    summary="下载批量替换规则模板",
    description="生成并下载批量替换规则模板文件"
)
async def download_template() -> Response:
    """下载批量替换规则模板
    
    Returns:
        Response: 模板文件响应
    """
    try:
        async with performance_logger.async_timer("download_template"):
            # 生成模板内容
            template_content = _generate_template_content()
            
            # 生成文件名（格式：batch_replace_template_YYYYMMDD.txt）
            current_date = datetime.now().strftime("%Y%m%d")
            filename = f"batch_replace_template_{current_date}.txt"
            
            # 创建文件流
            file_stream = io.BytesIO(template_content.encode('utf-8'))
            
            # 记录操作
            security_logger.log_info(
                "Template downloaded",
                template_filename=filename
            )
            
            # 返回文件响应
            return Response(
                content=file_stream.getvalue(),
                media_type="text/plain",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}",
                    "Content-Type": "text/plain; charset=utf-8",
                    "Cache-Control": "no-cache"
                }
            )
            
    except Exception as e:
        security_logger.log_error(
            "Failed to download template",
            e
        )
        
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                status=ResponseStatus.ERROR,
                error_code=ErrorCode.GENERAL_ERROR,
                message="模板下载失败",
                details={"error": str(e)},
                timestamp=performance_logger.get_current_time()
            ).model_dump()
        )


@router.post(
    "/validate",
    response_model=ApiResponse[Dict[str, Any]],
    summary="验证规则文件",
    description="验证批量替换规则文件的格式和语法"
)
async def validate_rules_file(
    request: Request,
    rules_file: UploadFile = File(..., description="替换规则文件")
) -> ApiResponse[Dict[str, Any]]:
    """验证规则文件
    
    Args:
        request: FastAPI请求对象
        rules_file: 替换规则文件
        
    Returns:
        ApiResponse[Dict[str, Any]]: 验证结果
    """
    try:
        async with performance_logger.async_timer("validate_rules_file"):
            # 验证文件基本信息
            await _validate_rules_file_basic(rules_file)
            
            # 读取文件内容
            rules_content = await rules_file.read()
            rules_text = rules_content.decode('utf-8')
            
            # 执行详细验证
            validation_result = await replace_service.validate_rules_detailed(rules_text)
            
            # 记录操作
            security_logger.log_info(
                "Rules file validated",
                rules_filename=rules_file.filename,
                is_valid=validation_result["is_valid"],
                valid_rules_count=validation_result["valid_rules_count"],
                invalid_rules_count=validation_result["invalid_rules_count"]
            )
            
            # 将recommendation字段提升到顶层以匹配测试期望
            response_data = validation_result.copy()
            if "validation_summary" in validation_result and "recommendation" in validation_result["validation_summary"]:
                response_data["recommendation"] = validation_result["validation_summary"]["recommendation"]
            
            return ApiResponse(
                status=ResponseStatus.SUCCESS,
                message="规则文件验证完成",
                data=response_data
            )
            
    except HTTPException:
        raise
    except Exception as e:
        security_logger.log_error(
            "Failed to validate rules file",
            e,
            rules_file=rules_file.filename if rules_file else "unknown"
        )
        
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                status=ResponseStatus.ERROR,
                error_code=ErrorCode.REPLACE_RULES_INVALID,
                message="规则文件验证失败",
                details={"error": str(e)},
                timestamp=performance_logger.get_current_time()
            ).model_dump()
        )


@router.post(
    "/execute",
    response_model=ApiResponse[Dict[str, Any]],
    summary="执行批量替换",
    description="执行批量文本替换操作"
)
@_apply_rate_limit
async def execute_batch_replace(
    request: Request,
    background_tasks: BackgroundTasks,
    session_id: str,
    case_sensitive: bool = False,
    use_regex: bool = False,
    rules_file: UploadFile = File(..., description="替换规则文件")
) -> ApiResponse[Dict[str, Any]]:
    """执行批量替换
    
    Args:
        request: FastAPI请求对象
        background_tasks: 后台任务
        session_id: 会话ID
        case_sensitive: 是否区分大小写
        use_regex: 是否使用正则表达式
        rules_file: 替换规则文件
        
    Returns:
        ApiResponse[Dict[str, Any]]: 执行结果
    """
    temp_rules_path = None
    
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
        
        async with performance_logger.async_timer("execute_batch_replace"):
            # 验证规则文件
            await _validate_rules_file(rules_file)
            
            # 保存规则文件
            temp_rules_path = await _save_rules_file(rules_file, session_id)
            
            # 读取并解析规则文件
            rules_content = await rules_file.read()
            rules_text = rules_content.decode('utf-8')
            
            # 验证规则
            validation_result = await replace_service.validate_rules(rules_text)
            if not validation_result.is_valid:
                raise HTTPException(
                    status_code=400,
                    detail=ErrorResponse(
                        status=ResponseStatus.ERROR,
                        error_code=ErrorCode.REPLACE_RULES_INVALID,
                        message="规则验证失败",
                        details=validation_result.invalid_rules,
                        timestamp=performance_logger.get_current_time()
                    ).model_dump()
                )
            
            # 解析规则
            rules = await replace_service._parse_rules(rules_text)
            
            # 启动批量替换任务
            task_id = await replace_service.execute_batch_replace(
                session_id=session_id,
                rules=rules,
                case_sensitive=case_sensitive
            )
            
            # 记录操作
            security_logger.log_info(
                "Batch replace started",
                session_id=session_id,
                task_id=task_id,
                case_sensitive=case_sensitive,
                use_regex=use_regex,
                rules_file=rules_file.filename
            )
            
            return ApiResponse(
                status=ResponseStatus.SUCCESS,
                message="批量替换任务已启动",
                data={
                    "task_id": task_id,
                    "session_id": session_id,
                    "task_url": f"/api/v1/batch-replace/progress/{session_id}",
                    "progress_url": f"/api/v1/batch-replace/progress/{session_id}",
                    "report_url": f"/api/v1/batch-replace/report/{session_id}"
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"批量替换执行失败: {e}")
        print(f"错误堆栈: {error_traceback}")
        
        security_logger.log_error(
            "Failed to execute batch replace",
            e,
            session_id=session_id,
            rules_file=rules_file.filename if rules_file else "unknown"
        )
        
        # 清理临时文件
        if temp_rules_path and os.path.exists(temp_rules_path):
            try:
                os.remove(temp_rules_path)
            except Exception:
                pass
        
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                status=ResponseStatus.ERROR,
                error_code=ErrorCode.REPLACE_OPERATION_FAILED,
                message="批量替换执行失败",
                details={"error": str(e)},
                timestamp=performance_logger.get_current_time()
            ).model_dump()
        )


@router.get(
    "/progress/{session_id}",
    summary="获取替换进度",
    description="通过SSE获取批量替换的实时进度"
)
async def get_replace_progress(session_id: str):
    """获取替换进度（SSE）
    
    Args:
        session_id: 会话ID
        
    Returns:
        EventSourceResponse: SSE响应流
    """
    try:
        # 验证会话
        session_info = await session_service.get_session(session_id)
        if not session_info:
            raise HTTPException(
                status_code=404,
                detail="会话不存在"
            )
        
        async def progress_generator():
            """进度生成器"""
            try:
                # 获取当前任务ID（假设使用session_id作为task_id）
                current_progress = await replace_service.get_progress(session_id)
                if not current_progress:
                    # 如果没有进度信息，返回默认状态
                    default_progress = {
                        "task_id": session_id,
                        "status": "not_started",
                        "progress_percentage": 0.0,
                        "current_file": "",
                        "processed_files": 0,
                        "total_files": 0,
                        "total_replacements": 0
                    }
                    yield {
                        "event": "progress",
                        "data": default_progress
                    }
                    return
                
                # 持续监控进度
                while True:
                    progress = await replace_service.get_progress(session_id)
                    if progress:
                        # 发送进度数据
                        yield {
                            "event": "progress",
                            "data": progress.model_dump()
                        }
                        
                        # 如果完成，发送完成事件
                        if progress.status in ["completed", "failed", "cancelled"]:
                            yield {
                                "event": "complete",
                                "data": progress.model_dump()
                            }
                            break
                    
                    # 等待一段时间再检查
                    import asyncio
                    await asyncio.sleep(1)
                        
            except Exception as e:
                # 发送错误事件
                error_progress = ReplaceProgress(
                    session_id=session_id,
                    status="failed",
                    current_file="",
                    processed_files=0,
                    total_files=0,
                    progress_percentage=0,
                    error_message=str(e),
                    start_time=performance_logger.get_current_time(),
                    estimated_remaining_time=0
                )
                
                yield {
                    "event": "error",
                    "data": error_progress.json()
                }
        
        return EventSourceResponse(
            progress_generator(),
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        security_logger.log_error(
            "Failed to get replace progress",
            e,
            session_id=session_id
        )
        
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                status=ResponseStatus.ERROR,
                error_code=ErrorCode.GENERAL_ERROR,
                message="获取进度失败",
                details={"error": str(e)},
                timestamp=performance_logger.get_current_time()
            ).model_dump()
        )


@router.get(
    "/progress/{session_id}/json",
    response_model=ApiResponse[Dict[str, Any]],
    summary="获取替换进度（JSON格式）",
    description="获取批量替换的当前进度信息（JSON格式）"
)
async def get_replace_progress_json(session_id: str) -> ApiResponse[Dict[str, Any]]:
    """获取替换进度（JSON格式）
    
    Args:
        session_id: 会话ID
        
    Returns:
        ApiResponse[Dict[str, Any]]: 进度信息
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
        
        async with performance_logger.async_timer("get_replace_progress_json"):
            # 获取进度信息
            progress = await replace_service.get_progress(session_id)
            
            if not progress:
                 # 如果没有进度信息，返回默认状态
                 progress_data = {
                     "status": "pending",
                     "percentage": 0.0,
                     "current_file": None,
                     "total_files": 0,
                     "processed_files": 0,
                     "total_replacements": 0,
                     "current_rule": None,
                     "start_time": None,
                     "estimated_completion": None,
                     "error_message": None
                 }
            else:
                # 转换进度对象为字典
                progress_data = {
                    "status": progress.status.value if hasattr(progress.status, 'value') else str(progress.status),
                    "percentage": progress.percentage,
                    "current_file": progress.current_file,
                    "total_files": progress.total_files,
                    "processed_files": progress.processed_files,
                    "total_replacements": progress.total_replacements,
                    "current_rule": progress.current_rule,
                    "start_time": progress.start_time.isoformat() if progress.start_time else None,
                    "estimated_completion": progress.estimated_completion.isoformat() if progress.estimated_completion else None,
                    "error_message": progress.error_message
                }
            
            return ApiResponse(
                status=ResponseStatus.SUCCESS,
                message="获取进度成功",
                data={
                    "progress": progress_data
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        security_logger.log_error(
            "Failed to get replace progress",
            e,
            session_id=session_id
        )
        
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                status=ResponseStatus.ERROR,
                error_code=ErrorCode.GENERAL_ERROR,
                message="获取进度失败",
                details={"error": str(e)},
                timestamp=performance_logger.get_current_time()
            ).model_dump()
        )


@router.get(
    "/report/{session_id}",
    summary="获取替换报告",
    description="获取批量替换的详细报告"
)
async def get_replace_report(session_id: str):
    """获取替换报告
    
    Args:
        session_id: 会话ID
        
    Returns:
        StreamingResponse: HTML报告
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
        
        async with performance_logger.async_timer("get_replace_report"):
            # 获取替换报告
            report = await replace_service.get_report_by_session(session_id)
            
            if not report:
                raise HTTPException(
                    status_code=404,
                    detail=ErrorResponse(
                        status=ResponseStatus.ERROR,
                        error_code=ErrorCode.REPLACE_REPORT_NOT_FOUND,
                        message="替换报告不存在",
                        timestamp=performance_logger.get_current_time()
                    ).model_dump()
                )
            
            # 生成 HTML 报告
            try:
                # 获取源文件名
                source_filename = f'session_{session_id}'
                if session_info.original_filename:
                    source_filename = session_info.original_filename
                elif session_info.metadata and session_info.metadata.get('original_filename'):
                    source_filename = session_info.metadata.get('original_filename')
                
                # 生成 HTML 报告内容
                html_content = await report_service.generate_html_report(
                    report=report,
                    source_filename=source_filename,
                    style="green"
                )
                
                # 返回HTML响应
                return StreamingResponse(
                    iter([html_content.encode('utf-8')]),
                    media_type="text/html",
                    headers={
                        "Content-Disposition": f"inline; filename=replace_report_{session_id}.html",
                        "Cache-Control": "no-cache"
                    }
                )
                
            except Exception as e:
                # 如果生成 HTML 失败，返回 JSON 格式的报告
                import json
                json_content = json.dumps(report.model_dump(), ensure_ascii=False, indent=2)
                return StreamingResponse(
                    iter([json_content.encode('utf-8')]),
                    media_type="application/json",
                    headers={
                        "Content-Disposition": f"inline; filename=replace_report_{session_id}.json",
                        "Cache-Control": "no-cache"
                    }
                )
            
    except HTTPException:
        raise
    except Exception as e:
        security_logger.log_error(
            "Failed to get replace report",
            e,
            session_id=session_id
        )
        
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                status=ResponseStatus.ERROR,
                error_code=ErrorCode.GENERAL_ERROR,
                message="获取报告失败",
                details={"error": str(e)},
                timestamp=performance_logger.get_current_time()
            ).model_dump()
        )


@router.post(
    "/",
    response_model=ApiResponse[Dict[str, Any]],
    summary="启动批量替换",
    description="启动批量替换任务（简化版接口）"
)
@_apply_rate_limit
async def start_batch_replace(
    request: Request,
    background_tasks: BackgroundTasks,
    replace_request: BatchReplaceRequest
) -> ApiResponse[Dict[str, Any]]:
    """启动批量替换（简化版）
    
    Args:
        request: FastAPI请求对象
        background_tasks: 后台任务
        replace_request: 替换请求
        
    Returns:
        ApiResponse[Dict[str, Any]]: 启动结果
    """
    try:
        # 验证会话
        session_info = await session_service.get_session(replace_request.session_id)
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
        
        # 验证规则
        if not replace_request.rules:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    status=ResponseStatus.ERROR,
                    error_code=ErrorCode.INVALID_REQUEST,
                    message="替换规则不能为空",
                    timestamp=performance_logger.get_current_time()
                ).model_dump()
            )
        
        async with performance_logger.async_timer("start_batch_replace"):
            # 启动批量替换任务
            task_id = await replace_service.execute_batch_replace(
                session_id=replace_request.session_id,
                rules=replace_request.rules,
                case_sensitive=replace_request.case_sensitive,
                target_files=replace_request.target_files
            )
            
            return ApiResponse(
                status=ResponseStatus.SUCCESS,
                message="批量替换任务已启动",
                data={
                    "task_id": task_id,
                    "session_id": replace_request.session_id,
                    "task_url": f"/api/v1/batch-replace/progress/{replace_request.session_id}",
                    "progress_url": f"/api/v1/batch-replace/progress/{replace_request.session_id}",
                    "report_url": f"/api/v1/batch-replace/report/{replace_request.session_id}"
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        security_logger.log_error(
            "Failed to start batch replace",
            e,
            session_id=replace_request.session_id
        )
        
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                status=ResponseStatus.ERROR,
                error_code=ErrorCode.REPLACE_EXECUTION_FAILED,
                message="启动批量替换失败",
                details={"error": str(e)},
                timestamp=performance_logger.get_current_time()
            ).model_dump()
        )


@router.post(
    "/{session_id}",
    response_model=ApiResponse[Dict[str, Any]],
    summary="执行批量替换（会话路径）",
    description="通过会话ID路径执行批量文本替换操作"
)
@_apply_rate_limit
async def execute_batch_replace_by_session(
    request: Request,
    background_tasks: BackgroundTasks,
    session_id: str,
    case_sensitive: bool = False,
    use_regex: bool = False,
    rules_file: UploadFile = File(..., description="替换规则文件")
) -> ApiResponse[Dict[str, Any]]:
    """通过会话ID路径执行批量替换
    
    Args:
        request: FastAPI请求对象
        background_tasks: 后台任务
        session_id: 会话ID
        case_sensitive: 是否区分大小写
        use_regex: 是否使用正则表达式
        rules_file: 替换规则文件
        
    Returns:
        ApiResponse[Dict[str, Any]]: 执行结果
    """
    # 直接调用现有的execute_batch_replace函数
    return await execute_batch_replace(
        request=request,
        background_tasks=background_tasks,
        session_id=session_id,
        case_sensitive=case_sensitive,
        use_regex=use_regex,
        rules_file=rules_file
    )


@router.post(
    "/cancel/{session_id}",
    response_model=ApiResponse[Dict[str, Any]],
    summary="取消批量替换",
    description="取消正在进行的批量替换任务"
)
async def cancel_batch_replace_post(session_id: str) -> ApiResponse[Dict[str, Any]]:
    """取消批量替换（POST方法）
    
    Args:
        session_id: 会话ID
        
    Returns:
        ApiResponse[Dict[str, Any]]: 取消结果
    """
    return await cancel_batch_replace(session_id)


@router.delete(
    "/{session_id}",
    response_model=ApiResponse[Dict[str, Any]],
    summary="取消批量替换",
    description="取消正在进行的批量替换任务"
)
async def cancel_batch_replace(session_id: str) -> ApiResponse[Dict[str, Any]]:
    """取消批量替换
    
    Args:
        session_id: 会话ID
        
    Returns:
        ApiResponse[Dict[str, Any]]: 取消结果
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
        
        # 取消替换任务
        success = await replace_service.cancel_task(session_id)
        
        if success:
            return ApiResponse(
                status=ResponseStatus.SUCCESS,
                message="批量替换任务已取消",
                data={"session_id": session_id}
            )
        else:
            return ApiResponse(
                status=ResponseStatus.SUCCESS,
                message="没有正在进行的替换任务",
                data={"session_id": session_id}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        security_logger.log_error(
            "Failed to cancel batch replace",
            e,
            session_id=session_id
        )
        
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                status=ResponseStatus.ERROR,
                error_code=ErrorCode.GENERAL_ERROR,
                message="取消替换任务失败",
                details={"error": str(e)},
                timestamp=performance_logger.get_current_time()
            ).model_dump()
        )


async def _validate_rules_file_basic(file: UploadFile):
    """验证规则文件基本信息
    
    Args:
        file: 规则文件
        
    Raises:
        HTTPException: 验证失败
    """
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                status=ResponseStatus.ERROR,
                error_code=ErrorCode.INVALID_REQUEST,
                message="规则文件名不能为空",
                timestamp=performance_logger.get_current_time()
            ).model_dump()
        )
    
    if not file.filename.endswith('.txt'):
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                status=ResponseStatus.ERROR,
                error_code=ErrorCode.INVALID_REQUEST,
                message="规则文件必须是.txt格式",
                timestamp=performance_logger.get_current_time()
            ).model_dump()
        )
    
    # 检查文件大小
    content = await file.read()
    if len(content) > getattr(settings, 'max_rules_file_size', 1024 * 1024):  # 默认1MB
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                status=ResponseStatus.ERROR,
                error_code=ErrorCode.INVALID_REQUEST,
                message=f"规则文件大小不能超过{getattr(settings, 'max_rules_file_size', 1024 * 1024) // 1024}KB",
                timestamp=performance_logger.get_current_time()
            ).model_dump()
        )
    
    # 重置文件指针
    await file.seek(0)


async def _validate_rules_file(file: UploadFile):
    """验证规则文件
    
    Args:
        file: 规则文件
        
    Raises:
        HTTPException: 验证失败
    """
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="规则文件名不能为空"
        )
    
    if not file.filename.endswith('.txt'):
        raise HTTPException(
            status_code=400,
            detail="规则文件必须是.txt格式"
        )
    
    # 检查文件大小
    content = await file.read()
    if len(content) > settings.max_rules_file_size:
        raise HTTPException(
            status_code=400,
            detail=f"规则文件大小不能超过{settings.max_rules_file_size // 1024}KB"
        )
    
    # 重置文件指针
    await file.seek(0)


async def _save_rules_file(file: UploadFile, session_id: str) -> str:
    """保存规则文件
    
    Args:
        file: 规则文件
        session_id: 会话ID
        
    Returns:
        str: 保存的文件路径
    """
    try:
        # 生成安全的文件名
        secure_filename = security_validator.generate_secure_filename(file.filename)
        temp_path = os.path.join(
            settings.temp_dir,
            f"rules_{session_id}_{secure_filename}"
        )
        
        # 确保目录存在
        os.makedirs(settings.temp_dir, exist_ok=True)
        
        # 保存文件
        with open(temp_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        
        # 重置文件指针
        await file.seek(0)
        
        return temp_path
        
    except Exception as e:
        security_logger.log_error("Failed to save rules file", e, session_id=session_id)
        raise HTTPException(
            status_code=500,
            detail="保存规则文件失败"
        )


def _generate_template_content() -> str:
    """生成批量替换规则模板内容
    
    Returns:
        str: 模板内容
    """
    template = """# AetherFolio 批量替换规则模板
# 生成时间: {timestamp}
# 使用说明:
# 1. 每行一个替换规则
# 2. 格式: 原文本 -> 新文本
# 3. 支持正则表达式（在规则前添加 REGEX: 前缀）
# 4. 支持大小写敏感（在规则前添加 CASE: 前缀）
# 5. 以 # 开头的行为注释，将被忽略
# 6. 空行将被忽略

# ========== 基本替换示例 ==========
# 简单文本替换
旧文本 -> 新文本
错误的词汇 -> 正确的词汇

# ========== 正则表达式替换示例 ==========
# 使用正则表达式进行复杂替换
REGEX: \\d{{4}}-\\d{{2}}-\\d{{2}} -> [日期已隐藏]
REGEX: [a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{{2,}} -> [邮箱已隐藏]

# ========== 大小写敏感替换示例 ==========
# 区分大小写的替换
CASE: HTML -> html
CASE: JavaScript -> JS

# ========== 组合模式示例 ==========
# 同时使用正则表达式和大小写敏感
CASE:REGEX: Chapter\\s+(\\d+) -> 第$1章

# ========== 特殊字符处理示例 ==========
# 处理包含特殊字符的文本
\"引号内容\" -> '引号内容'
<标签> -> [标签]

# ========== 多语言支持示例 ==========
# 中英文混合替换
Hello World -> 你好世界
数据库 -> Database

# ========== 格式化示例 ==========
# 统一格式
  多余空格  ->  标准空格
\\t制表符 -> 四个空格

# ========== 自定义规则区域 ==========
# 请在下方添加您的自定义替换规则

"""
    
    # 添加当前时间戳
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return template.format(timestamp=current_time)


# 导出路由器
__all__ = ["router"]