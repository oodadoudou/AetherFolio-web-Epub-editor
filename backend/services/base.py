"""服务层基础类"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TypeVar, Generic
from contextlib import asynccontextmanager
from core.logging import get_logger, performance_logger
from core.config import settings


T = TypeVar('T')


class BaseService(ABC):
    """服务基础类"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = get_logger(service_name)
        self._initialized = False
    
    async def initialize(self):
        """初始化服务"""
        if self._initialized:
            return
            
        self.logger.info(f"Initializing {self.service_name} service")
        await self._initialize()
        self._initialized = True
        self.logger.info(f"{self.service_name} service initialized successfully")
    
    async def cleanup(self):
        """清理服务资源"""
        if not self._initialized:
            return
            
        self.logger.info(f"Cleaning up {self.service_name} service")
        await self._cleanup()
        self._initialized = False
        self.logger.info(f"{self.service_name} service cleaned up successfully")
    
    @abstractmethod
    async def _initialize(self):
        """子类实现的初始化逻辑"""
        pass
    
    @abstractmethod
    async def _cleanup(self):
        """子类实现的清理逻辑"""
        pass
    
    @asynccontextmanager
    async def performance_context(self, operation: str, **kwargs):
        """性能监控上下文管理器"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            performance_logger.info(
                f"Operation {self.service_name}.{operation} completed in {duration:.3f}s",
                extra={
                    "operation": f"{self.service_name}.{operation}",
                    "duration": duration,
                    **kwargs
                }
            )
    
    def log_error(self, message: str, error: Exception, **kwargs):
        """记录错误日志"""
        self.logger.error(
            message,
            extra={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "service": self.service_name,
                **kwargs
            },
            exc_info=True
        )
    
    def log_info(self, message: str, **kwargs):
        """记录信息日志"""
        self.logger.info(
            message,
            extra={
                "service": self.service_name,
                **kwargs
            }
        )
    
    def log_warning(self, message: str, **kwargs):
        """记录警告日志"""
        self.logger.warning(
            message,
            extra={
                "service": self.service_name,
                **kwargs
            }
        )


class CacheableService(BaseService, Generic[T]):
    """支持缓存的服务基础类"""
    
    def __init__(self, service_name: str, cache_ttl: int = 300):
        super().__init__(service_name)
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def _get_cache_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        import hashlib
        import json
        
        cache_data = {
            "args": args,
            "kwargs": kwargs
        }
        cache_str = json.dumps(cache_data, sort_keys=True, default=str)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """检查缓存是否有效"""
        if not cache_entry:
            return False
            
        cache_time = cache_entry.get("timestamp", 0)
        return time.time() - cache_time < self.cache_ttl
    
    def get_from_cache(self, cache_key: str) -> Optional[T]:
        """从缓存获取数据"""
        cache_entry = self._cache.get(cache_key)
        if self._is_cache_valid(cache_entry):
            self.log_info("Cache hit", cache_key=cache_key)
            return cache_entry["data"]
        
        # 清理过期缓存
        if cache_entry:
            del self._cache[cache_key]
            
        return None
    
    def set_cache(self, cache_key: str, data: T):
        """设置缓存数据"""
        self._cache[cache_key] = {
            "data": data,
            "timestamp": time.time()
        }
        self.log_info("Cache set", cache_key=cache_key)
    
    def clear_cache(self, pattern: Optional[str] = None):
        """清理缓存"""
        if pattern:
            import re
            keys_to_remove = [
                key for key in self._cache.keys()
                if re.search(pattern, key)
            ]
            for key in keys_to_remove:
                del self._cache[key]
            self.log_info("Cache cleared by pattern", pattern=pattern, count=len(keys_to_remove))
        else:
            self._cache.clear()
            self.log_info("All cache cleared")
    
    async def _cleanup(self):
        """清理缓存"""
        self.clear_cache()
        await super()._cleanup()


class AsyncTaskService(BaseService):
    """异步任务服务基础类"""
    
    def __init__(self, service_name: str, max_concurrent_tasks: int = 10):
        super().__init__(service_name)
        self.max_concurrent_tasks = max_concurrent_tasks
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._running_tasks: Dict[str, asyncio.Task] = {}
    
    async def _initialize(self):
        """初始化信号量"""
        self._semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
    
    async def _cleanup(self):
        """取消所有运行中的任务"""
        if self._running_tasks:
            self.log_info("Cancelling running tasks", count=len(self._running_tasks))
            
            for task_id, task in self._running_tasks.items():
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        self.log_info("Task cancelled", task_id=task_id)
                    except Exception as e:
                        self.log_error("Error cancelling task", e, task_id=task_id)
            
            self._running_tasks.clear()
    
    async def run_task(self, task_id: str, coro, timeout: Optional[float] = None):
        """运行异步任务"""
        if not self._semaphore:
            raise RuntimeError("Service not initialized")
        
        async with self._semaphore:
            try:
                self.log_info("Starting task", task_id=task_id)
                
                if timeout:
                    task = asyncio.create_task(asyncio.wait_for(coro, timeout=timeout))
                else:
                    task = asyncio.create_task(coro)
                
                self._running_tasks[task_id] = task
                
                result = await task
                
                self.log_info("Task completed", task_id=task_id)
                return result
                
            except asyncio.TimeoutError:
                self.log_warning("Task timeout", task_id=task_id, timeout=timeout)
                raise
            except Exception as e:
                self.log_error("Task failed", e, task_id=task_id)
                raise
            finally:
                self._running_tasks.pop(task_id, None)
    
    def get_running_tasks(self) -> Dict[str, bool]:
        """获取运行中的任务状态"""
        return {
            task_id: not task.done()
            for task_id, task in self._running_tasks.items()
        }
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消指定任务"""
        task = self._running_tasks.get(task_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                self.log_info("Task cancelled", task_id=task_id)
                return True
            except Exception as e:
                self.log_error("Error cancelling task", e, task_id=task_id)
        
        return False


# 导出
__all__ = [
    "BaseService",
    "CacheableService", 
    "AsyncTaskService"
]