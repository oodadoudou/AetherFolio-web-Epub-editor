"""替换模型"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ReplaceStatus(str, Enum):
    """替换状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class ReplaceRule(BaseModel):
    """替换规则模型"""
    
    original: str = Field(..., description="原始文本")
    replacement: str = Field(..., description="替换文本")
    is_regex: bool = Field(default=False, description="是否为正则表达式")
    description: Optional[str] = Field(None, description="规则描述")
    enabled: bool = Field(default=True, description="是否启用")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "original": self.original,
            "replacement": self.replacement,
            "is_regex": self.is_regex,
            "description": self.description,
            "enabled": self.enabled
        }


class ReplaceOptions(BaseModel):
    """替换选项模型"""
    
    case_sensitive: bool = Field(default=True, description="是否区分大小写")
    whole_word: bool = Field(default=False, description="是否全词匹配")
    use_regex: bool = Field(default=False, description="是否使用正则表达式")
    target_files: Optional[List[str]] = Field(None, description="目标文件列表")
    exclude_files: Optional[List[str]] = Field(None, description="排除文件列表")
    file_patterns: Optional[List[str]] = Field(None, description="文件模式")
    backup_before_replace: bool = Field(default=True, description="替换前是否备份")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "case_sensitive": self.case_sensitive,
            "whole_word": self.whole_word,
            "use_regex": self.use_regex,
            "target_files": self.target_files,
            "exclude_files": self.exclude_files,
            "file_patterns": self.file_patterns,
            "backup_before_replace": self.backup_before_replace
        }


class ReplaceProgress(BaseModel):
    """替换进度模型"""
    
    status: ReplaceStatus = Field(..., description="状态")
    percentage: float = Field(default=0.0, ge=0.0, le=100.0, description="完成百分比")
    current_file: Optional[str] = Field(None, description="当前处理文件")
    total_files: int = Field(default=0, description="总文件数")
    processed_files: int = Field(default=0, description="已处理文件数")
    total_replacements: int = Field(default=0, description="总替换次数")
    current_rule: Optional[str] = Field(None, description="当前规则")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    estimated_completion: Optional[datetime] = Field(None, description="预计完成时间")
    error_message: Optional[str] = Field(None, description="错误消息")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "status": self.status.value,
            "percentage": self.percentage,
            "current_file": self.current_file,
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "total_replacements": self.total_replacements,
            "current_rule": self.current_rule,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "estimated_completion": self.estimated_completion.isoformat() if self.estimated_completion else None,
            "error_message": self.error_message
        }
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ReplaceTask(BaseModel):
    """替换任务模型"""
    
    task_id: str = Field(..., description="任务ID")
    session_id: str = Field(..., description="会话ID")
    rules: List[ReplaceRule] = Field(..., description="替换规则列表")
    options: ReplaceOptions = Field(..., description="替换选项")
    status: ReplaceStatus = Field(default=ReplaceStatus.PENDING, description="任务状态")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    progress: Optional[ReplaceProgress] = Field(None, description="进度信息")
    
    def start(self) -> None:
        """开始任务"""
        self.status = ReplaceStatus.RUNNING
        self.started_at = datetime.now()
        if not self.progress:
            self.progress = ReplaceProgress(status=ReplaceStatus.RUNNING)
        else:
            self.progress.status = ReplaceStatus.RUNNING
            self.progress.start_time = self.started_at
    
    def complete(self) -> None:
        """完成任务"""
        self.status = ReplaceStatus.COMPLETED
        self.completed_at = datetime.now()
        if self.progress:
            self.progress.status = ReplaceStatus.COMPLETED
            self.progress.percentage = 100.0
    
    def fail(self, error_message: str) -> None:
        """任务失败"""
        self.status = ReplaceStatus.FAILED
        self.completed_at = datetime.now()
        if self.progress:
            self.progress.status = ReplaceStatus.FAILED
            self.progress.error_message = error_message
    
    def cancel(self) -> None:
        """取消任务"""
        self.status = ReplaceStatus.CANCELLED
        self.completed_at = datetime.now()
        if self.progress:
            self.progress.status = ReplaceStatus.CANCELLED
    
    def pause(self) -> None:
        """暂停任务"""
        self.status = ReplaceStatus.PAUSED
        if self.progress:
            self.progress.status = ReplaceStatus.PAUSED
    
    def resume(self) -> None:
        """恢复任务"""
        self.status = ReplaceStatus.RUNNING
        if self.progress:
            self.progress.status = ReplaceStatus.RUNNING
    
    def get_duration(self) -> Optional[float]:
        """获取任务持续时间（秒）"""
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "session_id": self.session_id,
            "rules": [rule.to_dict() for rule in self.rules],
            "options": self.options.to_dict(),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress.to_dict() if self.progress else None,
            "duration": self.get_duration()
        }
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ReplaceFileResult(BaseModel):
    """文件替换结果模型"""
    
    file_path: str = Field(..., description="文件路径")
    replacements_count: int = Field(default=0, description="替换次数")
    rules_applied: List[str] = Field(default_factory=list, description="应用的规则")
    success: bool = Field(default=True, description="是否成功")
    error_message: Optional[str] = Field(None, description="错误消息")
    original_size: Optional[int] = Field(None, description="原始文件大小")
    new_size: Optional[int] = Field(None, description="新文件大小")
    processing_time: Optional[float] = Field(None, description="处理时间（秒）")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "file_path": self.file_path,
            "replacements_count": self.replacements_count,
            "rules_applied": self.rules_applied,
            "success": self.success,
            "error_message": self.error_message,
            "original_size": self.original_size,
            "new_size": self.new_size,
            "processing_time": self.processing_time
        }


