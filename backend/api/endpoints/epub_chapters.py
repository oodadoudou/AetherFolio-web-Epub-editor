"""EPUB章节操作API路由"""

from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

from services.session_service import session_service
from core.logging import performance_logger

router = APIRouter(prefix="/api/v1/epub", tags=["epub-chapters"])

class ChapterContent(BaseModel):
    content: str

class ChapterInfo(BaseModel):
    id: str
    title: str
    file_path: str
    order: int

class ChapterListResponse(BaseModel):
    success: bool
    chapters: List[ChapterInfo]
    total: int

class ChapterContentResponse(BaseModel):
    success: bool
    content: Dict[str, Any]

class ChapterUpdateResponse(BaseModel):
    success: bool
    message: str
    error: Optional[str] = None

@router.get("/{session_id}/chapters", response_model=ChapterListResponse)
async def get_epub_chapters(session_id: str = Path(..., description="会话ID")):
    """获取EPUB章节列表"""
    try:
        # 获取会话信息
        session_info = await session_service.get_session_info(session_id)
        if not session_info:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 获取解压目录
        temp_dir = await session_service.get_session_data(session_id, "temp_dir")
        if not temp_dir or not os.path.exists(temp_dir):
            raise HTTPException(status_code=404, detail="EPUB文件未找到")
        
        # 解析章节信息
        chapters = await _parse_epub_chapters(temp_dir)
        
        performance_logger.info(
            f"Retrieved {len(chapters)} chapters for session {session_id}"
        )
        
        return ChapterListResponse(
            success=True,
            chapters=chapters,
            total=len(chapters)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        performance_logger.error(f"Failed to get chapters: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取章节列表失败: {str(e)}")

@router.get("/{session_id}/chapters/{chapter_id}", response_model=ChapterContentResponse)
async def get_chapter_content(
    session_id: str = Path(..., description="会话ID"),
    chapter_id: str = Path(..., description="章节ID")
):
    """获取章节内容"""
    try:
        # 获取会话信息
        session_info = await session_service.get_session_info(session_id)
        if not session_info:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 获取解压目录
        temp_dir = await session_service.get_session_data(session_id, "temp_dir")
        if not temp_dir or not os.path.exists(temp_dir):
            raise HTTPException(status_code=404, detail="EPUB文件未找到")
        
        # 获取章节内容
        content = await _get_chapter_content(temp_dir, chapter_id)
        
        performance_logger.info(
            f"Retrieved content for chapter {chapter_id} in session {session_id}"
        )
        
        return ChapterContentResponse(
            success=True,
            content={
                "text": content,
                "chapter_id": chapter_id
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        performance_logger.error(f"Failed to get chapter content: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取章节内容失败: {str(e)}")

@router.put("/{session_id}/chapters/{chapter_id}", response_model=ChapterUpdateResponse)
async def update_chapter_content(
    chapter_content: ChapterContent,
    session_id: str = Path(..., description="会话ID"),
    chapter_id: str = Path(..., description="章节ID")
):
    """修改章节内容"""
    try:
        # 获取会话信息
        session_info = await session_service.get_session_info(session_id)
        if not session_info:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 获取解压目录
        temp_dir = await session_service.get_session_data(session_id, "temp_dir")
        if not temp_dir or not os.path.exists(temp_dir):
            raise HTTPException(status_code=404, detail="EPUB文件未找到")
        
        # 更新章节内容
        success = await _update_chapter_content(temp_dir, chapter_id, chapter_content.content)
        
        if success:
            performance_logger.info(
                f"Updated content for chapter {chapter_id} in session {session_id}"
            )
            return ChapterUpdateResponse(
                success=True,
                message="章节内容更新成功"
            )
        else:
            return ChapterUpdateResponse(
                success=False,
                message="章节内容更新失败",
                error="章节文件未找到或无法写入"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        performance_logger.error(f"Failed to update chapter content: {str(e)}")
        return ChapterUpdateResponse(
            success=False,
            message="章节内容更新失败",
            error=str(e)
        )

async def _parse_epub_chapters(temp_dir: str) -> List[ChapterInfo]:
    """解析EPUB章节信息"""
    chapters = []
    
    try:
        # 查找OPF文件
        container_path = os.path.join(temp_dir, "META-INF", "container.xml")
        if not os.path.exists(container_path):
            return chapters
        
        # 解析container.xml
        tree = ET.parse(container_path)
        root = tree.getroot()
        
        # 查找OPF文件路径
        opf_path = None
        for rootfile in root.findall(".//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile"):
            if rootfile.get("media-type") == "application/oebps-package+xml":
                opf_path = rootfile.get("full-path")
                break
        
        if not opf_path:
            return chapters
        
        # 解析OPF文件
        opf_full_path = os.path.join(temp_dir, opf_path)
        if not os.path.exists(opf_full_path):
            return chapters
        
        opf_tree = ET.parse(opf_full_path)
        opf_root = opf_tree.getroot()
        
        # 获取manifest和spine
        manifest = {}
        for item in opf_root.findall(".//{http://www.idpf.org/2007/opf}item"):
            item_id = item.get("id")
            href = item.get("href")
            media_type = item.get("media-type")
            if item_id and href:
                manifest[item_id] = {
                    "href": href,
                    "media_type": media_type
                }
        
        # 获取spine中的章节顺序
        spine_items = []
        for itemref in opf_root.findall(".//{http://www.idpf.org/2007/opf}itemref"):
            idref = itemref.get("idref")
            if idref and idref in manifest:
                spine_items.append(idref)
        
        # 构建章节信息
        opf_dir = os.path.dirname(opf_full_path)
        for order, item_id in enumerate(spine_items):
            item_info = manifest[item_id]
            if item_info["media_type"] == "application/xhtml+xml":
                file_path = os.path.join(opf_dir, item_info["href"])
                
                # 尝试从文件中提取标题
                title = f"章节 {order + 1}"
                try:
                    if os.path.exists(file_path):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            soup = BeautifulSoup(content, 'html.parser')
                            h1_tag = soup.find('h1')
                            if h1_tag and h1_tag.get_text().strip():
                                title = h1_tag.get_text().strip()
                            else:
                                title_tag = soup.find('title')
                                if title_tag and title_tag.get_text().strip():
                                    title = title_tag.get_text().strip()
                except:
                    pass
                
                chapters.append(ChapterInfo(
                    id=item_id,
                    title=title,
                    file_path=item_info["href"],
                    order=order
                ))
        
    except Exception as e:
        performance_logger.error(f"Failed to parse EPUB chapters: {str(e)}")
    
    return chapters

async def _get_chapter_content(temp_dir: str, chapter_id: str) -> str:
    """获取章节内容"""
    try:
        # 查找OPF文件
        container_path = os.path.join(temp_dir, "META-INF", "container.xml")
        if not os.path.exists(container_path):
            raise ValueError("找不到container.xml文件")
        
        # 解析container.xml
        tree = ET.parse(container_path)
        root = tree.getroot()
        
        # 查找OPF文件路径
        opf_path = None
        for rootfile in root.findall(".//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile"):
            if rootfile.get("media-type") == "application/oebps-package+xml":
                opf_path = rootfile.get("full-path")
                break
        
        if not opf_path:
            raise ValueError("找不到OPF文件路径")
        
        # 解析OPF文件
        opf_full_path = os.path.join(temp_dir, opf_path)
        if not os.path.exists(opf_full_path):
            raise ValueError("找不到OPF文件")
        
        opf_tree = ET.parse(opf_full_path)
        opf_root = opf_tree.getroot()
        
        # 查找章节文件
        for item in opf_root.findall(".//{http://www.idpf.org/2007/opf}item"):
            if item.get("id") == chapter_id:
                href = item.get("href")
                if href:
                    chapter_file_path = os.path.join(os.path.dirname(opf_full_path), href)
                    if os.path.exists(chapter_file_path):
                        with open(chapter_file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # 提取文本内容
                            soup = BeautifulSoup(content, 'html.parser')
                            return soup.get_text()
        
        raise ValueError(f"找不到章节 {chapter_id}")
        
    except Exception as e:
        raise ValueError(f"获取章节内容失败: {str(e)}")

async def _update_chapter_content(temp_dir: str, chapter_id: str, new_content: str) -> bool:
    """更新章节内容"""
    try:
        # 查找OPF文件
        container_path = os.path.join(temp_dir, "META-INF", "container.xml")
        if not os.path.exists(container_path):
            return False
        
        # 解析container.xml
        tree = ET.parse(container_path)
        root = tree.getroot()
        
        # 查找OPF文件路径
        opf_path = None
        for rootfile in root.findall(".//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile"):
            if rootfile.get("media-type") == "application/oebps-package+xml":
                opf_path = rootfile.get("full-path")
                break
        
        if not opf_path:
            return False
        
        # 解析OPF文件
        opf_full_path = os.path.join(temp_dir, opf_path)
        if not os.path.exists(opf_full_path):
            return False
        
        opf_tree = ET.parse(opf_full_path)
        opf_root = opf_tree.getroot()
        
        # 查找章节文件
        for item in opf_root.findall(".//{http://www.idpf.org/2007/opf}item"):
            if item.get("id") == chapter_id:
                href = item.get("href")
                if href:
                    chapter_file_path = os.path.join(os.path.dirname(opf_full_path), href)
                    if os.path.exists(chapter_file_path):
                        # 读取原始文件
                        with open(chapter_file_path, 'r', encoding='utf-8') as f:
                            original_content = f.read()
                        
                        # 解析HTML并更新内容
                        soup = BeautifulSoup(original_content, 'html.parser')
                        
                        # 查找body标签或主要内容区域
                        body = soup.find('body')
                        if body:
                            # 清空body内容并添加新内容
                            body.clear()
                            # 创建新的段落，保持特殊字符
                            for paragraph in new_content.split('\n'):
                                if paragraph.strip():
                                    p_tag = soup.new_tag('p')
                                    # 使用append而不是string来避免HTML转义
                                    from bs4 import NavigableString
                                    p_tag.append(NavigableString(paragraph.strip()))
                                    body.append(p_tag)
                        else:
                            # 如果没有body标签，直接替换整个内容
                            soup.clear()
                            new_soup = BeautifulSoup('<html><body></body></html>', 'html.parser')
                            new_body = new_soup.find('body')
                            for paragraph in new_content.split('\n'):
                                if paragraph.strip():
                                    p_tag = new_soup.new_tag('p')
                                    from bs4 import NavigableString
                                    p_tag.append(NavigableString(paragraph.strip()))
                                    new_body.append(p_tag)
                            soup.append(new_soup)
                        
                        # 写回文件
                        with open(chapter_file_path, 'w', encoding='utf-8') as f:
                            f.write(str(soup))
                        
                        return True
        
        return False
        
    except Exception as e:
        performance_logger.error(f"Failed to update chapter content: {str(e)}")
        return False