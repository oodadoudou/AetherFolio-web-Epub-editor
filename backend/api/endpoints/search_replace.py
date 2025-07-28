# Search and Replace endpoint
# Handles search and replace operations

import re
from typing import Dict, Any, List, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel

from backend.models.schemas import (
    ApiResponse, ErrorResponse, ResponseStatus, ErrorCode
)
from backend.services.session_service import session_service
from backend.services.text_service import text_service
from backend.services.epub_service import epub_service
from backend.core.config import settings
from backend.core.logging import performance_logger, security_logger

router = APIRouter(prefix="/search-replace", tags=["search-replace"])
limiter = Limiter(key_func=get_remote_address)


class SearchRequest(BaseModel):
    """搜索请求模型"""
    query: str
    case_sensitive: bool = False
    use_regex: bool = False
    whole_word: bool = False


class SearchResult(BaseModel):
    """搜索结果模型"""
    file_path: str
    line_number: int
    column_start: int
    column_end: int
    matched_text: str
    context_before: str
    context_after: str


class ReplaceRequest(BaseModel):
    """替换请求模型"""
    original: str
    replacement: str
    case_sensitive: bool = False
    use_regex: bool = False
    whole_word: bool = False


@router.post(
    "/{session_id}/search",
    response_model=ApiResponse[List[SearchResult]],
    summary="搜索文本",
    description="在文件中搜索指定文本"
)
@limiter.limit("10/minute")
async def search_in_files(
    request: Request,
    session_id: str, 
    search_request: SearchRequest
) -> ApiResponse[List[SearchResult]]:
    """在文件中搜索文本
    
    Args:
        request: FastAPI请求对象
        session_id: 会话ID
        search_request: 搜索请求
        
    Returns:
        ApiResponse[List[SearchResult]]: 搜索结果
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
        
        async with performance_logger.async_timer("search_in_files"):
            file_type = session_info.metadata.get('file_type', 'epub')
            results = []
            
            if file_type == 'text':
                # 搜索TEXT文件
                results = await _search_text_file(
                    session_id, search_request, session_info
                )
            else:
                # 搜索EPUB文件
                results = await _search_epub_files(
                    session_id, search_request
                )
            
            security_logger.log_info(
                "Search completed",
                session_id=session_id,
                query=search_request.query,
                results_count=len(results)
            )
            
            return ApiResponse(
                status=ResponseStatus.SUCCESS,
                message=f"搜索完成，找到 {len(results)} 个结果",
                data=results
            )
            
    except HTTPException:
        raise
    except Exception as e:
        security_logger.log_error(
            "Failed to search in files",
            e,
            session_id=session_id,
            query=search_request.query
        )
        
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                status=ResponseStatus.ERROR,
                error_code=ErrorCode.GENERAL_ERROR,
                message="搜索失败",
                details={"error": str(e)},
                timestamp=performance_logger.get_current_time()
            ).model_dump()
        )


@router.post(
    "/{session_id}/replace",
    response_model=ApiResponse[Dict[str, Any]],
    summary="替换文本",
    description="在文件中替换指定文本"
)
@limiter.limit("5/minute")
async def replace_in_files(
    request: Request,
    session_id: str, 
    replace_request: ReplaceRequest
) -> ApiResponse[Dict[str, Any]]:
    """在文件中替换文本
    
    Args:
        request: FastAPI请求对象
        session_id: 会话ID
        replace_request: 替换请求
        
    Returns:
        ApiResponse[Dict[str, Any]]: 替换结果
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
        
        async with performance_logger.async_timer("replace_in_files"):
            file_type = session_info.metadata.get('file_type', 'epub')
            
            if file_type == 'text':
                # 替换TEXT文件
                result = await _replace_text_file(
                    session_id, replace_request, session_info
                )
            else:
                # 替换EPUB文件
                result = await _replace_epub_files(
                    session_id, replace_request
                )
            
            security_logger.log_info(
                "Replace completed",
                session_id=session_id,
                search_text=replace_request.original,
                replace_text=replace_request.replacement,
                replacements=result.get('total_replacements', 0)
            )
            
            return ApiResponse(
                status=ResponseStatus.SUCCESS,
                message=f"替换完成，共替换 {result.get('total_replacements', 0)} 处",
                data=result
            )
            
    except HTTPException:
        raise
    except Exception as e:
        security_logger.log_error(
            "Failed to replace in files",
            e,
            session_id=session_id,
            search_text=replace_request.original
        )
        
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                status=ResponseStatus.ERROR,
                error_code=ErrorCode.GENERAL_ERROR,
                message="替换失败",
                details={"error": str(e)},
                timestamp=performance_logger.get_current_time()
            ).model_dump()
        )


