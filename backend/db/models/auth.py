"""用户认证相关数据模型"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import bcrypt

from ..base import BaseModel

class User(BaseModel):
    """用户模型"""
    __tablename__ = "users"
    
    username = Column(String(50), unique=True, index=True, nullable=False, comment="用户名")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    role = Column(String(20), default="user", comment="用户角色")
    is_active = Column(Boolean, default=True, comment="是否激活")
    last_login_at = Column(DateTime, comment="最后登录时间")
    login_count = Column(Integer, default=0, comment="登录次数")
    failed_login_attempts = Column(Integer, default=0, comment="失败登录尝试次数")
    locked_until = Column(DateTime, comment="锁定到期时间")
    profile_data = Column(JSON, comment="用户配置数据")
    
    # 关系
    created_invitations = relationship(
        "InvitationCode", 
        foreign_keys="InvitationCode.created_by", 
        back_populates="creator"
    )
    used_invitations = relationship(
        "InvitationCode", 
        foreign_keys="InvitationCode.used_by", 
        back_populates="user"
    )
    sessions = relationship("UserSession", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    
    def set_password(self, password: str) -> None:
        """设置密码
        
        Args:
            password: 明文密码
        """
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str) -> bool:
        """验证密码
        
        Args:
            password: 明文密码
            
        Returns:
            bool: 密码是否正确
        """
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def is_admin(self) -> bool:
        """检查是否为管理员
        
        Returns:
            bool: 是否为管理员
        """
        return self.role == "admin"
    
    def is_locked(self) -> bool:
        """检查账户是否被锁定
        
        Returns:
            bool: 账户是否被锁定
        """
        if self.locked_until:
            return datetime.utcnow() < self.locked_until
        return False
    
    def increment_failed_attempts(self) -> None:
        """增加失败登录尝试次数"""
        self.failed_login_attempts += 1
        
        # 如果失败次数超过5次，锁定账户1小时
        if self.failed_login_attempts >= 5:
            from datetime import timedelta
            self.locked_until = datetime.utcnow() + timedelta(hours=1)
    
    def reset_failed_attempts(self) -> None:
        """重置失败登录尝试次数"""
        self.failed_login_attempts = 0
        self.locked_until = None
    
    def record_login(self) -> None:
        """记录登录"""
        self.last_login_at = datetime.utcnow()
        self.login_count += 1
        self.reset_failed_attempts()

class InvitationCode(BaseModel):
    """邀请码模型"""
    __tablename__ = "invitation_codes"
    
    code = Column(String(32), unique=True, index=True, nullable=False, comment="邀请码")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, comment="创建者ID")
    expires_at = Column(DateTime, nullable=False, comment="过期时间")
    used_at = Column(DateTime, comment="使用时间")
    used_by = Column(Integer, ForeignKey("users.id"), comment="使用者ID")
    is_active = Column(Boolean, default=True, comment="是否激活")
    usage_limit = Column(Integer, default=1, comment="使用次数限制")
    usage_count = Column(Integer, default=0, comment="已使用次数")
    code_type = Column(String(20), default="registration", comment="邀请码类型")
    description = Column(Text, comment="描述")
    
    # 关系
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_invitations")
    user = relationship("User", foreign_keys=[used_by], back_populates="used_invitations")
    
    def is_valid(self) -> bool:
        """检查邀请码是否有效
        
        Returns:
            bool: 邀请码是否有效
        """
        now = datetime.utcnow()
        return (
            self.is_active and
            now < self.expires_at and
            self.usage_count < self.usage_limit
        )
    
    def use_code(self, user_id: int) -> None:
        """使用邀请码
        
        Args:
            user_id: 使用者用户ID
            
        Raises:
            ValueError: 邀请码无效或已过期
        """
        if not self.is_valid():
            raise ValueError("邀请码无效或已过期")
        
        self.used_at = datetime.utcnow()
        self.used_by = user_id
        self.usage_count += 1
        
        if self.usage_count >= self.usage_limit:
            self.is_active = False
    
    def deactivate(self) -> None:
        """停用邀请码"""
        self.is_active = False

class UserSession(BaseModel):
    """用户会话模型"""
    __tablename__ = "user_sessions"
    
    session_id = Column(String(64), unique=True, index=True, nullable=False, comment="会话ID")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    token_hash = Column(String(255), nullable=False, comment="令牌哈希")
    expires_at = Column(DateTime, nullable=False, comment="过期时间")
    last_accessed_at = Column(DateTime, default=datetime.utcnow, comment="最后访问时间")
    ip_address = Column(String(45), comment="IP地址")
    user_agent = Column(Text, comment="用户代理")
    is_active = Column(Boolean, default=True, comment="是否激活")
    
    # 关系
    user = relationship("User", back_populates="sessions")
    
    def is_expired(self) -> bool:
        """检查会话是否过期
        
        Returns:
            bool: 会话是否过期
        """
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self) -> bool:
        """检查会话是否有效
        
        Returns:
            bool: 会话是否有效
        """
        return self.is_active and not self.is_expired()
    
    def update_access_time(self) -> None:
        """更新最后访问时间"""
        self.last_accessed_at = datetime.utcnow()
    
    def invalidate(self) -> None:
        """使会话失效"""
        self.is_active = False

class AuditLog(BaseModel):
    """审计日志模型"""
    __tablename__ = "audit_logs"
    
    user_id = Column(Integer, ForeignKey("users.id"), comment="用户ID")
    action = Column(String(50), nullable=False, comment="操作类型")
    resource_type = Column(String(50), comment="资源类型")
    resource_id = Column(String(100), comment="资源ID")
    details = Column(JSON, comment="详细信息")
    ip_address = Column(String(45), comment="IP地址")
    user_agent = Column(Text, comment="用户代理")
    
    # 关系
    user = relationship("User", back_populates="audit_logs")
    
    @classmethod
    def create_log(
        cls,
        action: str,
        user_id: int = None,
        resource_type: str = None,
        resource_id: str = None,
        details: dict = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> 'AuditLog':
        """创建审计日志
        
        Args:
            action: 操作类型
            user_id: 用户ID
            resource_type: 资源类型
            resource_id: 资源ID
            details: 详细信息
            ip_address: IP地址
            user_agent: 用户代理
            
        Returns:
            AuditLog: 审计日志实例
        """
        return cls(
            action=action,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent
        )