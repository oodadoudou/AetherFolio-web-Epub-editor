"""认证相关的API端点"""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.orm import Session
import hashlib
import secrets
import uuid
import random
import string

# 导入数据库相关模块
from db.connection import db_manager
from services.auth_service import AuthService

# 简化的数据模型
class UserCreate(BaseModel):
    username: str
    password: str
    invitation_code: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserInfo(BaseModel):
    user_id: int
    username: str
    role: str = "user"
    is_admin: bool = False
    is_active: bool = True
    created_at: str
    failed_login_attempts: int = 0
    last_login: Optional[str] = None

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: Optional[UserInfo] = None

class InvitationCodeCreate(BaseModel):
    expires_at: Optional[str] = None
    expiration_days: Optional[int] = None
    usage_limit: int = 1
    description: str = ""

class InvitationCodeInfo(BaseModel):
    id: int
    code: str
    usage_limit: int
    usage_count: int
    expires_at: str
    description: str
    is_active: bool
    created_at: str

class UserListResponse(BaseModel):
    items: List[dict]
    total: int
    page: int
    page_size: int
    total_pages: int

class UserDetailResponse(BaseModel):
    id: int
    username: str
    role: str
    created_at: str
    last_login: Optional[str] = None
    is_active: bool = True
    login_count: int = 0
    invitation_code_used: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

# 配置
SECRET_KEY = "your-secret-key-here-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Invitation codes will be managed through database-based service

# 获取数据库会话的依赖函数
def get_db_session():
    """获取数据库会话"""
    if not db_manager._initialized:
        db_manager.initialize_default_databases()
    
    session_gen = db_manager.get_session()
    session = next(session_gen)
    try:
        yield session
    finally:
        try:
            session.close()
        except:
            pass

# 获取认证服务的依赖函数
def get_auth_service(db: Session = Depends(get_db_session)) -> AuthService:
    """获取认证服务"""
    return AuthService(db, SECRET_KEY, ALGORITHM)

# 账户锁定存储
failed_login_attempts = {}  # {username: {count: int, last_attempt: datetime, locked_until: datetime}}
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

# 邀请码计数器
invitation_code_counter = 2

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
security = HTTPBearer()

