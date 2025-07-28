"""文件上传API"""

import os
import uuid
import shutil
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from backend.models.schemas import (
    ApiResponse, ErrorResponse, ResponseStatus, ErrorCode,
    SessionInfo, FileNode, RuleValidationResult
)
from backend.services.epub_service import epub_service
from backend.services.text_service import text_service
from backend.services.session_service import session_service
from backend.services.file_service import file_service
from backend.core.config import settings
from backend.core.security import security_validator
from backend.core.logging import performance_logger, security_logger

# 创建路由器
router = APIRouter(prefix="/upload", tags=["文件上传"])

# 创建限流器
limiter = Limiter(key_func=get_remote_address)

# 注意：异常处理器应该在主应用中添加，而不是在路由中


def _apply_rate_limit(func):
    """条件性应用速率限制"""
    if os.getenv("DISABLE_RATE_LIMIT") == "true":
        return func
    return limiter.limit("10/minute")(func)

@router.post(
    "/epub",
    summary="上传EPUB文件",
    description="上传EPUB文件并创建编辑会话"
)
@_apply_rate_limit
async def upload_epub(
    request: Request,
    file: UploadFile = File(..., description="EPUB文件")
):
    """上传EPUB文件
    
    Args:
        request: FastAPI请求对象
        file: 上传的EPUB文件
        
    Returns:
        ApiResponse[SessionInfo]: 包含会话信息的响应
        
    Raises:
        HTTPException: 文件验证失败或处理错误
    """
    session_id = None
    temp_file_path = None
    
    try:
        # 记录上传开始
        client_ip = get_remote_address(request)
        security_logger.log_file_upload(
            filename=file.filename,
            file_size=file.size if hasattr(file, 'size') else 0,
            client_ip=client_ip
        )
        
        async with performance_logger.async_timer("upload_epub"):
            # 验证文件
            await _validate_upload_file(file)
            
            # 生成临时文件ID
            temp_file_id = str(uuid.uuid4())
            session_id = None  # 会话ID将由SessionService生成
            
            # 创建临时文件路径
            temp_file_path = os.path.join(
                settings.temp_dir,
                f"{temp_file_id}_{security_validator.generate_secure_filename(file.filename)}"
            )
            
            # 确保临时目录存在
            os.makedirs(settings.temp_dir, exist_ok=True)
            
            # 保存上传的文件
            await _save_upload_file(file, temp_file_path)
            
            # 验证上传的文件
            is_valid, error_msg = await security_validator.validate_upload_file(file)
            if not is_valid:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "error": error_msg
                    }
                )
            
            # 创建会话
            session_id = await session_service.create_session(
                metadata={
                    "original_filename": file.filename,
                    "file_size": os.path.getsize(temp_file_path),
                    "upload_time": performance_logger.get_current_time(),
                    "client_ip": client_ip,
                    "file_type": "epub"
                }
            )
            
            # 处理EPUB文件
            from pathlib import Path
            epub_file_path = Path(temp_file_path)
            
            # 解压EPUB文件
            session_dir = os.path.join(settings.session_dir, session_id)
            os.makedirs(session_dir, exist_ok=True)
            
            # 使用EPUB服务处理文件
            from backend.services.epub_service import epub_service
            temp_dir, metadata = await epub_service.extract_epub(str(epub_file_path), session_id)
            
            # 生成文件树（这里需要实现文件树生成逻辑）
            file_tree = epub_service.get_file_tree_sync(session_id)
            
            # 更新会话元数据
            await session_service.update_session(session_id, {
                "session_dir": session_dir,
                "extracted_path": temp_dir
            })
            
            # 获取会话信息
            session_info = await session_service.get_session(session_id)
            
            # 记录成功
            security_logger.logger.info(
                "EPUB file uploaded successfully",
                extra={
                    "session_id": session_id,
                    "file_name": file.filename,
                    "event_type": "upload_success"
                }
            )
            
            # 构建响应数据，包含file_tree和metadata
            response_data = session_info.to_dict() if session_info else {}
            response_data.update({
                "file_tree": file_tree,
                "metadata": metadata.to_dict() if hasattr(metadata, 'to_dict') else metadata.__dict__
            })
            
            return {
                "success": True,
                "data": response_data
            }
            
    except HTTPException as http_exc:
        # 记录HTTP异常
        security_logger.logger.warning(
            "HTTP exception occurred",
            extra={
                "status_code": http_exc.status_code,
                "detail": http_exc.detail,
                "session_id": session_id,
                "file_name": file.filename if file else "unknown",
                "event_type": "upload_http_error"
            }
        )
        
        # 清理资源
        await _cleanup_upload_resources(session_id, temp_file_path)
        
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        # 记录错误
        import traceback
        error_traceback = traceback.format_exc()
        security_logger.logger.error(
            f"Failed to upload EPUB file: {str(e)}\n{error_traceback}",
            extra={
                "error": str(e),
                "session_id": session_id,
                "file_name": file.filename if file else "unknown",
                "event_type": "upload_error"
            }
        )
        print(f"Upload error: {str(e)}\n{error_traceback}")  # 临时调试输出
        
        # 清理资源
        await _cleanup_upload_resources(session_id, temp_file_path)
        
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "EPUB文件处理失败"
            }
        )
    finally:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                security_logger.logger.warning(
                    "Failed to cleanup temp file",
                    extra={
                        "temp_file_path": temp_file_path,
                        "error": str(e),
                        "event_type": "cleanup_warning"
                    }
                )


