"""AetherFolio 后端主应用"""

import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# 导入配置和核心模块
from core.config import settings
from core.logging import performance_logger, security_logger
from db.models.schemas import ErrorResponse, ResponseStatus, ErrorCode

# 导入中间件
from middleware.performance import (
    PerformanceMiddleware,
    RequestSizeMiddleware,
    SecurityHeadersMiddleware,
    ErrorHandlingMiddleware
)

# 导入API路由
from api.upload import router as upload_router
from api.replace import router as replace_router
from api.files import router as files_router
from api.sessions import router as sessions_router
from api.rules import router as rules_router
from api.endpoints.export import router as export_router
from api.endpoints.search_replace import router as search_replace_router
# from api.endpoints.file_content import router as file_content_router  # 已合并到files_router
from api.endpoints.save_file import router as save_file_router
from api.endpoints.auth import router as auth_router
from api.endpoints.epub_chapters import router as epub_chapters_router
from api.endpoints.backup import router as backup_router
from api.websocket import router as websocket_router
from api.static import router as static_router
from api.preview import router as preview_router

# 导入服务
from services.session_service import session_service
from services.epub_service import epub_service
from services.replace_service import replace_service
from services.preview_service import preview_service
from services.file_service import file_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    try:
        # 确保必要的目录存在
        settings.ensure_directories()
        
        # 初始化数据库
        from db.connection import db_manager
        db_manager.initialize_default_databases()
        db_manager.create_all_tables()
        
        # 初始化服务
        await session_service.initialize()
        await epub_service.initialize()
        await replace_service.initialize()
        await preview_service.initialize()
        await file_service.initialize()
        
        # 启动定期清理任务
        cleanup_task = asyncio.create_task(_periodic_cleanup())
        
        security_logger.info(
            "AetherFolio backend started successfully",
            extra={
                "version": "1.0.0",
                "debug": settings.debug,
                "host": settings.host,
                "port": settings.port,
                "event_type": "startup"
            }
        )
        
        yield
        
    except Exception as e:
        security_logger.error(
            "Error during startup",
            extra={
                "error": str(e),
                "event_type": "startup_error"
            }
        )
        raise
        
    finally:
        # 关闭时清理
        try:
            # 停止定期清理任务
            cleanup_task.cancel()
            try:
                await cleanup_task
            except asyncio.CancelledError:
                pass
            
            # 清理服务
            await preview_service.cleanup()
            await replace_service.cleanup()
            await epub_service.cleanup()
            await session_service.cleanup()
            await file_service.cleanup()
            
            security_logger.info("AetherFolio backend stopped", extra={"event_type": "shutdown"})
            
        except Exception as e:
            security_logger.error("Error during shutdown", extra={"error": str(e), "event_type": "shutdown_error"})


# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    description="AetherFolio EPUB编辑器后端API",
    version="1.0.0",
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# 创建限流器
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"]
)

# 添加自定义中间件（按顺序添加）
# 注意：中间件是按照相反的顺序执行的，最后添加的最先执行
app.add_middleware(PerformanceMiddleware)
app.add_middleware(RequestSizeMiddleware, max_size=settings.max_request_size)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(ErrorHandlingMiddleware)

# 添加限流异常处理
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# 全局异常处理器
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """HTTP异常处理器"""
    request_id = getattr(request.state, "request_id", "unknown")
    
    # 记录HTTP异常
    if exc.status_code >= 500:
        security_logger.error(
            f"HTTP exception occurred: {exc.detail}",
            extra={
                "request_id": request_id,
                "status_code": exc.status_code,
                "url": str(request.url)
            }
        )
    elif exc.status_code >= 400:
        security_logger.warning(
            f"Client error: {exc.detail}",
            extra={
                "request_id": request_id,
                "status_code": exc.status_code,
                "url": str(request.url)
            }
        )
    
    # 处理detail的序列化，支持字典、Pydantic模型等复杂对象
    import json
    from datetime import datetime
    from pydantic import BaseModel
    
    def datetime_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, BaseModel):
            return obj.model_dump()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    try:
        # 尝试序列化detail对象
        if isinstance(exc.detail, (dict, BaseModel)):
            content_str = json.dumps(exc.detail, default=datetime_serializer, ensure_ascii=False)
            content = json.loads(content_str)
        else:
            # 对于其他类型，包装成简单错误响应格式
            content = {
                "success": False,
                "error": str(exc.detail)
            }
        
        return JSONResponse(
            status_code=exc.status_code,
            content=content,
            headers={"X-Request-ID": request_id}
        )
    except (TypeError, ValueError) as e:
        # 如果序列化失败，回退到简单错误响应
        simple_error = {
            "success": False,
            "error": str(exc.detail)
        }
        
        return JSONResponse(
            status_code=exc.status_code,
            content=simple_error,
            headers={"X-Request-ID": request_id}
        )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    """请求验证异常处理器"""
    request_id = getattr(request.state, "request_id", "unknown")
    
    security_logger.warning(
        "Request validation error",
        extra={
            "request_id": request_id,
            "errors": exc.errors(),
            "url": str(request.url)
        }
    )
    
    simple_error = {
        "success": False,
        "error": "请求参数验证失败"
    }
    
    return JSONResponse(
        status_code=422,
        content=simple_error,
        headers={"X-Request-ID": request_id}
    )


