"""用户数据访问仓储"""

from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from .base import BaseRepository
from ..models.auth import User, InvitationCode

class UserRepository(BaseRepository[User]):
    """用户仓储类"""
    
    def __init__(self, session: Session):
        super().__init__(session, User)
    
    def get_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户
        
        Args:
            username: 用户名
            
        Returns:
            Optional[User]: 用户实例或None
        """
        return self.session.query(User).filter(User.username == username).first()
    
    def create_user(
        self, 
        username: str, 
        password: str, 
        role: str = "user",
        **kwargs
    ) -> User:
        """创建用户
        
        Args:
            username: 用户名
            password: 密码
            role: 用户角色
            **kwargs: 其他用户属性
            
        Returns:
            User: 创建的用户实例
        """
        user = User(
            username=username,
            role=role,
            **kwargs
        )
        user.set_password(password)
        
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        
        return user
    
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """用户认证
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            Optional[User]: 认证成功返回用户实例，否则返回None
        """
        user = self.get_by_username(username)
        
        if not user:
            return None
        
        # 检查账户是否被锁定
        if user.is_locked():
            return None
        
        # 检查账户是否激活
        if not user.is_active:
            return None
        
        # 验证密码
        if user.verify_password(password):
            # 记录成功登录
            user.record_login()
            self.session.commit()
            return user
        else:
            # 记录失败登录
            user.increment_failed_attempts()
            self.session.commit()
            return None
    
    def change_password(self, user_id: int, new_password: str) -> bool:
        """修改用户密码
        
        Args:
            user_id: 用户ID
            new_password: 新密码
            
        Returns:
            bool: 是否修改成功
        """
        user = self.get_by_id(user_id)
        if user:
            user.set_password(new_password)
            self.session.commit()
            return True
        return False
    
    def update_password(self, user_id: int, new_password: str) -> bool:
        """更新用户密码（别名方法）
        
        Args:
            user_id: 用户ID
            new_password: 新密码
            
        Returns:
            bool: 是否更新成功
        """
        return self.change_password(user_id, new_password)
    
    def increment_failed_attempts(self, user_id: int) -> bool:
        """增加失败登录尝试次数
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否更新成功
        """
        user = self.get_by_id(user_id)
        if user:
            user.failed_login_attempts += 1
            self.session.commit()
            return True
        return False
    
    def reset_failed_attempts(self, user_id: int) -> bool:
        """重置失败登录尝试次数
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否重置成功
        """
        user = self.get_by_id(user_id)
        if user:
            user.failed_login_attempts = 0
            self.session.commit()
            return True
        return False
    
    def lock_user(self, user_id: int, lock_duration_hours: int = 24) -> bool:
        """锁定用户
        
        Args:
            user_id: 用户ID
            lock_duration_hours: 锁定时长（小时）
            
        Returns:
            bool: 是否锁定成功
        """
        user = self.get_by_id(user_id)
        if user:
            user.locked_until = datetime.utcnow() + timedelta(hours=lock_duration_hours)
            self.session.commit()
            return True
        return False
    
    def unlock_user(self, user_id: int) -> bool:
        """解锁用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否解锁成功
        """
        user = self.get_by_id(user_id)
        if user:
            user.locked_until = None
            user.failed_login_attempts = 0
            self.session.commit()
            return True
        return False
    
    def activate_user(self, user_id: int) -> bool:
        """激活用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否激活成功
        """
        user = self.get_by_id(user_id)
        if user:
            user.is_active = True
            self.session.commit()
            return True
        return False
    
    def deactivate_user(self, user_id: int) -> bool:
        """停用用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否停用成功
        """
        user = self.get_by_id(user_id)
        if user:
            user.is_active = False
            self.session.commit()
            return True
        return False
    
    def get_active_users(self, limit: int = 100, offset: int = 0) -> List[User]:
        """获取活跃用户列表
        
        Args:
            limit: 限制数量
            offset: 偏移量
            
        Returns:
            List[User]: 活跃用户列表
        """
        return (
            self.session.query(User)
            .filter(User.is_active == True)
            .offset(offset)
            .limit(limit)
            .all()
        )
    
    def get_admin_users(self) -> List[User]:
        """获取管理员用户列表
        
        Returns:
            List[User]: 管理员用户列表
        """
        return (
            self.session.query(User)
            .filter(User.role == "admin")
            .filter(User.is_active == True)
            .all()
        )
    
    def get_locked_users(self) -> List[User]:
        """获取被锁定的用户列表
        
        Returns:
            List[User]: 被锁定的用户列表
        """
        now = datetime.utcnow()
        return (
            self.session.query(User)
            .filter(User.locked_until.isnot(None))
            .filter(User.locked_until > now)
            .all()
        )
    
    def search_users(self, search_term: str, limit: int = 50) -> List[User]:
        """搜索用户
        
        Args:
            search_term: 搜索词
            limit: 限制数量
            
        Returns:
            List[User]: 搜索结果
        """
        return self.search(search_term, ['username'], limit)
    
    def get_user_stats(self) -> dict:
        """获取用户统计信息
        
        Returns:
            dict: 用户统计信息
        """
        total_users = self.session.query(User).count()
        active_users = self.session.query(User).filter(User.is_active == True).count()
        admin_users = self.session.query(User).filter(User.role == "admin").count()
        
        now = datetime.utcnow()
        locked_users = (
            self.session.query(User)
            .filter(User.locked_until.isnot(None))
            .filter(User.locked_until > now)
            .count()
        )
        
        # 最近30天注册的用户
        thirty_days_ago = now - timedelta(days=30)
        recent_users = (
            self.session.query(User)
            .filter(User.created_at >= thirty_days_ago)
            .count()
        )
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': total_users - active_users,
            'admin_users': admin_users,
            'locked_users': locked_users,
            'recent_users': recent_users
        }

class InvitationCodeRepository(BaseRepository[InvitationCode]):
    """邀请码仓储类"""
    
    def __init__(self, session: Session):
        super().__init__(session, InvitationCode)
    
    def get_by_code(self, code: str) -> Optional[InvitationCode]:
        """根据邀请码获取记录
        
        Args:
            code: 邀请码
            
        Returns:
            Optional[InvitationCode]: 邀请码实例或None
        """
        return self.session.query(InvitationCode).filter(InvitationCode.code == code).first()
    
    def create_invitation_code(
        self,
        code: str,
        created_by: int,
        expires_at: datetime,
        usage_limit: int = 1,
        code_type: str = "registration",
        description: str = None
    ) -> InvitationCode:
        """创建邀请码
        
        Args:
            code: 邀请码
            created_by: 创建者ID
            expires_at: 过期时间
            usage_limit: 使用次数限制
            code_type: 邀请码类型
            description: 描述
            
        Returns:
            InvitationCode: 创建的邀请码实例
        """
        invitation = InvitationCode(
            code=code,
            created_by=created_by,
            expires_at=expires_at,
            usage_limit=usage_limit,
            code_type=code_type,
            description=description
        )
        
        self.session.add(invitation)
        self.session.commit()
        self.session.refresh(invitation)
        
        return invitation
    
    def use_invitation_code(self, code: str, user_id: int) -> bool:
        """使用邀请码
        
        Args:
            code: 邀请码
            user_id: 使用者用户ID
            
        Returns:
            bool: 是否使用成功
        """
        invitation = self.get_by_code(code)
        
        if not invitation or not invitation.is_valid():
            return False
        
        try:
            invitation.use_code(user_id)
            self.session.commit()
            return True
        except ValueError:
            return False
    
    def get_valid_codes(self, created_by: int = None) -> List[InvitationCode]:
        """获取有效的邀请码
        
        Args:
            created_by: 创建者ID（可选）
            
        Returns:
            List[InvitationCode]: 有效邀请码列表
        """
        query = (
            self.session.query(InvitationCode)
            .filter(InvitationCode.is_active == True)
            .filter(InvitationCode.expires_at > datetime.utcnow())
        )
        
        if created_by:
            query = query.filter(InvitationCode.created_by == created_by)
        
        return query.all()
    
    def get_expired_codes(self) -> List[InvitationCode]:
        """获取过期的邀请码
        
        Returns:
            List[InvitationCode]: 过期邀请码列表
        """
        return (
            self.session.query(InvitationCode)
            .filter(InvitationCode.expires_at <= datetime.utcnow())
            .all()
        )
    
    def cleanup_expired_codes(self) -> int:
        """清理过期的邀请码
        
        Returns:
            int: 清理的邀请码数量
        """
        expired_codes = self.get_expired_codes()
        count = len(expired_codes)
        
        for code in expired_codes:
            code.is_active = False
        
        self.session.commit()
        return count