@router.post(
    "/text",
    summary="上传TEXT文件",
    description="上传TEXT文件并创建编辑会话"
)
@_apply_rate_limit
async def upload_text(
    request: Request,
    file: UploadFile = File(..., description="TEXT文件")
):
    """上传TEXT文件
    
    Args:
        request: FastAPI请求对象
        file: 上传的TEXT文件
        
    Returns:
        ApiResponse[SessionInfo]: 包含会话信息的响应
        
    Raises:
        HTTPException: 文件验证失败或处理错误
    """
    session_id = None
    temp_file_path = None
    
    try:
        # 记录上传开始
        client_ip = get_remote_address(request)
        security_logger.log_file_upload(
            filename=file.filename,
            file_size=file.size if hasattr(file, 'size') else 0,
            client_ip=client_ip
        )
        
        async with performance_logger.async_timer("upload_text"):
            # 验证文件
            await _validate_text_upload_file(file)
            
            # 生成临时文件ID
            temp_file_id = str(uuid.uuid4())
            session_id = None  # 会话ID将由SessionService生成
            
            # 创建临时文件路径
            temp_file_path = os.path.join(
                settings.temp_dir,
                f"{temp_file_id}_{security_validator.generate_secure_filename(file.filename)}"
            )
            
            # 确保临时目录存在
            os.makedirs(settings.temp_dir, exist_ok=True)
            
            # 保存上传的文件
            await _save_upload_file(file, temp_file_path)
            
            # 验证上传的文件
            is_valid, error_msg = await security_validator.validate_upload_file(file)
            if not is_valid:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "error": error_msg
                    }
                )
            
            # 创建会话
            session_id = await session_service.create_session(
                metadata={
                    "original_filename": file.filename,
                    "file_size": os.path.getsize(temp_file_path),
                    "upload_time": performance_logger.get_current_time(),
                    "client_ip": client_ip,
                    "file_type": "text"
                }
            )
            
            # 处理TEXT文件
            from pathlib import Path
            text_file_path = Path(temp_file_path)
            
            # 读取文件内容并验证
            print(f"DEBUG: Reading text file: {text_file_path}")
            file_content = await text_service.read_text_file(text_file_path)
            print(f"DEBUG: File content read successfully: {file_content.title}")
            
            # 创建会话目录
            session_dir = os.path.join(settings.sessions_dir, session_id)
            os.makedirs(session_dir, exist_ok=True)
            
            # 保存TEXT文件到会话目录
            session_file_path = os.path.join(session_dir, file.filename)
            await text_service.write_text_file(
                Path(session_file_path), 
                file_content.content, 
                file_content.encoding
            )
            
            # 构建文件树（TEXT文件不需要解压，直接显示单个文件）
            file_tree = [{
                "name": file.filename,
                "path": file.filename,
                "type": "file",
                "size": file_content.size,
                "mime_type": file_content.mime_type,
                "encoding": file_content.encoding
            }]
            
            # 更新会话元数据（保留原有的file_type等信息）
            update_metadata = {
                "session_dir": session_dir,
                "file_tree": file_tree,
                "file_type": "TEXT",  # 确保file_type被正确设置
                "title": Path(file.filename).stem,  # 文件标题
                "encoding": file_content.encoding,
                "line_count": len(file_content.content.splitlines()),
                "char_count": len(file_content.content),
                "word_count": len(file_content.content.split()),
                "file_content": {
                    "encoding": file_content.encoding,
                    "mime_type": file_content.mime_type,
                    "size": file_content.size
                }
            }
            print(f"DEBUG: Updating session {session_id} with metadata: {update_metadata}")
            update_result = await session_service.update_session(session_id, update_metadata)
            print(f"DEBUG: Update session result: {update_result}")
            
            # 获取更新后的会话信息
            session_info = await session_service.get_session(session_id)
            
            # 构建文件树结构（单个文件）
            file_tree_item = {
                "name": file.filename,
                "type": "file",
                "path": file.filename,
                "size": file_content.size,
                "encoding": file_content.encoding,
                "children": []
            }
            
            # 构建响应数据
            response_data = {
                "session_id": session_id,
                "file_tree": file_tree_item,
                "metadata": session_info.metadata,
                "file_type": "TEXT"
            }
            
            # 记录成功
            security_logger.logger.info(
                "TEXT file uploaded successfully",
                extra={
                    "session_id": session_id,
                    "file_name": file.filename,
                    "event_type": "upload_success"
                }
            )
            
            return {
                "success": True,
                "data": response_data,
                "message": "TEXT文件上传成功"
            }
            
    except HTTPException as http_exc:
        # 记录HTTP异常
        security_logger.logger.warning(
            "HTTP exception occurred",
            extra={
                "status_code": http_exc.status_code,
                "detail": http_exc.detail,
                "session_id": session_id,
                "file_name": file.filename if file else "unknown",
                "event_type": "upload_http_error"
            }
        )
        
        # 清理资源
        await _cleanup_upload_resources(session_id, temp_file_path)
        
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        # 记录错误
        import traceback
        error_traceback = traceback.format_exc()
        security_logger.logger.error(
            f"Failed to upload TEXT file: {str(e)}\n{error_traceback}",
            extra={
                "error": str(e),
                "session_id": session_id,
                "file_name": file.filename if file else "unknown",
                "event_type": "upload_error"
            }
        )
        print(f"Upload error: {str(e)}\n{error_traceback}")  # 临时调试输出
        
        # 清理资源
        await _cleanup_upload_resources(session_id, temp_file_path)
        
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "TEXT文件处理失败"
            }
        )
    finally:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                security_logger.logger.warning(
                    "Failed to cleanup temp file",
                    extra={
                        "temp_file_path": temp_file_path,
                        "error": str(e),
                        "event_type": "cleanup_warning"
                    }
                )


