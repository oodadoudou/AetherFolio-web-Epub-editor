"""用户认证相关数据模型"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import bcrypt

Base = declarative_base()

class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)
    login_count = Column(Integer, default=0)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime)
    profile_data = Column(JSON)
    
    # 关系
    created_invitations = relationship("InvitationCode", foreign_keys="InvitationCode.created_by", back_populates="creator")
    used_invitations = relationship("InvitationCode", foreign_keys="InvitationCode.used_by", back_populates="user")
    sessions = relationship("UserSession", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    
    def set_password(self, password: str):
        """设置密码"""
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str) -> bool:
        """验证密码"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def is_admin(self) -> bool:
        """检查是否为管理员"""
        return self.role == "admin"
    
    def is_locked(self) -> bool:
        """检查账户是否被锁定"""
        if self.locked_until:
            return datetime.utcnow() < self.locked_until
        return False

class InvitationCode(Base):
    """邀请码模型"""
    __tablename__ = "invitation_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(32), unique=True, index=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime)
    used_by = Column(Integer, ForeignKey("users.id"))
    is_active = Column(Boolean, default=True)
    usage_limit = Column(Integer, default=1)
    usage_count = Column(Integer, default=0)
    code_type = Column(String(20), default="registration")
    description = Column(Text)
    
    # 关系
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_invitations")
    user = relationship("User", foreign_keys=[used_by], back_populates="used_invitations")
    
    def is_valid(self) -> bool:
        """检查邀请码是否有效"""
        now = datetime.utcnow()
        return (
            self.is_active and
            now < self.expires_at and
            self.usage_count < self.usage_limit
        )
    
    def use_code(self, user_id: int):
        """使用邀请码"""
        if not self.is_valid():
            raise ValueError("邀请码无效或已过期")
        
        self.used_at = datetime.utcnow()
        self.used_by = user_id
        self.usage_count += 1
        
        if self.usage_count >= self.usage_limit:
            self.is_active = False

class UserSession(Base):
    """用户会话模型"""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_accessed_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    is_active = Column(Boolean, default=True)
    
    # 关系
    user = relationship("User", back_populates="sessions")

class AuditLog(Base):
    """审计日志模型"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(50), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(String(100))
    details = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    user = relationship("User", back_populates="audit_logs")