async def _search_text_file(
    session_id: str, 
    search_request: SearchRequest,
    session_info
) -> List[SearchResult]:
    """在TEXT文件中搜索"""
    results = []
    
    try:
        # 获取会话目录
        session_dir = Path(settings.session_dir) / session_id
        
        # 查找文本文件
        text_files = (
            list(session_dir.glob('*.txt')) + 
            list(session_dir.glob('*.text')) + 
            list(session_dir.glob('*.md')) +
            list(session_dir.glob('*.markdown'))
        )
        
        if not text_files:
            return results
        
        file_path = text_files[0]  # 使用第一个找到的文本文件
        
        # 读取文件内容
        file_content = await text_service.read_text_file(file_path)
        content = file_content.content
        
        # 构建搜索模式
        pattern = search_request.query
        flags = 0
        
        if not search_request.case_sensitive:
            flags |= re.IGNORECASE
        
        if search_request.use_regex:
            try:
                regex_pattern = re.compile(pattern, flags)
            except re.error as e:
                raise ValueError(f"正则表达式语法错误: {str(e)}")
        else:
            # 转义特殊字符
            pattern = re.escape(pattern)
            if search_request.whole_word:
                pattern = r'\b' + pattern + r'\b'
            regex_pattern = re.compile(pattern, flags)
        
        # 按行搜索
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            for match in regex_pattern.finditer(line):
                # 获取上下文
                context_before = line[:match.start()]
                context_after = line[match.end():]
                
                # 限制上下文长度
                if len(context_before) > 50:
                    context_before = '...' + context_before[-47:]
                if len(context_after) > 50:
                    context_after = context_after[:47] + '...'
                
                results.append(SearchResult(
                    file_path=file_path.name,
                    line_number=line_num,
                    column_start=match.start(),
                    column_end=match.end(),
                    matched_text=match.group(0),
                    context_before=context_before,
                    context_after=context_after
                ))
        
        return results
        
    except Exception as e:
        raise ValueError(f"搜索TEXT文件失败: {str(e)}")


async def _search_epub_files(
    session_id: str, 
    search_request: SearchRequest
) -> List[SearchResult]:
    """在EPUB文件中搜索"""
    # TODO: 实现EPUB文件搜索
    # 这里可以调用epub_service的相关方法
    return []


async def _replace_text_file(
    session_id: str, 
    replace_request: ReplaceRequest,
    session_info
) -> Dict[str, Any]:
    """在TEXT文件中替换"""
    try:
        # 获取会话目录
        session_dir = Path(settings.session_dir) / session_id
        
        # 查找文本文件
        text_files = (
            list(session_dir.glob('*.txt')) + 
            list(session_dir.glob('*.text')) + 
            list(session_dir.glob('*.md')) +
            list(session_dir.glob('*.markdown'))
        )
        
        if not text_files:
            return {"total_replacements": 0, "affected_files": []}
        
        file_path = text_files[0]  # 使用第一个找到的文本文件
        
        # 读取文件内容
        file_content = await text_service.read_text_file(file_path)
        content = file_content.content
        original_content = content
        
        # 构建替换模式
        pattern = replace_request.original
        replacement = replace_request.replacement
        flags = 0
        
        if not replace_request.case_sensitive:
            flags |= re.IGNORECASE
        
        if replace_request.use_regex:
            try:
                regex_pattern = re.compile(pattern, flags)
            except re.error as e:
                raise ValueError(f"正则表达式语法错误: {str(e)}")
        else:
            # 转义特殊字符
            pattern = re.escape(pattern)
            if replace_request.whole_word:
                pattern = r'\b' + pattern + r'\b'
            regex_pattern = re.compile(pattern, flags)
        
        # 执行替换
        new_content, count = regex_pattern.subn(replacement, content)
        
        # 如果有替换，保存文件
        if count > 0:
            await text_service.write_text_file(
                file_path, new_content, file_content.encoding
            )
        
        return {
            "total_replacements": count,
            "affected_files": [file_path.name] if count > 0 else [],
            "original_size": len(original_content),
            "new_size": len(new_content)
        }
        
    except Exception as e:
        raise ValueError(f"替换TEXT文件失败: {str(e)}")


async def _replace_epub_files(
    session_id: str, 
    replace_request: ReplaceRequest
) -> Dict[str, Any]:
    """在EPUB文件中替换"""
    # TODO: 实现EPUB文件替换
    # 这里可以调用epub_service的相关方法
    return {"total_replacements": 0, "affected_files": []}