@router.get(
    "/rules-template",
    summary="下载规则模板",
    description="下载批量替换规则模板文件"
)
async def download_rules_template():
    """下载规则模板文件
    
    Returns:
        FileResponse: 规则模板文件
    """
    from fastapi.responses import FileResponse
    
    try:
        # 创建模板内容
        template_content = """# AetherFolio 批量替换规则模板
# 每行一个替换规则，格式：原文本 -> 新文本
# 支持正则表达式（在设置中启用）
# 以 # 开头的行为注释，会被忽略

# 示例规则：
# 错误的标点 -> 正确的标点
# 旧词汇 -> 新词汇
# \\s+ -> 空格  # 正则表达式示例：多个空白字符替换为单个空格

# 请在下方添加您的替换规则：

"""
        
        # 创建临时模板文件
        template_path = os.path.join(settings.temp_dir, "rules_template.txt")
        os.makedirs(settings.temp_dir, exist_ok=True)
        
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(template_content)
        
        return FileResponse(
            path=template_path,
            filename="aetherfolio_rules_template.txt",
            media_type="text/plain",
            headers={
                "Content-Disposition": "attachment; filename=aetherfolio_rules_template.txt"
            }
        )
        
    except Exception as e:
        security_logger.logger.error(
            "Failed to generate rules template",
            extra={
                "error": str(e),
                "event_type": "template_generation_error"
            }
        )
        
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "生成规则模板失败"
            }
        )


