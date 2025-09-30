"""文件操作API路由"""

import mimetypes
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, Response
from typing import Optional

from services.file_service import file_service
from services.session_service import session_service
from core.logging import performance_logger
from db.models.schemas import FileContentResponse, FileTreeResponse

router = APIRouter(prefix="/api/v1", tags=["files"])


@router.get("/file-tree/{session_id}", response_model=FileTreeResponse)
async def get_file_tree(session_id: str):
    """获取文件树结构"""
    try:
        result = await file_service.get_file_tree(session_id)
        
        performance_logger.info(
            f"File tree retrieved",
            extra={"session_id": session_id}
        )
        
        return result
        
    except HTTPException:
        # 让 HTTPException 直接传递，保持原有的状态码
        raise
    except Exception as e:
        performance_logger.error(f"Get file tree failed: {str(e)}")
        raise HTTPException(status_code=500, detail="获取文件树失败")


@router.get("/files/content", response_model=FileContentResponse)
async def get_file_content(
    session_id: str = Query(...),
    file_path: str = Query(...)
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
                "file_path": file_path
            }
        )
        
        # 转换为FileContentResponse格式
        return FileContentResponse(
            success=True,
            content=result.content,
            encoding=result.encoding,
            mime_type=result.mime_type,
            size=result.size,
            last_modified=result.last_modified,
            is_binary=result.is_binary
        )
        
    except HTTPException:
        # 让 HTTPException 直接传递，保持原有的状态码
        raise
    except Exception as e:
        performance_logger.error(f"Get file content failed: {str(e)}")
        raise HTTPException(status_code=500, detail="获取文件内容失败")


@router.get("/files/binary")
async def get_binary_file(
    session_id: str = Query(...),
    file_path: str = Query(...)
):
    """获取二进制文件内容（图片、字体等）"""
    try:
        # 获取会话信息
        session = await session_service.get_session(session_id)
        if not session:
            performance_logger.error(f"Session not found: {session_id}")
            raise HTTPException(status_code=404, detail="会话不存在")
        
        performance_logger.info(f"Binary file request - session_id: {session_id}, file_path: {file_path}, session: {session}")
        
        # 构建完整文件路径
        if session.get('extracted_path'):
            # EPUB文件
            base_dir = Path(session['extracted_path'])
            if (base_dir / 'epub').exists():
                base_dir = base_dir / 'epub'
            performance_logger.info(f"Using EPUB base directory: {base_dir}")
        else:
            # 文本文件
            base_dir = Path("backend/sessions") / session_id
            performance_logger.info(f"Using text file base directory: {base_dir}")
        
        # 安全处理文件路径，防止路径遍历攻击
        clean_path = file_path
        original_path = clean_path
        
        # 处理各种相对路径格式
        while clean_path.startswith('../'):
            clean_path = clean_path[3:]  # 移除 '../'
        
        if clean_path.startswith('./'):
            clean_path = clean_path[2:]  # 移除 './'
        
        if clean_path.startswith('/'):
            clean_path = clean_path[1:]  # 移除开头的 '/'
        
        performance_logger.info(f"Path processing - original: {original_path}, cleaned: {clean_path}")
        
        # 确保路径不包含危险字符（但允许正常的相对路径）
        if '..' in clean_path.replace('../', '').replace('./', '') or clean_path.startswith('/'):
            performance_logger.warning(f"Invalid file path detected: {clean_path}")
            raise HTTPException(status_code=400, detail="无效的文件路径")
        
        # 尝试多种路径组合
        possible_paths = [
            base_dir / clean_path,
            base_dir / Path(clean_path).name,  # 只使用文件名
        ]
        
        # 如果原始路径包含相对路径，也尝试直接使用
        if '../' in original_path or './' in original_path:
            try:
                # 尝试相对于base_dir解析路径
                relative_path = Path(original_path)
                if not relative_path.is_absolute():
                    possible_paths.append(base_dir / relative_path)
            except Exception as e:
                performance_logger.warning(f"Failed to process relative path {original_path}: {e}")
        
        found_file = None
        
        # 首先尝试直接路径匹配
        for path_candidate in possible_paths:
            try:
                resolved_path = path_candidate.resolve()
                base_resolved = base_dir.resolve()
                
                # 安全检查：确保文件在基础目录内
                if str(resolved_path).startswith(str(base_resolved)) and resolved_path.exists() and resolved_path.is_file():
                    found_file = resolved_path
                    performance_logger.info(f"Direct path match found: {resolved_path}")
                    break
            except Exception as e:
                performance_logger.debug(f"Path resolution failed for {path_candidate}: {e}")
                continue
        
        # 如果直接路径不存在，尝试递归查找文件
        if not found_file:
            filename = Path(clean_path).name
            performance_logger.info(f"Starting recursive search for filename: {filename} in {base_dir}")
            
            # 在base_dir中递归查找同名文件
            try:
                for file_candidate in base_dir.rglob(filename):
                    if file_candidate.is_file():
                        # 确保找到的文件仍在安全目录内
                        try:
                            resolved_candidate = file_candidate.resolve()
                            base_resolved = base_dir.resolve()
                            if str(resolved_candidate).startswith(str(base_resolved)):
                                found_file = resolved_candidate
                                performance_logger.info(f"Recursive search found: {resolved_candidate}")
                                break
                        except Exception as e:
                            performance_logger.debug(f"File candidate resolution failed: {e}")
                            continue
            except Exception as e:
                performance_logger.error(f"Recursive search failed: {e}")
        
        if not found_file:
            # 列出base_dir的内容以便调试
            try:
                dir_contents = list(base_dir.rglob('*'))[:20]  # 限制输出数量
                performance_logger.warning(f"File not found. Base dir contents (first 20): {[str(p) for p in dir_contents]}")
            except Exception:
                performance_logger.warning(f"File not found and failed to list directory contents")
            
            performance_logger.error(f"Binary file not found - session_id: {session_id}, original_path: {original_path}, cleaned_path: {clean_path}, base_dir: {base_dir}")
            raise HTTPException(status_code=404, detail=f"文件不存在: {file_path}")
        
        full_path = found_file
        
        # 读取二进制文件
        try:
            with open(full_path, 'rb') as f:
                content = f.read()
        except Exception as e:
            performance_logger.error(f"Failed to read binary file {full_path}: {e}")
            raise HTTPException(status_code=500, detail="文件读取失败")
        
        # 获取MIME类型
        mime_type, _ = mimetypes.guess_type(str(full_path))
        if not mime_type:
            # 根据扩展名推断
            extension = full_path.suffix.lower()
            extension_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.svg': 'image/svg+xml',
                '.webp': 'image/webp',
                '.bmp': 'image/bmp',
                '.ico': 'image/x-icon',
                '.tiff': 'image/tiff',
                '.tif': 'image/tiff',
                '.woff': 'font/woff',
                '.woff2': 'font/woff2',
                '.ttf': 'font/ttf',
                '.otf': 'font/otf',
                '.eot': 'application/vnd.ms-fontobject'
            }
            mime_type = extension_map.get(extension, 'application/octet-stream')
        
        performance_logger.info(
            f"Binary file served successfully",
            extra={
                "session_id": session_id,
                "original_path": file_path,
                "resolved_path": str(full_path),
                "mime_type": mime_type,
                "size": len(content)
            }
        )
        
        return Response(
            content=content,
            media_type=mime_type,
            headers={
                "Cache-Control": "public, max-age=3600",
                "Content-Length": str(len(content)),
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        performance_logger.error(f"Get binary file failed - session_id: {session_id}, file_path: {file_path}, error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取二进制文件失败: {str(e)}")