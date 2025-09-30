"""用户认证服务"""

from datetime import datetime, timedelta
from typing import Optional, List
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import HTTPException, status
from db.models.auth import User, InvitationCode, UserSession, AuditLog
from schemas.auth import UserCreate, UserLogin, TokenData, InvitationCodeCreate
import secrets
import hashlib
import string
import random

class AuthService:
    """认证服务类"""
    
    def __init__(self, db: Session, secret_key: str, algorithm: str = "HS256"):
        self.db = db
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = 60
        self.refresh_token_expire_days = 7
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def create_refresh_token(self, data: dict) -> str:
        """创建刷新令牌"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str, token_type: str = "access") -> TokenData:
        """验证令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            username: str = payload.get("sub")
            token_type_in_payload: str = payload.get("type")
            
            if username is None or token_type_in_payload != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="无效的令牌",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return TokenData(username=username)
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return self.db.query(User).filter(User.username == username).first()
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据用户ID获取用户"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """用户认证"""
        user = self.get_user_by_username(username)
        if not user:
            return None
        
        # 检查账户是否被锁定
        if user.is_locked():
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"账户已被锁定，请在 {user.locked_until} 后重试"
            )
        
        # 验证密码
        if not user.verify_password(password):
            # 增加失败尝试次数
            user.failed_login_attempts += 1
            
            # 如果失败次数过多，锁定账户
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.utcnow() + timedelta(minutes=30)
                self.log_audit(user.id, "account_locked", "user", str(user.id), 
                             {"reason": "too_many_failed_attempts"})
            
            self.db.commit()
            return None
        
        # 登录成功，重置失败次数
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.utcnow()
        user.login_count += 1
        self.db.commit()
        
        return user
    
    def register_user(self, user_data: UserCreate) -> User:
        """用户注册"""
        # 验证邀请码
        invitation = self.db.query(InvitationCode).filter(
            InvitationCode.code == user_data.invitation_code
        ).first()
        
        if not invitation or not invitation.is_valid():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邀请码无效或已过期"
            )
        
        # 检查用户名是否已存在
        if self.db.query(User).filter(User.username == user_data.username).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )
        
        # 创建新用户
        user = User(
            username=user_data.username,
            role="user"
        )
        user.set_password(user_data.password)
        
        self.db.add(user)
        self.db.flush()  # 获取用户ID
        
        # 使用邀请码
        invitation.use_code(user.id)
        
        # 记录审计日志
        self.log_audit(user.id, "user_registered", "user", str(user.id), 
                      {"invitation_code": user_data.invitation_code})
        
        self.db.commit()
        return user
    
    def create_user_session(self, user: User, ip_address: str, user_agent: str) -> UserSession:
        """创建用户会话"""
        session_id = secrets.token_urlsafe(32)
        access_token = self.create_access_token(data={"sub": user.username})
        token_hash = hashlib.sha256(access_token.encode()).hexdigest()
        
        session = UserSession(
            session_id=session_id,
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes),
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.db.add(session)
        self.db.commit()
        
        return session
    
    def invalidate_user_sessions(self, user_id: int):
        """使用户所有会话失效"""
        self.db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_active == True
        ).update({"is_active": False})
        self.db.commit()
    
    def generate_invitation_code(self, created_by: int, code_data: InvitationCodeCreate) -> InvitationCode:
        """生成邀请码"""
        # 生成唯一的邀请码
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
            if not self.db.query(InvitationCode).filter(InvitationCode.code == code).first():
                break
        
        expires_at = datetime.utcnow() + timedelta(days=code_data.expires_in_days)
        
        invitation = InvitationCode(
            code=code,
            created_by=created_by,
            expires_at=expires_at,
            usage_limit=code_data.usage_limit,
            code_type=code_data.code_type,
            description=code_data.description
        )
        
        self.db.add(invitation)
        self.db.commit()
        
        # 记录审计日志
        self.log_audit(created_by, "invitation_code_created", "invitation_code", str(invitation.id),
                      {"code": code, "expires_at": expires_at.isoformat()})
        
        return invitation
    
    def get_invitation_codes(self, page: int = 1, page_size: int = 20, 
                           status_filter: Optional[str] = None) -> tuple[List[InvitationCode], int]:
        """获取邀请码列表"""
        query = self.db.query(InvitationCode)
        
        # 应用状态过滤
        if status_filter == "active":
            query = query.filter(
                InvitationCode.is_active == True,
                InvitationCode.expires_at > datetime.utcnow(),
                InvitationCode.usage_count < InvitationCode.usage_limit
            )
        elif status_filter == "used":
            query = query.filter(InvitationCode.usage_count >= InvitationCode.usage_limit)
        elif status_filter == "expired":
            query = query.filter(InvitationCode.expires_at <= datetime.utcnow())
        
        total = query.count()
        
        # 分页
        offset = (page - 1) * page_size
        codes = query.order_by(InvitationCode.created_at.desc()).offset(offset).limit(page_size).all()
        
        return codes, total
    
    def delete_invitation_code(self, code_id: int, deleted_by: int) -> bool:
        """删除邀请码"""
        invitation = self.db.query(InvitationCode).filter(InvitationCode.id == code_id).first()
        if not invitation:
            return False
        
        # 记录审计日志
        self.log_audit(deleted_by, "invitation_code_deleted", "invitation_code", str(code_id),
                      {"code": invitation.code})
        
        self.db.delete(invitation)
        self.db.commit()
        return True
    
    def get_users(self, page: int = 1, page_size: int = 20) -> tuple[List[User], int]:
        """获取用户列表"""
        query = self.db.query(User)
        total = query.count()
        
        offset = (page - 1) * page_size
        users = query.order_by(User.created_at.desc()).offset(offset).limit(page_size).all()
        
        return users, total
    
    def update_user(self, user_id: int, is_active: Optional[bool] = None, 
                   role: Optional[str] = None, updated_by: int = None) -> Optional[User]:
        """更新用户信息"""
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        
        changes = {}
        if is_active is not None:
            user.is_active = is_active
            changes["is_active"] = is_active
        
        if role is not None:
            user.role = role
            changes["role"] = role
        
        user.updated_at = datetime.utcnow()
        
        # 记录审计日志
        if updated_by:
            self.log_audit(updated_by, "user_updated", "user", str(user_id), changes)
        
        self.db.commit()
        return user
    
    def change_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        """修改密码"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        
        # 验证当前密码
        if not user.verify_password(current_password):
            return False
        
        # 设置新密码
        user.set_password(new_password)
        user.updated_at = datetime.utcnow()
        
        # 使所有会话失效
        self.invalidate_user_sessions(user_id)
        
        # 记录审计日志
        self.log_audit(user_id, "password_changed", "user", str(user_id), {})
        
        self.db.commit()
        return True
    
    def get_audit_logs(self, page: int = 1, page_size: int = 50, 
                      user_id: Optional[int] = None, 
                      action: Optional[str] = None) -> tuple[List[AuditLog], int]:
        """获取审计日志"""
        query = self.db.query(AuditLog)
        
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        
        if action:
            query = query.filter(AuditLog.action == action)
        
        total = query.count()
        
        offset = (page - 1) * page_size
        logs = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size).all()
        
        return logs, total
    
    def log_audit(self, user_id: Optional[int], action: str, resource_type: str, 
                  resource_id: str, details: dict, ip_address: str = None, 
                  user_agent: str = None):
        """记录审计日志"""
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.db.add(audit_log)
        # 注意：这里不提交，由调用方决定何时提交
    
    def create_admin_user(self, username: str, password: str) -> User:
        """创建管理员用户（仅用于初始化）"""
        # 检查是否已存在管理员
        existing_admin = self.db.query(User).filter(User.role == "admin").first()
        if existing_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="管理员账户已存在"
            )
        
        # 检查用户名是否已存在
        if self.db.query(User).filter(User.username == username).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )
        
        # 创建管理员用户
        admin_user = User(
            username=username,
            role="admin",
            is_active=True
        )
        admin_user.set_password(password)
        
        self.db.add(admin_user)
        self.db.commit()
        
        # 记录审计日志
        self.log_audit(admin_user.id, "admin_user_created", "user", str(admin_user.id), 
                      {"username": username})
        self.db.commit()
        
        return admin_user