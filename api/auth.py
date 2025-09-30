from http.server import BaseHTTPRequestHandler
import json
import os
from datetime import datetime, timedelta
from jose import JWTError, jwt
import hashlib
from typing import Optional
from database import get_db_connection, execute_query, execute_query_one

# 配置
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

def hash_password(password: str) -> str:
    """哈希密码"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
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

def verify_token(token: str):
    """验证访问令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError:
        return None

def get_user_by_username(username: str):
    """根据用户名获取用户"""
    query = "SELECT id, username, password_hash, role, is_active, created_at, last_login_at, failed_login_attempts FROM users WHERE username = %s"
    return execute_query_one(query, (username,))

def authenticate_user(username: str, password: str):
    """用户认证"""
    user = get_user_by_username(username)
    if not user:
        return None
    
    # 验证密码
    if not verify_password(password, user['password_hash']):
        return None
    
    # 更新最后登录时间
    update_query = "UPDATE users SET last_login_at = %s WHERE id = %s"
    execute_query(update_query, (datetime.utcnow(), user['id']))
    
    return user

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # 解析请求路径
            path = self.path.split('/')[-1]  # 获取最后一部分作为操作类型
            
            # 读取请求体
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                body = self.rfile.read(content_length)
                data = json.loads(body.decode('utf-8'))
            else:
                data = {}
            
            if path == 'login':
                self.handle_login(data)
            elif path == 'refresh':
                self.handle_refresh(data)
            elif path == 'logout':
                self.handle_logout()
            else:
                self.send_error_response(404, "Not Found")
                
        except Exception as e:
            print(f"Error in auth handler: {e}")
            self.send_error_response(500, "Internal Server Error")
    
    def do_GET(self):
        try:
            path = self.path.split('/')[-1]
            
            if path == 'me':
                self.handle_get_current_user()
            else:
                self.send_error_response(404, "Not Found")
                
        except Exception as e:
            print(f"Error in auth GET handler: {e}")
            self.send_error_response(500, "Internal Server Error")
    
    def handle_login(self, data):
        """处理登录请求"""
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            self.send_error_response(400, "用户名和密码不能为空")
            return
        
        # 认证用户
        user = authenticate_user(username, password)
        if not user:
            self.send_error_response(401, "用户名或密码错误")
            return
        
        # 创建令牌
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        access_token = create_access_token(
            data={"sub": user['username']}, expires_delta=access_token_expires
        )
        refresh_token = create_refresh_token(
            data={"sub": user['username']}, expires_delta=refresh_token_expires
        )
        
        # 构建用户信息
        user_info = {
            "user_id": user['id'],
            "username": user['username'],
            "role": user['role'],
            "is_admin": user['role'] == 'admin',
            "is_active": user['is_active'],
            "created_at": user['created_at'].isoformat() if user['created_at'] else None,
            "failed_login_attempts": user['failed_login_attempts'] or 0,
            "last_login": user['last_login_at'].isoformat() if user['last_login_at'] else None
        }
        
        response_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user_info
        }
        
        self.send_json_response(200, response_data)
    
    def handle_refresh(self, data):
        """处理令牌刷新请求"""
        # 从Authorization header获取token
        auth_header = self.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            self.send_error_response(401, "缺少Authorization header")
            return
        
        refresh_token = auth_header[7:]  # 移除 'Bearer ' 前缀
        
        try:
            # 验证refresh token
            payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            token_type = payload.get("type")
            
            if username is None or token_type != "refresh":
                self.send_error_response(401, "无效的刷新令牌")
                return
            
            # 检查用户是否存在
            user = get_user_by_username(username)
            if not user:
                self.send_error_response(401, "用户不存在")
                return
            
            # 生成新的令牌
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
            
            new_access_token = create_access_token(
                data={"sub": username}, expires_delta=access_token_expires
            )
            new_refresh_token = create_refresh_token(
                data={"sub": username}, expires_delta=refresh_token_expires
            )
            
            response_data = {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer"
            }
            
            self.send_json_response(200, response_data)
            
        except JWTError:
            self.send_error_response(401, "无效的刷新令牌")
    
    def handle_logout(self):
        """处理登出请求"""
        self.send_json_response(200, {"message": "登出成功"})
    
    def handle_get_current_user(self):
        """获取当前用户信息"""
        # 从Authorization header获取token
        auth_header = self.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            self.send_error_response(401, "缺少Authorization header")
            return
        
        token = auth_header[7:]  # 移除 'Bearer ' 前缀
        username = verify_token(token)
        
        if not username:
            self.send_error_response(401, "无效的令牌")
            return
        
        user = get_user_by_username(username)
        if not user:
            self.send_error_response(401, "用户不存在")
            return
        
        user_info = {
            "user_id": user['id'],
            "username": user['username'],
            "role": user['role'],
            "is_admin": user['role'] == 'admin',
            "is_active": user['is_active'],
            "created_at": user['created_at'].isoformat() if user['created_at'] else None,
            "failed_login_attempts": user['failed_login_attempts'] or 0,
            "last_login": user['last_login_at'].isoformat() if user['last_login_at'] else None
        }
        
        self.send_json_response(200, user_info)
    
    def send_json_response(self, status_code, data):
        """发送JSON响应"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        
        response_json = json.dumps(data, ensure_ascii=False, default=str)
        self.wfile.write(response_json.encode('utf-8'))
    
    def send_error_response(self, status_code, message):
        """发送错误响应"""
        self.send_json_response(status_code, {"detail": message})
    
    def do_OPTIONS(self):
        """处理CORS预检请求"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()