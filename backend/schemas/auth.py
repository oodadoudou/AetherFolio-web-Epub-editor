"""认证相关的Pydantic模式"""

from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    """用户创建模式"""
    username: str
    password: str
    invitation_code: str
    
    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3 or len(v) > 50:
            raise ValueError('用户名长度必须在3-50个字符之间')
        if not v.replace('_', '').isalnum():
            raise ValueError('用户名只能包含字母、数字和下划线')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('密码长度至少8个字符')
        return v

class UserLogin(BaseModel):
    """用户登录模式"""
    username: str
    password: str

class TokenResponse(BaseModel):
    """令牌响应模式"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int
    user_info: dict

class UserInfo(BaseModel):
    """用户信息模式"""
    user_id: int
    username: str
    role: str
    is_active: bool
    created_at: str
    last_login_at: Optional[str] = None
    login_count: int

class TokenData(BaseModel):
    """令牌数据模式"""
    username: Optional[str] = None

class InvitationCodeCreate(BaseModel):
    """邀请码创建模式"""
    expires_in_days: int = 7
    usage_limit: int = 1
    code_type: str = "registration"
    description: Optional[str] = None
    
    @validator('expires_in_days')
    def validate_expires_in_days(cls, v):
        if v < 1 or v > 365:
            raise ValueError('过期天数必须在1-365之间')
        return v
    
    @validator('usage_limit')
    def validate_usage_limit(cls, v):
        if v < 1 or v > 1000:
            raise ValueError('使用限制必须在1-1000之间')
        return v

class InvitationCodeInfo(BaseModel):
    """邀请码信息模式"""
    id: int
    code: str
    created_at: str
    expires_at: str
    used_at: Optional[str] = None
    used_by: Optional[str] = None
    is_active: bool
    usage_limit: int
    usage_count: int
    code_type: str
    description: Optional[str] = None

class InvitationCodeList(BaseModel):
    """邀请码列表模式"""
    codes: list[InvitationCodeInfo]
    total: int
    page: int
    page_size: int
    total_pages: int

class InvitationCodeStats(BaseModel):
    """邀请码统计模式"""
    total_codes: int
    active_codes: int
    used_codes: int
    expired_codes: int

class PasswordChange(BaseModel):
    """密码修改模式"""
    current_password: str
    new_password: str
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('新密码长度至少8个字符')
        return v

class UserUpdate(BaseModel):
    """用户更新模式"""
    is_active: Optional[bool] = None
    role: Optional[str] = None
    
    @validator('role')
    def validate_role(cls, v):
        if v and v not in ['user', 'admin']:
            raise ValueError('角色只能是user或admin')
        return v

class AuditLogInfo(BaseModel):
    """审计日志信息模式"""
    id: int
    user_id: Optional[int]
    username: Optional[str]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    details: Optional[dict]
    ip_address: Optional[str]
    created_at: str

class AuditLogList(BaseModel):
    """审计日志列表模式"""
    logs: list[AuditLogInfo]
    total: int
    page: int
    page_size: int
    total_pages: int