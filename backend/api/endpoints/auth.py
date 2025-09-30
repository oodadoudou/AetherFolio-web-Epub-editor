"""认证相关的API端点"""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
import hashlib
import secrets
import uuid
import random
import string

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
    users: List[dict]
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

# 简化的内存存储（仅用于测试）
users_db = {}
invitation_codes = {}

# 从数据库加载数据到内存
def load_data_from_database():
    """从数据库加载用户和邀请码数据到内存"""
    import sqlite3
    import os
    
    # 尝试从主数据库加载
    db_path = "db/data/auth.db"
    if not os.path.exists(db_path):
        # 如果主数据库不存在，使用默认数据
        invitation_codes["WELCOME2024"] = {
            "id": 1,
            "code": "WELCOME2024",
            "usage_limit": 100,
            "usage_count": 0,
            "expires_at": "2024-12-31T23:59:59",
            "description": "Default welcome code",
            "is_active": True,
            "created_at": "2024-01-01T00:00:00"
        }
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 加载用户数据
        cursor.execute("SELECT id, username, password, role FROM users")
        users = cursor.fetchall()
        for user_id, username, password, role in users:
            users_db[username] = {
                "id": user_id,
                "username": username,
                "password": password,  # 已经是哈希后的密码
                "role": role,
                "created_at": datetime.utcnow()
            }
        
        # 加载邀请码数据
        cursor.execute("SELECT id, code, usage_limit, usage_count, expires_at, description, is_active FROM invitation_codes")
        codes = cursor.fetchall()
        for code_id, code, usage_limit, usage_count, expires_at, description, is_active in codes:
            invitation_codes[code] = {
                "id": code_id,
                "code": code,
                "usage_limit": usage_limit,
                "usage_count": usage_count,
                "expires_at": expires_at or "2024-12-31T23:59:59",
                "description": description or "",
                "is_active": bool(is_active),
                "created_at": "2024-01-01T00:00:00"
            }
        
        conn.close()
        print(f"从数据库加载了 {len(users_db)} 个用户和 {len(invitation_codes)} 个邀请码")
        
    except Exception as e:
        print(f"从数据库加载数据失败: {e}")
        # 使用默认数据
        invitation_codes["WELCOME2024"] = {
            "id": 1,
            "code": "WELCOME2024",
            "usage_limit": 100,
            "usage_count": 0,
            "expires_at": "2024-12-31T23:59:59",
            "description": "Default welcome code",
            "is_active": True,
            "created_at": "2024-01-01T00:00:00"
        }

