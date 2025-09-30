"""批量替换API路由"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional
import json
import tempfile
import os

from services.replace_service import replace_service
from core.logging import performance_logger
from db.models.schemas import (
    ReplaceValidationResponse,
    ReplaceExecuteResponse,
    ReplaceReportResponse
)

router = APIRouter(prefix="/api/v1/batch-replace", tags=["batch-replace"])


@router.get("/template")
async def download_template():
    """下载规则模板文件"""
    try:
        template_content = replace_service.get_template_content()
        
        return StreamingResponse(
            iter([template_content.encode('utf-8')]),
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": "attachment; filename=batch_replace_rules_template.txt"
            }
        )
    except Exception as e:
        performance_logger.error(f"Template download failed: {str(e)}")
        raise HTTPException(status_code=500, detail="模板下载失败")


@router.post("/validate", response_model=ReplaceValidationResponse)
async def validate_rules(
    rules_file: UploadFile = File(...)
):
    """验证规则文件"""
    try:
        # 检查文件大小
        from core.config import settings
        content = await rules_file.read()
        file_size = len(content)
        
        if file_size > settings.max_rules_file_size:
            raise HTTPException(
                status_code=413, 
                detail=f"规则文件过大，最大允许大小为 {settings.max_rules_file_size // (1024*1024)}MB"
            )
        
        # 读取规则文件内容
        rules_content = content.decode('utf-8')
        
        # 使用详细验证方法
        validation_result = await replace_service.validate_rules_detailed(rules_content)
        
        # 构建响应数据，直接返回详细验证结果
        response_data = {
            "success": True,
            "valid": validation_result["is_valid"],
            "rule_count": validation_result["total_rules_count"],
            "rules_preview": validation_result["rule_preview"],
            "errors": [error for rule in validation_result["invalid_rules"] for error in rule["errors"]],
            "warnings": validation_result["warnings"],
            "statistics": validation_result["statistics"],
            "validation_summary": validation_result["validation_summary"],
            "valid_rules": validation_result["valid_rules"],
            "invalid_rules": validation_result["invalid_rules"],
            "dangerous_operations": validation_result["dangerous_operations"]
        }
        
        performance_logger.info(
            f"Rules validation completed: {validation_result['is_valid']}",
            extra={
                "rule_count": validation_result["total_rules_count"],
                "valid": validation_result["is_valid"]
            }
        )
        
        return response_data
        
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="规则文件编码错误，请使用UTF-8编码")
    except Exception as e:
        performance_logger.error(f"Rules validation failed: {str(e)}")
        # 返回验证失败的结果而不是抛出500错误
        return {
            "success": False,
            "valid": False,
            "rule_count": 0,
            "rules_preview": [],
            "errors": [f"规则验证失败: {str(e)}"],
            "warnings": [],
            "statistics": {"total_lines": 0, "non_empty_lines": 0, "comment_lines": 0, "empty_lines": 0},
            "validation_summary": {
                "can_proceed": False,
                "has_warnings": False,
                "recommendation": f"规则验证失败: {str(e)}"
            },
            "valid_rules": [],
            "invalid_rules": [],
            "dangerous_operations": []
        }


@router.post("/execute")
async def execute_replace(
    session_id: str = Form(...),
    rules_file: UploadFile = File(...)
):
    """执行批量替换"""
    try:
        # 读取规则文件
        content = await rules_file.read()
        rules_content = content.decode('utf-8')
        
        # 执行替换
        result = await replace_service.execute_replace(
            session_id=session_id,
            rules_content=rules_content
        )
        
        performance_logger.info(
            f"Replace execution started",
            extra={
                "session_id": session_id,
                "task_id": result["task_id"]
            }
        )
        
        # 构造响应对象，匹配测试期望的格式
        return {
            "success": True,
            "data": {
                "task_id": result["task_id"],
                "session_id": result["session_id"],
                "message": result["message"]
            }
        }
        
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="规则文件编码错误，请使用UTF-8编码")
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        performance_logger.error(f"Replace execution failed: {str(e)}\nTraceback: {error_details}")
        raise HTTPException(status_code=500, detail=f"替换执行失败: {str(e)}")


@router.get("/progress/{task_id}")
async def get_progress(task_id: str):
    """获取替换进度 (JSON)"""
    try:
        progress = await replace_service.get_progress(task_id)
        if progress:
            return {
                "success": True,
                "data": {
                    "status": progress.status,
                    "progress": progress.progress_percentage,
                    "current_file": progress.current_file,
                    "processed_files": progress.processed_files,
                    "total_files": progress.total_files,
                    "estimated_remaining": progress.estimated_remaining
                }
            }
        else:
            raise HTTPException(status_code=404, detail="任务不存在")
    except Exception as e:
        performance_logger.error(f"Progress query failed: {str(e)}")
        raise HTTPException(status_code=500, detail="进度获取失败")


@router.get("/progress-stream/{session_id}")
async def get_progress_stream(session_id: str):
    """获取替换进度 (SSE)"""
    try:
        # 根据session_id查找task_id
        task_id = replace_service.session_to_task.get(session_id)
        if not task_id:
            # 如果没有找到task_id，创建一个空的进度流
            async def empty_stream():
                import json
                import asyncio
                # 立即发送初始连接确认消息
                yield f"data: {json.dumps({'status': 'waiting', 'progress': 0.0, 'message': 'Waiting for task to start'})}\r\n\r\n"
                # 持续发送心跳消息
                for i in range(30):  # 30秒后停止
                    await asyncio.sleep(1)
                    yield f"data: {json.dumps({'status': 'waiting', 'progress': 0.0, 'heartbeat': i+1})}\r\n\r\n"
            
            return StreamingResponse(
                empty_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive"
                }
            )
        
        return StreamingResponse(
            replace_service.get_progress_stream(task_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )
    except Exception as e:
        performance_logger.error(f"Progress stream failed: {str(e)}")
        raise HTTPException(status_code=500, detail="进度获取失败")


@router.get("/report/{session_id}")
async def get_report(
    session_id: str,
    request: Request,
    format: Optional[str] = "json"
):
    """获取替换报告（带缓存机制）"""
    from fastapi.responses import JSONResponse, Response
    import hashlib
    from datetime import datetime, timedelta
    
    # 添加调试日志
    performance_logger.info(
        f"get_report called for session_id: {session_id}",
        extra={"session_id": session_id, "format": format}
    )
    
    try:
        report = await replace_service.get_report_by_session(session_id)
        
        if not report:
            raise HTTPException(status_code=404, detail="报告不存在")
        
        # 构造响应数据
        result = {
            "success": True,
            "data": {
                "total_files": report.total_files,
                "files_processed": report.total_files,
                "total_replacements": report.total_replacements,
                "generated_at": report.generated_at,
                "file_stats": report.file_stats,
                "rule_stats": report.rule_stats,
                "task_id": report.task_id,
                "session_id": report.session_id
            }
        }
        
        # 生成ETag用于缓存验证
        content_hash = hashlib.md5(str(result).encode()).hexdigest()
        etag = f'"{content_hash}"'
        
        # 设置缓存头信息
        from datetime import datetime
        last_modified = datetime.fromtimestamp(report.generated_at).strftime("%a, %d %b %Y %H:%M:%S GMT")
        
        # 检查条件请求头
        if_none_match = request.headers.get("If-None-Match")
        if_modified_since = request.headers.get("If-Modified-Since")
        
        # 处理条件请求
        cache_hit = False
        if if_none_match and if_none_match == etag:
            cache_hit = True
        elif if_modified_since and if_modified_since == last_modified:
            cache_hit = True
        
        # 如果缓存命中，返回304 Not Modified
        if cache_hit:
            headers = {
                "Cache-Control": "public, max-age=300",
                "ETag": etag,
                "Last-Modified": last_modified,
                "X-Cache": "HIT",
                "Vary": "Accept-Encoding"
            }
            
            performance_logger.info(
                f"Cache hit for report",
                extra={
                    "session_id": session_id,
                    "etag": etag,
                    "cache_status": "HIT"
                }
            )
            
            response = Response(status_code=304)
            for key, value in headers.items():
                response.headers[key] = value
            return response
        
        # 缓存未命中，返回完整响应
        headers = {
            "Cache-Control": "public, max-age=300",  # 缓存5分钟
            "ETag": etag,
            "Last-Modified": last_modified,
            "X-Cache": "MISS",  # 首次请求标记为MISS
            "Vary": "Accept-Encoding"
        }
        
        performance_logger.info(
            f"Report generated with cache headers",
            extra={
                "session_id": session_id,
                "format": format,
                "etag": etag,
                "cache_status": "MISS",
                "headers": headers
            }
        )
        
        # 创建JSONResponse并确保头被正确设置
        response = JSONResponse(content=result)
        for key, value in headers.items():
            response.headers[key] = value
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        performance_logger.error(f"Report generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="报告生成失败")