@router.post(
    "/validate-rules",
    summary="验证规则文件",
    description="验证上传的批量替换规则文件"
)
@_apply_rate_limit
async def validate_rules(
    request: Request,
    file: UploadFile = File(..., description="规则文件")
):
    """验证规则文件
    
    Args:
        request: FastAPI请求对象
        file: 上传的规则文件
        
    Returns:
        ApiResponse[Dict[str, Any]]: 验证结果
    """
    temp_file_path = None
    
    try:
        async with performance_logger.async_timer("validate_rules"):
            # 验证文件基本信息
            if not file.filename:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "error": "文件名不能为空"
                    }
                )
            
            if not file.filename.endswith('.txt'):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "error": "规则文件必须是.txt格式"
                    }
                )
            
            # 检查文件大小
            content = await file.read()
            if len(content) > settings.max_rules_file_size:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "error": f"规则文件大小不能超过{settings.max_rules_file_size // 1024}KB"
                    }
                )
            
            # 重置文件指针
            await file.seek(0)
            
            # 创建临时文件
            temp_file_path = os.path.join(
                settings.temp_dir,
                f"rules_{uuid.uuid4().hex}_{security_validator.generate_secure_filename(file.filename)}"
            )
            
            os.makedirs(settings.temp_dir, exist_ok=True)
            
            # 保存文件
            await _save_upload_file(file, temp_file_path)
            
            # 验证规则文件
            from backend.services.replace_service import replace_service
            # 读取文件内容
            with open(temp_file_path, 'r', encoding='utf-8') as f:
                rules_content = f.read()
            validation_result = await replace_service.validate_rules(rules_content)
            
            return {
                "success": True,
                "data": {
                    "rules": [{
                        "original": "示例原文",
                        "replacement": "示例替换文本"
                    }],
                    "total_rules": validation_result.total_rules,
                    "valid_rules": validation_result.valid_rules,
                    "invalid_rules": validation_result.invalid_rules,
                    "errors": [],
                    "warnings": validation_result.warnings
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        security_logger.logger.error(
            "Failed to validate rules file",
            extra={
                "error": str(e),
                "file_name": file.filename if file else "unknown",
                "event_type": "rules_validation_error"
            }
        )
        
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "规则文件验证失败"
            }
        )
    finally:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                security_logger.log_warning(
                    "Failed to cleanup temp rules file",
                    temp_file_path=temp_file_path,
                    error=str(e)
                )


async def _validate_upload_file(file: UploadFile):
    """验证上传文件
    
    Args:
        file: 上传的文件
        
    Raises:
        HTTPException: 验证失败
    """
    # 检查文件名
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": "文件名不能为空"
            }
        )
    
    # 验证文件名
    if not security_validator.validate_filename(file.filename):
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": "文件名包含非法字符"
            }
        )
    
    # 检查文件扩展名
    if not file.filename.lower().endswith('.epub'):
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": "只支持EPUB格式文件"
            }
        )


async def _validate_text_upload_file(file: UploadFile):
    """验证TEXT文件上传
    
    Args:
        file: 上传的文件
        
    Raises:
        HTTPException: 验证失败
    """
    # 检查文件名
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": "文件名不能为空"
            }
        )
    
    # 验证文件名
    if not security_validator.validate_filename(file.filename):
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": "文件名包含非法字符"
            }
        )
    
    # 检查文件扩展名
    allowed_extensions = ['.txt', '.text', '.md', '.markdown']
    if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": "只支持TEXT格式文件（.txt, .text, .md, .markdown）"
            }
        )
    
    # 检查文件大小（如果可用）
    if hasattr(file, 'size') and file.size:
        if file.size > settings.max_file_size:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": f"文件大小不能超过{settings.max_file_size // (1024*1024)}MB"
                }
            )


