from pydantic import BaseModel, Field, validator
from typing import List, Optional, Union, Dict, Any, Generic, TypeVar
from datetime import datetime
from enum import Enum
from fastapi import UploadFile

T = TypeVar('T')


class FileType(str, Enum):
    """文件类型枚举"""
    FILE = "file"
    DIRECTORY = "directory"
    HTML = "html"
    TEXT = "text"
    XML = "xml"
    CSS = "css"
    JAVASCRIPT = "javascript"
    IMAGE = "image"
    FONT = "font"


class MimeType(str, Enum):
    """MIME类型枚举"""
    HTML = "text/html"
    XHTML = "application/xhtml+xml"
    CSS = "text/css"
    XML = "application/xml"
    IMAGE = "image/*"
    FONT = "font/*"
    JAVASCRIPT = "application/javascript"
    TEXT = "text/plain"


class ResponseStatus(str, Enum):
    """响应状态枚举"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


class ErrorCode(str, Enum):
    """错误码枚举"""
    # 通用错误 (1000-1999)
    INTERNAL_ERROR = "1000"
    INVALID_REQUEST = "1001"
    UNAUTHORIZED = "1002"
    FORBIDDEN = "1003"
    NOT_FOUND = "1004"
    GENERAL_ERROR = "1005"
    
    # 文件相关错误 (2000-2999)
    FILE_NOT_FOUND = "2000"
    FILE_TOO_LARGE = "2001"
    INVALID_FILE_FORMAT = "2002"
    FILE_UPLOAD_FAILED = "2003"
    FILE_SAVE_FAILED = "2004"
    FILE_INVALID_NAME = "2005"
    FILE_INVALID_TYPE = "2006"
    FILE_INVALID_PATH = "2007"
    FILE_READ_FAILED = "2008"
    FILE_DELETE_FAILED = "2009"
    
    # 会话相关错误 (3000-3999)
    SESSION_NOT_FOUND = "3000"
    SESSION_EXPIRED = "3001"
    SESSION_CREATION_FAILED = "3002"
    
    # EPUB相关错误 (4000-4999)
    EPUB_PARSE_ERROR = "4000"
    EPUB_INVALID_STRUCTURE = "4001"
    EPUB_EXPORT_FAILED = "4002"
    EPUB_EXTRACTION_FAILED = "4003"
    
    # 替换相关错误 (5000-5999)
    REPLACE_RULES_INVALID = "5000"
    REPLACE_OPERATION_FAILED = "5001"


class FileNode(BaseModel):
    """文件节点模型"""
    name: str = Field(..., description="文件名")
    path: str = Field(..., description="文件路径")
    type: FileType = Field(..., description="文件类型")
    size: Optional[int] = Field(None, description="文件大小（字节）")
    mime_type: Optional[str] = Field(None, description="MIME类型")
    modified_time: Optional[datetime] = Field(None, description="修改时间")
    children: Optional[List['FileNode']] = Field(None, description="子文件（目录类型）")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BookMetadata(BaseModel):
    """书籍元数据模型"""
    title: str = Field(..., description="书名")
    author: str = Field(..., description="作者")
    language: Optional[str] = Field("zh", description="语言")
    publisher: Optional[str] = Field(None, description="出版社")
    publication_date: Optional[str] = Field(None, description="出版日期")
    isbn: Optional[str] = Field(None, description="ISBN")
    description: Optional[str] = Field(None, description="描述")
    cover_image: Optional[str] = Field(None, description="封面图片路径")
    contributor: Optional[List[str]] = Field(None, description="贡献者")
    subject: Optional[List[str]] = Field(None, description="主题")
    rights: Optional[str] = Field(None, description="版权信息")


class SessionInfo(BaseModel):
    """会话信息模型"""
    session_id: str = Field(..., description="会话ID")
    file_type: FileType = Field(FileType.FILE, description="文件类型")
    file_tree: List[FileNode] = Field(..., description="文件树")
    metadata: BookMetadata = Field(..., description="书籍元数据")
    created_at: datetime = Field(..., description="创建时间")
    last_accessed: datetime = Field(..., description="最后访问时间")
    expires_at: datetime = Field(..., description="过期时间")
    status: str = Field(..., description="会话状态")
    original_filename: Optional[str] = Field(None, description="原始文件名")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FileContent(BaseModel):
    """文件内容模型"""
    path: str = Field(..., description="文件路径")
    content: str = Field(..., description="文件内容")
    encoding: str = Field("utf-8", description="编码格式")
    mime_type: str = Field(..., description="MIME类型")
    size: int = Field(..., description="文件大小")
    is_binary: bool = Field(False, description="是否为二进制文件")
    chunk_info: Optional[Dict[str, Any]] = Field(None, description="分块信息")
    checksum: Optional[str] = Field(None, description="文件校验和")
    last_modified: Optional[datetime] = Field(None, description="最后修改时间")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CurrentFile(BaseModel):
    """当前编辑文件模型"""
    path: str = Field(..., description="文件路径")
    content: str = Field(..., description="当前内容")
    original_content: str = Field(..., description="原始内容")
    is_modified: bool = Field(False, description="是否已修改")
    last_saved: Optional[datetime] = Field(None, description="最后保存时间")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ApiResponse(BaseModel, Generic[T]):
    """通用API响应模型"""
    status: ResponseStatus = Field(..., description="响应状态")
    message: str = Field(..., description="响应消息")
    data: Optional[T] = Field(None, description="响应数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    
    @property
    def success(self) -> bool:
        """兼容性属性：根据status判断是否成功"""
        return self.status == ResponseStatus.SUCCESS
    
    def model_dump(self, **kwargs):
        """重写序列化方法，添加success字段"""
        result = super().model_dump(**kwargs)
        result['success'] = self.success
        return result

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorResponse(BaseModel):
    """错误响应模型"""
    status: str = "error"
    error_code: str = Field(..., description="错误码")
    message: str = Field(..., description="错误消息")
    details: Optional[dict] = Field(None, description="错误详情")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    @property
    def success(self) -> bool:
        """兼容性属性：错误响应总是返回False"""
        return False
    
    def model_dump(self, **kwargs):
        """重写序列化方法，添加success字段"""
        result = super().model_dump(**kwargs)
        result['success'] = self.success
        return result

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SimpleErrorResponse(BaseModel):
    """简单错误响应模型（用于测试兼容）"""
    success: bool = False
    error: str = Field(..., description="错误消息")
    message: Optional[str] = Field(None, description="详细消息")


class SimpleSuccessResponse(BaseModel, Generic[T]):
    """简单成功响应模型（用于测试兼容）"""
    success: bool = True
    data: T = Field(..., description="响应数据")
    message: Optional[str] = Field(None, description="成功消息")


class SaveFileRequest(BaseModel):
    """文件保存请求模型"""
    session_id: str = Field(..., description="会话ID")
    file_path: str = Field(..., description="文件路径")
    content: str = Field(..., description="文件内容")
    encoding: str = Field("utf-8", description="编码格式")


class ExportRequest(BaseModel):
    """导出请求模型"""
    session_id: str = Field(..., description="会话ID")
    metadata: BookMetadata = Field(..., description="更新的元数据")
    include_images: bool = Field(True, description="是否包含图片")
    compression_level: int = Field(6, ge=0, le=9, description="压缩级别")


class ReplaceRule(BaseModel):
    """替换规则模型"""
    original: str = Field(..., description="搜索文本")
    replacement: str = Field(..., description="替换文本")
    is_regex: bool = Field(False, description="是否使用正则表达式")
    enabled: bool = Field(True, description="是否启用此规则")
    description: Optional[str] = Field("", description="规则描述")
    case_sensitive: bool = Field(True, description="是否区分大小写")
    target_files: Optional[List[str]] = Field(None, description="目标文件列表")


class BatchReplaceRequest(BaseModel):
    """批量替换请求模型"""
    session_id: str = Field(..., description="会话ID")
    rules: List[ReplaceRule] = Field(..., description="替换规则列表")
    target_files: Optional[List[str]] = Field(None, description="目标文件列表")
    case_sensitive: bool = Field(True, description="是否区分大小写")
    use_regex: bool = Field(False, description="是否使用正则表达式")


class RuleValidationResult(BaseModel):
    """规则文件验证结果模型"""
    is_valid: bool = Field(..., description="是否有效")
    total_rules: int = Field(..., description="总规则数量")
    valid_rules: int = Field(..., description="有效规则数量")
    invalid_rules: List[Dict[str, Any]] = Field(default_factory=list, description="无效规则详情")
    warnings: List[str] = Field(default_factory=list, description="警告信息")


class ReplaceProgress(BaseModel):
    """替换进度模型"""
    session_id: str = Field(..., description="会话ID")
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="处理状态")
    total_files: int = Field(0, description="总文件数")
    processed_files: int = Field(0, description="已处理文件数")
    total_replacements: int = Field(0, description="总替换数量")
    current_file: str = Field("", description="当前处理文件")
    progress_percentage: float = Field(0.0, ge=0, le=100, description="进度百分比")
    start_time: float = Field(..., description="开始时间戳")
    estimated_remaining: float = Field(0, description="预计剩余时间（秒）")
    error_message: Optional[str] = Field(None, description="错误消息")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ReplaceResult(BaseModel):
    """替换结果模型"""
    file_path: str = Field(..., description="文件路径")
    replacement_count: int = Field(..., description="替换数量")
    replacements: List[Dict[str, Any]] = Field(default_factory=list, description="替换详情列表")
    original_size: int = Field(..., description="原始文件大小")
    new_size: int = Field(..., description="新文件大小")
    errors: List[str] = Field(default_factory=list, description="错误信息")


class BatchReplaceReport(BaseModel):
    """批量替换报告模型"""
    task_id: str = Field(..., description="任务ID")
    session_id: str = Field(..., description="会话ID")
    total_files: int = Field(..., description="处理的文件总数")
    total_replacements: int = Field(..., description="总替换数量")
    results: List[ReplaceResult] = Field(..., description="替换结果列表")
    file_stats: Dict[str, Any] = Field(default_factory=dict, description="文件统计信息")
    rule_stats: Dict[str, int] = Field(default_factory=dict, description="规则统计信息")
    generated_at: float = Field(..., description="生成时间戳")
    errors: List[str] = Field(default_factory=list, description="全局错误")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PreviewRequest(BaseModel):
    """预览请求模型"""
    session_id: str = Field(..., description="会话ID")
    file_path: str = Field(..., description="文件路径")
    base_url: Optional[str] = Field(None, description="基础URL")


class HealthCheck(BaseModel):
    """健康检查模型"""
    status: str = Field(..., description="服务状态")
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = Field(..., description="API版本")
    uptime: float = Field(..., description="运行时间（秒）")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# 文件信息模型
class FileInfo(BaseModel):
    """文件信息模型"""
    filename: str = Field(..., description="文件名")
    size: int = Field(..., description="文件大小")
    type: str = Field(..., description="文件类型")
    mime_type: Optional[str] = Field(None, description="MIME类型")
    encoding: Optional[str] = Field(None, description="文件编码")
    checksum: Optional[str] = Field(None, description="文件校验和")

# API响应模型
class UploadResponse(BaseModel):
    """文件上传响应模型"""
    success: bool = True
    session_id: str = Field(..., description="会话ID")
    file_tree: List[FileNode] = Field(..., description="文件树")
    metadata: BookMetadata = Field(..., description="书籍元数据")
    message: str = Field("文件上传成功", description="响应消息")
    original_filename: str = Field(..., description="原始文件名")
    file_size: int = Field(..., description="文件大小")
    upload_time: datetime = Field(default_factory=datetime.now, description="上传时间")
    file_info: Optional[FileInfo] = Field(None, description="文件详细信息")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FileContentResponse(BaseModel):
    """文件内容响应模型"""
    success: bool = True
    content: str = Field(..., description="文件内容")
    encoding: str = Field("utf-8", description="编码格式")
    mime_type: str = Field(..., description="MIME类型")
    size: int = Field(..., description="文件大小")
    last_modified: Optional[datetime] = Field(None, description="最后修改时间")
    is_binary: bool = Field(False, description="是否为二进制文件")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FileTreeResponse(BaseModel):
    """文件树响应模型"""
    success: bool = True
    file_tree: List[FileNode] = Field(..., description="文件树")
    total_files: int = Field(..., description="总文件数")
    total_size: int = Field(..., description="总大小")


class SessionInfoResponse(BaseModel):
    """会话信息响应模型"""
    success: bool = True
    session_info: SessionInfo = Field(..., description="会话信息")


class SessionListResponse(BaseModel):
    """会话列表响应模型"""
    success: bool = True
    sessions: List[SessionInfo] = Field(..., description="会话列表")
    total_count: int = Field(..., description="总数量")


class ReplaceValidationResponse(BaseModel):
    """规则验证响应模型"""
    success: bool = True
    valid: bool = Field(..., description="是否有效")
    rule_count: int = Field(..., description="规则数量")
    rules_preview: List[Dict[str, Any]] = Field(default_factory=list, description="规则预览")
    errors: List[str] = Field(default_factory=list, description="错误列表")
    warnings: List[str] = Field(default_factory=list, description="警告列表")
    recommendation: Optional[str] = Field(None, description="建议")
    statistics: Dict[str, Any] = Field(default_factory=dict, description="统计信息")


class ReplaceExecuteResponse(BaseModel):
    """替换执行响应模型"""
    success: bool = True
    task_id: str = Field(..., description="任务ID")
    session_id: str = Field(..., description="会话ID")
    message: str = Field("替换任务已启动", description="响应消息")
    estimated_time: Optional[float] = Field(None, description="预计完成时间（秒）")


class ReplaceReportResponse(BaseModel):
    """替换报告响应模型"""
    success: bool = True
    report: BatchReplaceReport = Field(..., description="替换报告")
    format: str = Field("json", description="报告格式")


class SearchReplaceRequest(BaseModel):
    """搜索替换请求模型"""
    session_id: str = Field(..., description="会话ID")
    search_term: str = Field(..., description="搜索词")
    replace_term: Optional[str] = Field(None, description="替换词")
    case_sensitive: bool = Field(True, description="是否区分大小写")
    use_regex: bool = Field(False, description="是否使用正则表达式")
    file_path: Optional[str] = Field(None, description="指定文件路径")
    replace_all: bool = Field(False, description="是否替换所有")


class SearchMatch(BaseModel):
    """搜索匹配结果模型"""
    file_path: str = Field(..., description="文件路径")
    line_number: int = Field(..., description="行号")
    column_start: int = Field(..., description="开始列")
    column_end: int = Field(..., description="结束列")
    matched_text: str = Field(..., description="匹配文本")
    context_before: str = Field("", description="前文")
    context_after: str = Field("", description="后文")


class SearchReplaceResponse(BaseModel):
    """搜索替换响应模型"""
    success: bool = True
    matches: List[SearchMatch] = Field(default_factory=list, description="匹配结果")
    total_matches: int = Field(0, description="总匹配数")
    replacements_made: int = Field(0, description="已替换数量")
    files_affected: List[str] = Field(default_factory=list, description="受影响的文件")
    message: str = Field("", description="操作消息")


# 更新FileNode模型以支持递归引用
FileNode.model_rebuild()