def hash_password(password: str) -> str:
    """哈希密码"""
    # 优先使用bcrypt，如果不可用则使用SHA256
    try:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.hash(password)
    except ImportError:
        return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    # 检查是否是bcrypt哈希（以$2b$开头）
    if hashed_password.startswith('$2b$'):
        try:
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            return pwd_context.verify(plain_password, hashed_password)
        except ImportError:
            return False
    else:
        # 使用SHA256验证（向后兼容）
        return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建刷新令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security), auth_service: AuthService = Depends(get_auth_service)):
    """验证访问令牌"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )
        # 检查用户是否存在
        user = auth_service.get_user_by_username(username)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/register", response_model=Token)
async def register(user_data: UserCreate, auth_service: AuthService = Depends(get_auth_service)):
    """用户注册"""
    try:
        # 使用AuthService进行用户注册
        user = auth_service.register_user(user_data)
        
        # 创建访问令牌和刷新令牌
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        refresh_token = create_refresh_token(
            data={"sub": user.username}, expires_delta=refresh_token_expires
        )
        
        # 构建用户信息
        user_info = UserInfo(
            user_id=user.id,
            username=user.username,
            role=user.role,
            is_admin=user.is_admin(),
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else datetime.utcnow().isoformat(),
            failed_login_attempts=user.failed_login_attempts,
            last_login=user.last_login_at.isoformat() if user.last_login_at else None
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user_info
        }
        
    except HTTPException:
        # 重新抛出HTTP异常（如邀请码无效等）
        raise
    except Exception as e:
        # 处理其他异常
        print(f"注册过程中发生错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册过程中发生错误"
        )

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, auth_service: AuthService = Depends(get_auth_service)):
    """用户登录"""
    try:
        # 使用AuthService进行用户认证
        user = auth_service.authenticate_user(user_data.username, user_data.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 创建访问令牌和刷新令牌
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        refresh_token = create_refresh_token(
            data={"sub": user.username}, expires_delta=refresh_token_expires
        )
        
        # 构建用户信息
        user_info = UserInfo(
            user_id=user.id,
            username=user.username,
            role=user.role,
            is_admin=user.is_admin(),
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else datetime.utcnow().isoformat(),
            failed_login_attempts=user.failed_login_attempts,
            last_login=user.last_login_at.isoformat() if user.last_login_at else None
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user_info
        }
        
    except HTTPException:
        # 重新抛出HTTP异常（如账户锁定等）
        raise
    except Exception as e:
        # 处理其他异常
        print(f"登录过程中发生错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录过程中发生错误"
        )

def get_admin_user(current_user = Depends(verify_token)):
    """验证管理员权限"""
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user

@router.get("/me", response_model=UserInfo)
async def get_current_user_info(current_user = Depends(verify_token)):
    """获取当前用户信息"""
    return UserInfo(
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        is_admin=current_user.is_admin(),
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat() if current_user.created_at else datetime.utcnow().isoformat(),
        failed_login_attempts=current_user.failed_login_attempts,
        last_login=current_user.last_login_at.isoformat() if current_user.last_login_at else None
    )

@router.post("/logout")
async def logout():
    """用户登出"""
    return {"message": "登出成功"}

@router.post("/refresh")
async def refresh_token(credentials: HTTPAuthorizationCredentials = Depends(security), auth_service: AuthService = Depends(get_auth_service)):
    """刷新访问令牌"""
    refresh_token = credentials.credentials
    
    try:
        # 验证refresh token
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if username is None or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 使用AuthService检查用户是否存在
        user = auth_service.get_user_by_username(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 生成新的访问令牌和刷新令牌
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        new_access_token = create_access_token(
            data={"sub": username}, expires_delta=access_token_expires
        )
        new_refresh_token = create_refresh_token(
            data={"sub": username}, expires_delta=refresh_token_expires
        )
        
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user = Depends(verify_token),
    auth_service: AuthService = Depends(get_auth_service)
):
    """修改密码"""
    # 验证当前密码
    if not current_user.verify_password(password_data.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前密码错误"
        )
    
    # 检查新密码长度
    if len(password_data.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新密码至少需要6个字符"
        )
    
    # 检查新密码是否与当前密码相同
    if current_user.verify_password(password_data.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新密码不能与当前密码相同"
        )
    
    # 更新密码
    current_user.set_password(password_data.new_password)
    auth_service.db.commit()
    
    return {"message": "密码修改成功"}

# 邀请码管理API
@router.post("/admin/invitation-codes", status_code=201)
async def create_invitation_code(
    invitation_data: InvitationCodeCreate,
    admin_user = Depends(get_admin_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """创建邀请码"""
    try:
        # 生成唯一邀请码
        code = str(uuid.uuid4()).replace("-", "").upper()[:8]
        
        # 计算过期时间
        expires_at = None
        if hasattr(invitation_data, 'expiration_days') and invitation_data.expiration_days:
            expires_at = datetime.now() + timedelta(days=invitation_data.expiration_days)
        elif hasattr(invitation_data, 'expires_at') and invitation_data.expires_at:
            # 解析ISO格式的日期字符串
            try:
                expires_at = datetime.fromisoformat(invitation_data.expires_at.replace('Z', '+00:00'))
            except:
                expires_at = datetime.now() + timedelta(days=30)
        else:
            # 默认30天后过期
            expires_at = datetime.now() + timedelta(days=30)
        
        # 使用AuthService创建邀请码
        invitation_code = auth_service.create_invitation_code(
            code=code,
            usage_limit=getattr(invitation_data, 'usage_limit', 1),
            expires_at=expires_at,
            description=getattr(invitation_data, 'description', "")
        )
        
        return {
            "id": invitation_code.id,
            "code": invitation_code.code,
            "usage_limit": invitation_code.usage_limit,
            "usage_count": invitation_code.usage_count,
            "expires_at": invitation_code.expires_at.isoformat() if invitation_code.expires_at else None,
            "description": invitation_code.description or "",
            "is_active": invitation_code.is_active,
            "created_at": invitation_code.created_at.isoformat() if invitation_code.created_at else datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"创建邀请码时发生错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建邀请码失败"
        )

# Admin endpoints using database-based authentication
@router.get("/admin/users", response_model=UserListResponse)
async def get_users(
    page: int = 1,
    size: int = 20,
    admin_user = Depends(get_admin_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """获取用户列表（管理员）"""
    try:
        # 获取用户列表和总数
        users, total = auth_service.get_users_paginated(page, size)
        
        # 转换用户数据格式
        user_list = []
        for user in users:
            user_dict = {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "is_admin": user.is_admin(),
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else datetime.utcnow().isoformat(),
                "last_login": user.last_login_at.isoformat() if user.last_login_at else None,
                "failed_login_attempts": user.failed_login_attempts
            }
            user_list.append(user_dict)
        
        # 计算总页数
        total_pages = (total + size - 1) // size
        
        return {
            "items": user_list,
            "total": total,
            "page": page,
            "page_size": size,
            "total_pages": total_pages
        }
        
    except Exception as e:
        print(f"获取用户列表时发生错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户列表失败"
        )

@router.get("/admin/invitation-codes")
async def get_invitation_codes(
    page: int = 1,
    size: int = 20,
    admin_user = Depends(get_admin_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """获取邀请码列表（管理员）"""
    try:
        # 获取邀请码列表和总数
        invitation_codes, total = auth_service.get_invitation_codes_paginated(page, size)
        
        # 转换邀请码数据格式
        codes_list = []
        for code in invitation_codes:
            code_dict = {
                "id": code.id,
                "code": code.code,
                "usage_limit": code.usage_limit,
                "usage_count": code.usage_count,
                "expires_at": code.expires_at.isoformat() if code.expires_at else None,
                "description": code.description or "",
                "is_active": code.is_active,
                "created_at": code.created_at.isoformat() if code.created_at else datetime.utcnow().isoformat()
            }
            codes_list.append(code_dict)
        
        # 计算总页数
        total_pages = (total + size - 1) // size
        
        return {
            "items": codes_list,
            "total": total,
            "page": page,
            "page_size": size,
            "total_pages": total_pages
        }
        
    except Exception as e:
        print(f"获取邀请码列表时发生错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取邀请码列表失败"
        )

@router.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: int,
    admin_user = Depends(get_admin_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """删除用户（管理员）"""
    try:
        # 检查用户是否存在
        user = auth_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # 防止管理员删除自己
        if user.id == admin_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能删除自己的账户"
            )
        
        # 删除用户
        success = auth_service.delete_user(user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="删除用户失败"
            )
        
        return {"message": "用户删除成功"}
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        print(f"删除用户时发生错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除用户失败"
        )

@router.delete("/admin/invitation-codes/{code_id}")
async def delete_invitation_code(
    code_id: int,
    admin_user = Depends(get_admin_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """删除邀请码（管理员）"""
    try:
        # 删除邀请码
        success = auth_service.delete_invitation_code(code_id, admin_user.id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="邀请码不存在"
            )
        
        return {"message": "邀请码删除成功"}
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        print(f"删除邀请码时发生错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除邀请码失败"
        )