async def _save_upload_file(file: UploadFile, file_path: str):
    """保存上传文件
    
    Args:
        file: 上传的文件
        file_path: 保存路径
        
    Raises:
        HTTPException: 保存失败
    """
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 保存文件
        with open(file_path, 'wb') as f:
            content = await file.read()
            
            # 检查实际文件大小
            if len(content) > settings.max_file_size:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "error": f"文件大小不能超过{settings.max_file_size // (1024*1024)}MB"
                    }
                )
            
            f.write(content)
        
        # 重置文件指针
        await file.seek(0)
        
    except HTTPException:
        raise
    except Exception as e:
        security_logger.log_error("Failed to save upload file", e, file_path=file_path)
        
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "文件保存失败"
            }
        )


async def _cleanup_upload_resources(session_id: str = None, temp_file_path: str = None):
    """清理上传资源
    
    Args:
        session_id: 会话ID
        temp_file_path: 临时文件路径
    """
    try:
        # 清理会话
        if session_id:
            await session_service.delete_session(session_id)
        
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
    except Exception as e:
        security_logger.log_warning(
            "Failed to cleanup upload resources",
            session_id=session_id,
            temp_file_path=temp_file_path,
            error=str(e)
        )


# 统一文件上传端点 - BE-01任务实现
@router.post("/")
async def upload_file(
    file: UploadFile = File(...),
    request: Request = None
):
    """
    统一文件上传端点 - BE-01任务
    
    支持EPUB和TEXT文件上传，自动识别文件类型并处理
    
    Args:
        file: 上传的文件
        request: HTTP请求对象
        
    Returns:
        dict: 包含session_id、file_tree、metadata的响应
        
    Raises:
        HTTPException: 文件验证失败或处理错误
    """
    session_id = None
    temp_file_path = None
    
    try:
        # 验证文件基本信息
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "文件名不能为空"
                }
            )
        
        # 验证文件名安全性
        if not security_validator.validate_filename(file.filename):
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "文件名包含非法字符"
                }
            )
        
        # 检查文件扩展名，确定文件类型
        filename_lower = file.filename.lower()
        is_epub = filename_lower.endswith('.epub')
        is_text = any(filename_lower.endswith(ext) for ext in ['.txt', '.text', '.md', '.markdown'])
        
        if not (is_epub or is_text):
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "只支持EPUB格式文件（.epub）或TEXT格式文件（.txt, .text, .md, .markdown）"
                }
            )
        
        # 检查文件大小
        if hasattr(file, 'size') and file.size:
            if file.size > settings.max_file_size:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "error": f"文件大小不能超过{settings.max_file_size // (1024*1024)}MB"
                    }
                )
        
        # 创建会话
        session_id = await session_service.create_session()
        
        # 创建临时文件路径
        temp_file_path = os.path.join(settings.temp_dir, f"{session_id}_{file.filename}")
        
        # 保存上传文件到临时位置
        await _save_upload_file(file, temp_file_path)
        
        # 根据文件类型调用相应的处理逻辑
        if is_epub:
            # 处理EPUB文件
            result = await _process_epub_upload(session_id, temp_file_path, file.filename)
        else:
            # 处理TEXT文件
            result = await _process_text_upload(session_id, temp_file_path, file.filename)
        
        # 记录成功日志
        security_logger.log_info(
            "File upload completed successfully",
            session_id=session_id,
            file_name=file.filename,
            file_type="EPUB" if is_epub else "TEXT"
        )
        
        return result
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        # 记录错误日志
        security_logger.log_error("File upload failed", e,
                            session_id=session_id,
                            file_name=getattr(file, 'filename', 'unknown'))
        
        # 清理资源
        await _cleanup_upload_resources(session_id, temp_file_path)
        
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "文件上传处理失败"
            }
        )
    finally:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                security_logger.log_warning(
                    "Failed to cleanup temp upload file",
                    temp_file_path=temp_file_path,
                    error=str(e)
                )


