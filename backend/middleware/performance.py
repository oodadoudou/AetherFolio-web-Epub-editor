"""性能监控中间件"""

import time
import uuid
from datetime import datetime
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from backend.core.logging import performance_logger, security_logger
from backend.core.config import settings


class PerformanceMiddleware(BaseHTTPMiddleware):
    """性能监控中间件"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.slow_request_threshold = settings.slow_request_threshold
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并监控性能
        
        Args:
            request: HTTP请求
            call_next: 下一个处理器
            
        Returns:
            Response: HTTP响应
        """
        # 生成请求ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # 记录请求开始时间
        start_time = time.time()
        
        # 提取请求信息
        method = request.method
        url = str(request.url)
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        # 记录请求开始
        performance_logger.logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": method,
                "url": url,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "event_type": "request_start"
            }
        )
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 添加性能头
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.4f}"
            
            # 记录请求完成
            log_level = "warning" if process_time > self.slow_request_threshold else "info"
            
            if log_level == "warning":
                performance_logger.logger.warning(
                    "Request completed (slow)",
                    extra={
                        "request_id": request_id,
                        "method": method,
                        "url": url,
                        "status_code": response.status_code,
                        "process_time": process_time,
                        "client_ip": client_ip,
                        "is_slow": True,
                        "event_type": "request_complete"
                    }
                )
            else:
                performance_logger.logger.info(
                    "Request completed",
                    extra={
                        "request_id": request_id,
                        "method": method,
                        "url": url,
                        "status_code": response.status_code,
                        "process_time": process_time,
                        "client_ip": client_ip,
                        "is_slow": False,
                        "event_type": "request_complete"
                    }
                )
            
            # 如果是慢请求，额外记录
            if process_time > self.slow_request_threshold:
                security_logger.logger.warning(
                    "Slow request detected",
                    extra={
                        "request_id": request_id,
                        "method": method,
                        "url": url,
                        "process_time": process_time,
                        "threshold": self.slow_request_threshold,
                        "event_type": "slow_request"
                    }
                )
            
            return response
            
        except Exception as e:
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录错误
            performance_logger.logger.error(
                "Request failed",
                extra={
                    "error": str(e),
                    "request_id": request_id,
                    "method": method,
                    "url": url,
                    "process_time": process_time,
                    "client_ip": client_ip,
                    "event_type": "request_error"
                }
            )
            
            # 重新抛出异常
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址
        
        Args:
            request: HTTP请求
            
        Returns:
            str: 客户端IP地址
        """
        # 检查代理头
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # 取第一个IP（原始客户端IP）
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # 使用直接连接的IP
        if hasattr(request.client, "host"):
            return request.client.host
        
        return "unknown"


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """请求大小限制中间件"""
    
    def __init__(self, app: ASGIApp, max_size: int = None):
        super().__init__(app)
        self.max_size = max_size or settings.max_request_size
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """检查请求大小
        
        Args:
            request: HTTP请求
            call_next: 下一个处理器
            
        Returns:
            Response: HTTP响应
        """
        # 检查Content-Length头
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_size:
                    security_logger.logger.warning(
                        "Request size exceeded",
                        extra={
                            "content_length": size,
                            "max_size": self.max_size,
                            "client_ip": self._get_client_ip(request),
                            "url": str(request.url),
                            "event_type": "request_size_exceeded"
                        }
                    )
                    
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=413,
                        detail=f"Request entity too large. Maximum size: {self.max_size} bytes"
                    )
            except ValueError:
                # 无效的Content-Length头
                pass
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        if hasattr(request.client, "host"):
            return request.client.host
        
        return "unknown"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全头中间件"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """添加安全头
        
        Args:
            request: HTTP请求
            call_next: 下一个处理器
            
        Returns:
            Response: HTTP响应
        """
        response = await call_next(request)
        
        # 添加安全头
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            )
        }
        
        for header, value in security_headers.items():
            response.headers[header] = value
        
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """错误处理中间件"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理未捕获的异常
        
        Args:
            request: HTTP请求
            call_next: 下一个处理器
            
        Returns:
            Response: HTTP响应
        """
        try:
            return await call_next(request)
        except Exception as e:
            # 不要捕获HTTPException，让它正常传播
            from fastapi import HTTPException
            if isinstance(e, HTTPException):
                raise
            
            # 记录未捕获的异常
            import traceback
            request_id = getattr(request.state, "request_id", "unknown")
            
            security_logger.logger.error(
                "Unhandled exception in middleware",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(request.url),
                    "client_ip": self._get_client_ip(request),
                    "event_type": "unhandled_exception"
                }
            )
            
            # 也打印到控制台以便调试
            print(f"Unhandled exception: {type(e).__name__}: {str(e)}")
            print(traceback.format_exc())
            
            # 返回简单错误响应
            from fastapi.responses import JSONResponse
            
            simple_error = {
                "success": False,
                "error": "服务器内部错误"
            }
            
            return JSONResponse(
                status_code=500,
                content=simple_error,
                headers={"X-Request-ID": request_id}
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        if hasattr(request.client, "host"):
            return request.client.host
        
        return "unknown"


# 导出中间件类
__all__ = [
    "PerformanceMiddleware",
    "RequestSizeMiddleware",
    "SecurityHeadersMiddleware",
    "ErrorHandlingMiddleware"
]