# 初始化时加载数据
load_data_from_database()

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

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
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
        user = users_db.get(username)
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
async def register(user_data: UserCreate):
    """用户注册"""
    # 验证邀请码
    if user_data.invitation_code not in invitation_codes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的邀请码"
        )
    
    invitation_code_data = invitation_codes[user_data.invitation_code]
    
    # 检查邀请码是否有效
    if not invitation_code_data["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邀请码已失效"
        )
    
    # 检查使用次数限制
    if invitation_code_data["usage_count"] >= invitation_code_data["usage_limit"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邀请码使用次数已达上限"
        )
    
    # 检查过期时间
    expires_at = datetime.fromisoformat(invitation_code_data["expires_at"].replace("Z", "+00:00"))
    if datetime.now() > expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邀请码已过期"
        )
    
    # 检查用户是否已存在
    if user_data.username in users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已被注册"
        )
    
    # 生成随机6位用户ID
    def generate_user_id():
        while True:
            user_id = ''.join(random.choices(string.digits, k=6))
            # 确保ID不重复
            if not any(user.get('id') == user_id for user in users_db.values()):
                return user_id
    
    # 创建用户
    user_id = generate_user_id()
    users_db[user_data.username] = {
        "id": user_id,
        "username": user_data.username,
        "password": hash_password(user_data.password),
        "role": "user",
        "created_at": datetime.utcnow()
    }
    
    # 更新邀请码使用次数
    invitation_codes[user_data.invitation_code]["usage_count"] += 1
    
    # 创建访问令牌和刷新令牌
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    access_token = create_access_token(
        data={"sub": user_data.username}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": user_data.username}, expires_delta=refresh_token_expires
    )
    
    # 构建用户信息
    user_info = UserInfo(
        user_id=users_db[user_data.username]["id"],
        username=users_db[user_data.username]["username"],
        role=users_db[user_data.username].get("role", "user"),
        is_admin=users_db[user_data.username].get("role") == "admin",
        is_active=True,
        created_at=users_db[user_data.username].get("created_at", datetime.utcnow()).isoformat() if isinstance(users_db[user_data.username].get("created_at"), datetime) else str(users_db[user_data.username].get("created_at", "")),
        failed_login_attempts=0
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user_info
    }

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin):
    """用户登录"""
    username = user_data.username
    current_time = datetime.utcnow()
    
    # 检查账户是否被锁定
    if username in failed_login_attempts:
        attempt_data = failed_login_attempts[username]
        if "locked_until" in attempt_data and current_time < attempt_data["locked_until"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"账户已被锁定，请在{attempt_data['locked_until'].strftime('%Y-%m-%d %H:%M:%S')}后重试",
            )
    
    # 验证用户
    user = users_db.get(username)
    if not user or not verify_password(user_data.password, user["password"]):
        # 记录失败尝试
        if username not in failed_login_attempts:
            failed_login_attempts[username] = {"count": 0, "last_attempt": current_time}
        
        failed_login_attempts[username]["count"] += 1
        failed_login_attempts[username]["last_attempt"] = current_time
        
        # 检查是否需要锁定账户
        if failed_login_attempts[username]["count"] >= MAX_FAILED_ATTEMPTS:
            failed_login_attempts[username]["locked_until"] = current_time + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"登录失败次数过多，账户已被锁定{LOCKOUT_DURATION_MINUTES}分钟",
            )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 登录成功，清除失败记录
    if username in failed_login_attempts:
        del failed_login_attempts[username]
    
    # 创建访问令牌和刷新令牌
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    access_token = create_access_token(
        data={"sub": user_data.username}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": user_data.username}, expires_delta=refresh_token_expires
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

def get_admin_user(current_user: dict = Depends(verify_token)):
    """验证管理员权限"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user

@router.get("/me", response_model=UserInfo)
async def get_current_user_info(current_user: dict = Depends(verify_token)):
    """获取当前用户信息"""
    return UserInfo(
        user_id=current_user["id"],
        username=current_user["username"],
        role=current_user.get("role", "user"),
        is_admin=current_user.get("role") == "admin",
        is_active=True,
        created_at=current_user.get("created_at", datetime.utcnow()).isoformat() if isinstance(current_user.get("created_at"), datetime) else str(current_user.get("created_at", "")),
        failed_login_attempts=0
    )

@router.post("/logout")
async def logout():
    """用户登出"""
    return {"message": "登出成功"}

@router.post("/refresh")
async def refresh_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
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
        
        # 检查用户是否存在
        if username not in users_db:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = users_db[username]
        
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
    current_user: dict = Depends(verify_token)
):
    """修改密码"""
    # 验证当前密码
    if not verify_password(password_data.current_password, current_user["password"]):
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
    if verify_password(password_data.new_password, current_user["password"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新密码不能与当前密码相同"
        )
    
    # 更新密码
    username = current_user["username"]
    users_db[username]["password"] = hash_password(password_data.new_password)
    
    return {"message": "密码修改成功"}

# 邀请码管理API
@router.post("/admin/invitation-codes", status_code=201)
async def create_invitation_code(
    invitation_data: InvitationCodeCreate,
    admin_user: dict = Depends(get_admin_user)
):
    """创建邀请码"""
    global invitation_code_counter
    
    # 生成唯一邀请码
    code = str(uuid.uuid4()).replace("-", "").upper()[:8]
    
    # 计算过期时间
    if hasattr(invitation_data, 'expiration_days') and invitation_data.expiration_days:
        expires_at = (datetime.now() + timedelta(days=invitation_data.expiration_days)).isoformat()
    elif hasattr(invitation_data, 'expires_at') and invitation_data.expires_at:
        expires_at = invitation_data.expires_at
    else:
        # 默认30天后过期
        expires_at = (datetime.now() + timedelta(days=30)).isoformat()
    
    invitation_code = {
        "id": invitation_code_counter,
        "code": code,
        "usage_limit": getattr(invitation_data, 'usage_limit', 1),
        "usage_count": 0,
        "expires_at": expires_at,
        "description": getattr(invitation_data, 'description', ""),
        "is_active": True,
        "created_at": datetime.now().isoformat()
    }
    
    invitation_codes[code] = invitation_code
    invitation_code_counter += 1
    
    return invitation_code

@router.get("/admin/users")
async def get_users(
    page: int = 1,
    size: int = 20,
    admin_user: dict = Depends(get_admin_user)
):
    """获取用户列表（分页）"""
    # 获取所有用户
    all_users = []
    seen_ids = set()  # 用于跟踪已经处理过的用户ID
    
    for username, user_data in users_db.items():
        # 确保用户ID唯一
        user_id = user_data["id"]
        if user_id in seen_ids:
            # 如果ID已存在，生成一个新的唯一ID
            user_id = max(seen_ids) + 1 if seen_ids else 1
        
        seen_ids.add(user_id)
        
        user_info = {
            "id": user_id,
            "username": user_data["username"],
            "role": user_data.get("role", "user"),
            "created_at": user_data.get("created_at", datetime.utcnow()).isoformat() if isinstance(user_data.get("created_at"), datetime) else str(user_data.get("created_at", "")),
            "last_login": user_data.get("last_login", None)
        }
        all_users.append(user_info)
    
    total = len(all_users)
    
    # 计算分页
    start_index = (page - 1) * size
    end_index = start_index + size
    items = all_users[start_index:end_index]
    
    # 计算总页数
    pages = (total + size - 1) // size if total > 0 else 1
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages
    }

@router.get("/admin/users/stats")
async def get_user_stats(
    admin_user: dict = Depends(get_admin_user)
):
    """获取用户统计信息"""
    total = len(users_db)
    
    return {
        "total": total
    }

@router.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: str,
    admin_user: dict = Depends(get_admin_user)
):
    """删除用户"""
    # 查找用户
    target_user = None
    target_username = None
    for username, user_data in users_db.items():
        if str(user_data["id"]) == str(user_id):
            target_user = user_data
            target_username = username
            break
    
    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 不能删除管理员账户
    if target_user.get("role") == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除管理员账户"
        )
    
    # 不能删除自己
    if target_username == admin_user["username"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己的账户"
        )
    
    # 删除用户
    del users_db[target_username]
    
    return {
        "message": "用户删除成功",
        "user_id": user_id
    }

@router.get("/admin/invitation-codes")
async def get_invitation_codes(
    page: int = 1,
    size: int = 20,
    admin_user: dict = Depends(get_admin_user)
):
    """获取邀请码列表（分页）"""
    # 获取所有邀请码
    all_codes = list(invitation_codes.values())
    total = len(all_codes)
    
    # 计算分页
    start_index = (page - 1) * size
    end_index = start_index + size
    items = all_codes[start_index:end_index]
    
    # 计算总页数
    pages = (total + size - 1) // size if total > 0 else 1
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages
    }

@router.delete("/admin/invitation-codes/{code_id}")
async def delete_invitation_code(
    code_id: int,
    admin_user: dict = Depends(get_admin_user)
):
    """删除邀请码"""
    # 查找要删除的邀请码
    code_to_delete = None
    for code, data in invitation_codes.items():
        if data["id"] == code_id:
            code_to_delete = code
            break
    
    if code_to_delete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="邀请码不存在"
        )
    
    # 删除邀请码
    del invitation_codes[code_to_delete]
    
    return {"message": "邀请码删除成功"}

@router.post("/admin/reload-data")
async def reload_data_from_database(admin_user: dict = Depends(get_admin_user)):
    """重新从数据库加载用户和邀请码数据"""
    global users_db, invitation_codes
    
    # 清空现有数据
    users_db.clear()
    invitation_codes.clear()
    
    # 重新加载数据
    load_data_from_database()
    
    return {
        "message": "数据重新加载成功",
        "users_count": len(users_db),
        "invitation_codes_count": len(invitation_codes)
    }

# 初始化默认用户
def init_default_users():
    """初始化默认用户"""
    if "test_user" not in users_db:
        users_db["test_user"] = {
            "id": 1,
            "username": "test_user",
            "password": hash_password("test123456"),
            "role": "user",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "last_login": None
        }
    
    if "admin" not in users_db:
        users_db["admin"] = {
            "id": 2,
            "username": "admin",
            "password": hash_password("admin123456"),
            "role": "admin",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "last_login": None
        }



# 初始化默认用户
init_default_users()