@app.exception_handler(StarletteHTTPException)
async def starlette_exception_handler(request, exc: StarletteHTTPException):
    """Starlette HTTP异常处理器"""
    request_id = getattr(request.state, "request_id", "unknown")
    
    security_logger.warning(
        f"Starlette HTTP exception: {exc.detail}",
        extra={
            "request_id": request_id,
            "status_code": exc.status_code,
            "url": str(request.url)
        }
    )
    
    simple_error = {
        "success": False,
        "error": str(exc.detail)
    }
    
    return JSONResponse(
        status_code=exc.status_code,
        content=simple_error,
        headers={"X-Request-ID": request_id}
    )


# 注册API路由
app.include_router(auth_router)  # auth_router已经包含了完整的prefix
app.include_router(upload_router, prefix="/api/v1")
app.include_router(replace_router)  # replace_router已经包含了完整的prefix
app.include_router(files_router)  # files_router已经包含了完整的prefix
app.include_router(sessions_router)  # sessions_router已经包含了完整的prefix
app.include_router(rules_router)  # rules_router已经包含了完整的prefix
app.include_router(export_router)  # export_router已经包含了完整的prefix
app.include_router(search_replace_router, prefix="/api/v1")
# app.include_router(file_content_router)  # 已合并到files_router，避免重复注册
app.include_router(save_file_router)  # save_file_router已经包含了完整的prefix
app.include_router(epub_chapters_router)  # epub_chapters_router已经包含了完整的prefix
app.include_router(backup_router)  # backup_router已经包含了完整的prefix
app.include_router(websocket_router)  # websocket_router已经包含了完整的prefix
app.include_router(static_router)  # static_router已经包含了完整的prefix
app.include_router(preview_router)  # preview_router已经包含了完整的prefix

# 为BE-01任务添加统一上传端点
from api.upload import upload_file
app.post("/api/v1/upload")(upload_file)


# 根路径
@app.get("/", include_in_schema=False)
async def root():
    """根路径"""
    return {
        "message": "AetherFolio EPUB Editor Backend",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.debug else "disabled"
    }


# 健康检查
@app.get("/health", include_in_schema=False)
async def health_check():
    """健康检查"""
    try:
        # 检查各个服务的状态
        session_count = len(await session_service.list_sessions())
        
        return {
            "status": "healthy",
            "timestamp": performance_logger.get_current_time(),
            "version": "1.0.0",
            "services": {
                "session_service": "healthy",
                "epub_service": "healthy",
                "replace_service": "healthy",
                "preview_service": "healthy"
            },
            "metrics": {
                "active_sessions": session_count
            }
        }
    except Exception as e:
        security_logger.error(f"Health check failed: {e}")
        
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": performance_logger.get_current_time(),
                "error": str(e)
            }
        )


# 版本信息
@app.get("/version", include_in_schema=False)
async def version_info():
    """版本信息"""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "description": "AetherFolio EPUB编辑器后端API",
        "python_version": "3.8+",
        "fastapi_version": "0.104+"
    }


async def _periodic_cleanup():
    """定期清理任务"""
    while True:
        try:
            # 等待清理间隔
            await asyncio.sleep(settings.cleanup_interval)
            
            # 清理过期会话
            cleaned_count = await session_service.cleanup_expired_sessions()
            
            # 清理断开连接的会话（1小时后清理）
            disconnected_count = await session_service.cleanup_disconnected_sessions(max_age_hours=1)
            
            if cleaned_count > 0 or disconnected_count > 0:
                security_logger.logger.info(
                    "Periodic cleanup completed",
                    extra={
                        "cleaned_expired_sessions": cleaned_count,
                        "cleaned_disconnected_sessions": disconnected_count
                    }
                )
            
        except asyncio.CancelledError:
            # 任务被取消，正常退出
            break
        except Exception as e:
            security_logger.logger.error(f"Error in periodic cleanup: {e}")
            # 继续运行，不要因为清理错误而停止


if __name__ == "__main__":
    import uvicorn
    
    # 运行应用
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug",
        access_log=True
    )