class ReplaceReport(BaseModel):
    """替换报告模型"""
    
    task_id: str = Field(..., description="任务ID")
    summary: Dict[str, Any] = Field(..., description="摘要信息")
    details: List[ReplaceFileResult] = Field(..., description="详细结果")
    statistics: Dict[str, Any] = Field(..., description="统计信息")
    generated_at: datetime = Field(default_factory=datetime.now, description="生成时间")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "summary": self.summary,
            "details": [detail.to_dict() for detail in self.details],
            "statistics": self.statistics,
            "generated_at": self.generated_at.isoformat()
        }
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ReplaceRuleValidation(BaseModel):
    """替换规则验证模型"""
    
    rule: ReplaceRule = Field(..., description="规则")
    is_valid: bool = Field(..., description="是否有效")
    errors: List[str] = Field(default_factory=list, description="错误列表")
    warnings: List[str] = Field(default_factory=list, description="警告列表")
    suggestions: List[str] = Field(default_factory=list, description="建议列表")
    
    def add_error(self, error: str) -> None:
        """添加错误"""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str) -> None:
        """添加警告"""
        self.warnings.append(warning)
    
    def add_suggestion(self, suggestion: str) -> None:
        """添加建议"""
        self.suggestions.append(suggestion)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "rule": self.rule.to_dict(),
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions
        }


class ReplaceRulesValidationResult(BaseModel):
    """替换规则验证结果模型"""
    
    is_valid: bool = Field(..., description="整体是否有效")
    validations: List[ReplaceRuleValidation] = Field(..., description="各规则验证结果")
    global_errors: List[str] = Field(default_factory=list, description="全局错误")
    global_warnings: List[str] = Field(default_factory=list, description="全局警告")
    
    def add_global_error(self, error: str) -> None:
        """添加全局错误"""
        self.global_errors.append(error)
        self.is_valid = False
    
    def add_global_warning(self, warning: str) -> None:
        """添加全局警告"""
        self.global_warnings.append(warning)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "is_valid": self.is_valid,
            "validations": [validation.to_dict() for validation in self.validations],
            "global_errors": self.global_errors,
            "global_warnings": self.global_warnings
        }