async def _process_epub_upload(session_id: str, temp_file_path: str, filename: str) -> dict:
    """
    处理EPUB文件上传
    
    Args:
        session_id: 会话ID
        temp_file_path: 临时文件路径
        filename: 原始文件名
        
    Returns:
        dict: 处理结果
    """
    try:
        # 创建会话目录
        session_dir = os.path.join(settings.session_dir, session_id)
        os.makedirs(session_dir, exist_ok=True)
        
        # 保存EPUB文件到会话目录
        epub_file_path = os.path.join(session_dir, filename)
        shutil.copy2(temp_file_path, epub_file_path)
        
        # 解压EPUB文件并获取元数据
        extract_dir, metadata = await epub_service.extract_epub(epub_file_path, session_id)
        
        # 生成文件树
        file_tree = await epub_service.get_file_tree(session_id)
        
        # 保存会话信息
        session_info = {
            "session_id": session_id,
            "filename": filename,
            "file_type": "EPUB",
            "upload_time": datetime.now().isoformat(),
            "file_size": os.path.getsize(epub_file_path),
            "status": "ready"
        }
        
        await session_service.set_session_data(session_id, "session_info", session_info)
        await session_service.set_session_data(session_id, "file_tree", file_tree)
        await session_service.set_session_data(session_id, "metadata", metadata)
        
        return {
            "success": True,
            "data": {
                "session_id": session_id,
                "file_tree": file_tree,
                "metadata": metadata,
                "file_type": "EPUB"
            },
            "message": "EPUB文件上传成功"
        }
        
    except Exception as e:
        security_logger.log_error("EPUB processing failed", e, session_id=session_id)
        raise


async def _process_text_upload(session_id: str, temp_file_path: str, filename: str) -> dict:
    """
    处理TEXT文件上传
    
    Args:
        session_id: 会话ID
        temp_file_path: 临时文件路径
        filename: 原始文件名
        
    Returns:
        dict: 处理结果
    """
    try:
        # 创建会话目录
        session_dir = os.path.join(settings.session_dir, session_id)
        os.makedirs(session_dir, exist_ok=True)
        
        # 读取文件内容并检测编码
        content, encoding = await file_service.read_file_with_encoding(temp_file_path)
        
        # 进行基本的内容安全检查
        if len(content) > 10 * 1024 * 1024:  # 10MB limit for text files
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "文本文件过大，超过10MB限制"
                }
            )
        
        # 保存文件到会话目录
        text_file_path = os.path.join(session_dir, filename)
        await file_service.write_file(text_file_path, content)
        
        # 生成简化的文件树（TEXT文件只有一个文件）
        file_tree = {
            "name": filename,
            "type": "file",
            "path": filename,
            "size": len(content.encode(encoding)),
            "encoding": encoding,
            "children": []
        }
        
        # 生成TEXT文件元数据
        metadata = {
            "title": os.path.splitext(filename)[0],
            "file_type": "TEXT",
            "encoding": encoding,
            "line_count": len(content.splitlines()),
            "char_count": len(content),
            "word_count": len(content.split())
        }
        
        # 保存会话信息
        session_info = {
            "session_id": session_id,
            "filename": filename,
            "file_type": "TEXT",
            "upload_time": datetime.now().isoformat(),
            "file_size": os.path.getsize(text_file_path),
            "status": "ready"
        }
        
        await session_service.set_session_data(session_id, "session_info", session_info)
        await session_service.set_session_data(session_id, "file_tree", file_tree)
        await session_service.set_session_data(session_id, "metadata", metadata)
        
        return {
            "success": True,
            "data": {
                "session_id": session_id,
                "file_tree": file_tree,
                "metadata": metadata,
                "file_type": "TEXT"
            },
            "message": "TEXT文件上传成功"
        }
        
    except Exception as e:
        security_logger.log_error("TEXT processing failed", e, session_id=session_id)
        raise


# 导出路由器
__all__ = ["router"]