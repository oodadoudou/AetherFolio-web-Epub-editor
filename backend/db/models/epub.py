"""EPUB模型"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class EpubVersion(str, Enum):
    """EPUB版本枚举"""
    EPUB2 = "2.0"
    EPUB3 = "3.0"
    EPUB31 = "3.1"
    EPUB32 = "3.2"


class EpubMetadata(BaseModel):
    """EPUB元数据模型"""
    
    title: str = Field(..., description="书名")
    author: str = Field(..., description="作者")
    language: str = Field(default="en", description="语言")
    identifier: Optional[str] = Field(None, description="标识符")
    publisher: Optional[str] = Field(None, description="出版社")
    publication_date: Optional[str] = Field(None, description="出版日期")
    isbn: Optional[str] = Field(None, description="ISBN")
    description: Optional[str] = Field(None, description="描述")
    subject: Optional[List[str]] = Field(None, description="主题")
    contributor: Optional[List[str]] = Field(None, description="贡献者")
    rights: Optional[str] = Field(None, description="版权信息")
    source: Optional[str] = Field(None, description="来源")
    relation: Optional[str] = Field(None, description="关联")
    coverage: Optional[str] = Field(None, description="覆盖范围")
    type: Optional[str] = Field(None, description="类型")
    format: Optional[str] = Field(None, description="格式")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "author": self.author,
            "language": self.language,
            "identifier": self.identifier,
            "publisher": self.publisher,
            "publication_date": self.publication_date,
            "isbn": self.isbn,
            "description": self.description,
            "subject": self.subject,
            "contributor": self.contributor,
            "rights": self.rights,
            "source": self.source,
            "relation": self.relation,
            "coverage": self.coverage,
            "type": self.type,
            "format": self.format
        }


class EpubSpineItem(BaseModel):
    """EPUB脊柱项模型"""
    
    id: str = Field(..., description="项目ID")
    href: str = Field(..., description="文件路径")
    media_type: str = Field(..., description="媒体类型")
    linear: bool = Field(default=True, description="是否线性")
    properties: Optional[List[str]] = Field(None, description="属性")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "href": self.href,
            "media_type": self.media_type,
            "linear": self.linear,
            "properties": self.properties
        }


class EpubManifestItem(BaseModel):
    """EPUB清单项模型"""
    
    id: str = Field(..., description="项目ID")
    href: str = Field(..., description="文件路径")
    media_type: str = Field(..., description="媒体类型")
    properties: Optional[List[str]] = Field(None, description="属性")
    fallback: Optional[str] = Field(None, description="回退项")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "href": self.href,
            "media_type": self.media_type,
            "properties": self.properties,
            "fallback": self.fallback
        }


class EpubNavPoint(BaseModel):
    """EPUB导航点模型"""
    
    id: str = Field(..., description="导航点ID")
    label: str = Field(..., description="标签")
    src: str = Field(..., description="源文件")
    play_order: Optional[int] = Field(None, description="播放顺序")
    children: Optional[List['EpubNavPoint']] = Field(None, description="子导航点")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "label": self.label,
            "src": self.src,
            "play_order": self.play_order,
            "children": [child.to_dict() for child in self.children] if self.children else None
        }


class EpubFile(BaseModel):
    """EPUB文件模型"""
    
    file_path: str = Field(..., description="文件路径")
    metadata: EpubMetadata = Field(..., description="元数据")
    version: EpubVersion = Field(default=EpubVersion.EPUB3, description="EPUB版本")
    file_size: int = Field(..., description="文件大小")
    extracted_path: Optional[str] = Field(None, description="解压路径")
    manifest_items: Optional[List[EpubManifestItem]] = Field(None, description="清单项")
    spine_items: Optional[List[EpubSpineItem]] = Field(None, description="脊柱项")
    nav_points: Optional[List[EpubNavPoint]] = Field(None, description="导航点")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    modified_at: datetime = Field(default_factory=datetime.now, description="修改时间")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "file_path": self.file_path,
            "metadata": self.metadata.to_dict(),
            "version": self.version.value,
            "file_size": self.file_size,
            "extracted_path": self.extracted_path,
            "manifest_items": [item.to_dict() for item in self.manifest_items] if self.manifest_items else None,
            "spine_items": [item.to_dict() for item in self.spine_items] if self.spine_items else None,
            "nav_points": [nav.to_dict() for nav in self.nav_points] if self.nav_points else None,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat()
        }
    
    def update_modified_time(self) -> None:
        """更新修改时间"""
        self.modified_at = datetime.now()
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EpubValidationResult(BaseModel):
    """EPUB验证结果模型"""
    
    is_valid: bool = Field(..., description="是否有效")
    errors: List[str] = Field(default_factory=list, description="错误列表")
    warnings: List[str] = Field(default_factory=list, description="警告列表")
    info: List[str] = Field(default_factory=list, description="信息列表")
    validation_time: datetime = Field(default_factory=datetime.now, description="验证时间")
    
    def add_error(self, error: str) -> None:
        """添加错误"""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str) -> None:
        """添加警告"""
        self.warnings.append(warning)
    
    def add_info(self, info: str) -> None:
        """添加信息"""
        self.info.append(info)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
            "validation_time": self.validation_time.isoformat()
        }
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EpubExportOptions(BaseModel):
    """EPUB导出选项模型"""
    
    include_images: bool = Field(default=True, description="是否包含图片")
    include_fonts: bool = Field(default=True, description="是否包含字体")
    include_css: bool = Field(default=True, description="是否包含CSS")
    compression_level: int = Field(default=6, ge=0, le=9, description="压缩级别")
    validate_before_export: bool = Field(default=True, description="导出前是否验证")
    optimize_images: bool = Field(default=False, description="是否优化图片")
    minify_css: bool = Field(default=False, description="是否压缩CSS")
    minify_html: bool = Field(default=False, description="是否压缩HTML")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "include_images": self.include_images,
            "include_fonts": self.include_fonts,
            "include_css": self.include_css,
            "compression_level": self.compression_level,
            "validate_before_export": self.validate_before_export,
            "optimize_images": self.optimize_images,
            "minify_css": self.minify_css,
            "minify_html": self.minify_html
        }


class EpubExportResult(BaseModel):
    """EPUB导出结果模型"""
    
    success: bool = Field(..., description="是否成功")
    output_path: Optional[str] = Field(None, description="输出路径")
    file_size: Optional[int] = Field(None, description="文件大小")
    export_time: datetime = Field(default_factory=datetime.now, description="导出时间")
    duration: Optional[float] = Field(None, description="导出耗时（秒）")
    errors: List[str] = Field(default_factory=list, description="错误列表")
    warnings: List[str] = Field(default_factory=list, description="警告列表")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "output_path": self.output_path,
            "file_size": self.file_size,
            "export_time": self.export_time.isoformat(),
            "duration": self.duration,
            "errors": self.errors,
            "warnings": self.warnings
        }
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }