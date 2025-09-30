"""文件上传API路由"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional
import os
import tempfile
import shutil
from pathlib import Path

from services.session_service import session_service
from services.epub_service import epub_service
from services.text_service import text_service
from core.config import settings
from core.logging import performance_logger
from db.models.schemas import UploadResponse, ErrorResponse, ApiResponse, ResponseStatus

router = APIRouter(prefix="/api/v1", tags=["upload"])


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user_id: Optional[str] = None
):
    """上传文件并创建会话"""
    try:
        # 验证文件名安全性
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        # 检查文件名是否包含危险字符或路径遍历
        import re
        # 只阻止真正危险的字符，允许Unicode字符（如韩文、日文等）
        dangerous_chars = r'[<>:"|?*\\]|\.\.'
        if re.search(dangerous_chars, file.filename) or any(ord(c) < 32 for c in file.filename):
            raise HTTPException(status_code=400, detail="文件名包含非法字符")
        
        # 检查可执行文件扩展名
        dangerous_exts = ['.exe', '.bat', '.cmd', '.com', '.scr', '.pif', '.vbs', '.js', '.jar', '.sh']
        if any(file.filename.lower().endswith(ext) for ext in dangerous_exts):
            raise HTTPException(status_code=400, detail="不允许上传可执行文件")
        
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in [".epub", ".txt"]:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件格式: {file_ext}。仅支持 .epub 和 .txt 文件"
            )
        
        # 先检查文件大小（在读取内容之前）
        file.file.seek(0, 2)  # 移动到文件末尾
        file_size = file.file.tell()
        file.file.seek(0)  # 重置到文件开头
        
        # 根据文件类型检查大小限制
        if file_ext == ".txt" and file_size > settings.max_text_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"TEXT文件大小超出限制。最大允许: {settings.max_text_file_size // (1024*1024)}MB"
            )
        elif file_ext == ".epub" and file_size > settings.max_epub_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"EPUB文件大小超出限制。最大允许: {settings.max_epub_file_size // (1024*1024)}MB"
            )
        
        # 验证文件内容类型（防止扩展名欺骗）
        content = await file.read()
        await file.seek(0)  # 重置文件指针
        
        # 检查文件魔数（文件头）来验证真实文件类型
        if file_ext == ".epub":
            # EPUB文件实际上是ZIP文件，检查ZIP文件头
            if not content.startswith(b'PK\x03\x04') and not content.startswith(b'PK\x05\x06') and not content.startswith(b'PK\x07\x08'):
                raise HTTPException(
                    status_code=422,
                    detail="无效的EPUB文件：文件不是有效的ZIP格式"
                )
            
            # 检查MIME类型
            if file.content_type and file.content_type not in ['application/epub+zip', 'application/zip', 'application/octet-stream']:
                raise HTTPException(
                    status_code=422,
                    detail=f"无效的EPUB文件：MIME类型不正确 ({file.content_type})"
                )
        
        if file_ext == ".txt":
            # 检查文本文件的MIME类型
            if file.content_type and not file.content_type.startswith('text/'):
                raise HTTPException(
                    status_code=422,
                    detail=f"无效的文本文件：MIME类型不正确 ({file.content_type})"
                )
            
            # 验证文本文件内容
            try:
                # 尝试解码为UTF-8文本
                text_content = content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    # 尝试其他常见编码
                    text_content = content.decode('gbk')
                except UnicodeDecodeError:
                    raise HTTPException(
                        status_code=422,
                        detail="无效的文本文件：文件内容不是有效的文本格式"
                    )
            
            # 检查是否包含二进制内容（简单启发式检查）
            null_bytes = content.count(b'\x00')
            if null_bytes > len(content) * 0.01:  # 如果空字节超过1%，可能是二进制文件
                raise HTTPException(
                    status_code=422,
                    detail="无效的文本文件：检测到二进制内容"
                )
            
            # 检查恶意脚本内容
            malicious_patterns = [
                r'<script[^>]*>.*?</script>',
                r'javascript:',
                r'vbscript:',
                r'onload\s*=',
                r'onerror\s*=',
                r'eval\s*\(',
                r'document\.cookie',
                r'window\.location',
                r'\bDROP\s+TABLE\b',
                r'\bUNION\s+SELECT\b',
                r'\bINSERT\s+INTO\b',
                r'\bDELETE\s+FROM\b',
                r'\bUPDATE\s+.*\bSET\b',
                r'\bEXEC\s*\(',
                r'\bEXECUTE\s*\(',
                r'\bxp_cmdshell\b'
            ]
            
            for pattern in malicious_patterns:
                if re.search(pattern, text_content, re.IGNORECASE | re.DOTALL):
                    raise HTTPException(
                        status_code=400,
                        detail="检测到潜在的恶意内容"
                    )
        
        # 对EPUB文件进行深度验证
        if file_ext == ".epub":
            from core.security import file_validator
            from core.exceptions import FileValidationError
            try:
                # 验证EPUB文件结构
                is_valid = file_validator.validate_epub_file(file)
                if not is_valid:
                    raise HTTPException(
                        status_code=422,
                        detail="无效的EPUB文件：文件结构不符合EPUB标准"
                    )
            except FileValidationError as e:
                raise HTTPException(
                    status_code=422,
                    detail=f"EPUB文件验证失败: {str(e)}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"EPUB文件处理错误: {str(e)}"
                )
        
        # 文件大小已在前面检查过了
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
            
        # 更新文件大小为实际内容大小
        file_size = len(content)
        
        try:
            # 根据文件类型处理
            if file_ext == ".epub":
                result = await epub_service.process_upload(
                    temp_file_path, 
                    file.filename,
                    user_id
                )
            else:  # .txt
                result = await text_service.process_upload(
                    temp_file_path,
                    file.filename, 
                    user_id
                )
            
            performance_logger.info(
                f"File uploaded successfully: {file.filename}",
                extra={
                    "session_id": result.session_id,
                    "file_size": file_size,
                    "file_type": file_ext
                }
            )
            
            # 返回标准API响应格式
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "文件上传成功",
                    "data": {
                        "session_id": result.session_id,
                        "file_tree": [node.dict() for node in result.file_tree],
                        "metadata": result.metadata.dict() if result.metadata else None,
                        "original_filename": result.original_filename,
                        "file_size": result.file_size,
                        "upload_time": result.upload_time.isoformat(),
                        "file_info": result.file_info.dict() if result.file_info else None
                    }
                }
            )
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except HTTPException as e:
        # 返回标准错误响应格式
        return JSONResponse(
            status_code=e.status_code,
            content={
                "status": "error",
                "message": str(e.detail),
                "data": None
            }
        )
    except Exception as e:
        performance_logger.error(f"Upload failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "文件上传失败",
                "data": None
            }
        )


@router.post("/reextract/{session_id}")
async def reextract_epub(
    session_id: str,
    file: UploadFile = File(...),
    user_id: str = "default_user"
):
    """重新解包现有会话的EPUB文件
    
    Args:
        session_id: 会话ID
        file: 上传的EPUB文件
        user_id: 用户ID
    
    Returns:
        JSONResponse: 重新解包结果
    """
    try:
        # 验证会话是否存在
        session_info = await session_service.get_session(session_id)
        if not session_info:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "会话不存在",
                    "data": None
                }
            )
        
        # 验证文件类型
        if not file.filename.lower().endswith('.epub'):
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "只支持EPUB文件",
                    "data": None
                }
            )
        
        # 读取文件内容
        content = await file.read()
        
        # 验证EPUB文件格式
        if not content.startswith(b'PK\x03\x04') and not content.startswith(b'PK\x05\x06') and not content.startswith(b'PK\x07\x08'):
            return JSONResponse(
                status_code=422,
                content={
                    "status": "error",
                    "message": "无效的EPUB文件：文件不是有效的ZIP格式",
                    "data": None
                }
            )
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.epub') as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # 重新解包EPUB文件
            success = await epub_service.reextract_epub_for_session(session_id, temp_file_path)
            
            if success:
                # 获取更新后的文件树
                file_tree = await epub_service.get_file_tree(session_id)
                
                performance_logger.info(
                    f"EPUB re-extracted successfully for session: {session_id}",
                    extra={
                        "session_id": session_id,
                        "file_name": file.filename,
                        "file_size": len(content)
                    }
                )
                
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "success",
                        "message": "EPUB文件重新解包成功",
                        "data": {
                            "session_id": session_id,
                            "file_tree": [node.dict() for node in file_tree],
                            "file_name": file.filename,
                            "file_size": len(content)
                        }
                    }
                )
            else:
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "message": "EPUB文件重新解包失败",
                        "data": None
                    }
                )
                
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        performance_logger.error(f"Re-extract failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"重新解包失败: {str(e)}",
                "data": None
            }
        )