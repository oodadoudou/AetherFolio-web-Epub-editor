"""数据库连接管理

统一管理数据库连接、会话和事务。
"""

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator, Dict, Optional
import os
from contextlib import contextmanager
from pathlib import Path

class DatabaseManager:
    """数据库管理器
    
    统一管理多个数据库连接和会话。
    """
    
    def __init__(self):
        self.engines: Dict[str, Engine] = {}
        self.session_factories: Dict[str, sessionmaker] = {}
        self._initialized = False
    
    def add_database(self, name: str, url: str, **kwargs) -> None:
        """添加数据库连接
        
        Args:
            name: 数据库名称
            url: 数据库连接URL
            **kwargs: 额外的引擎参数
        """
        # SQLite特殊配置
        if url.startswith("sqlite"):
            kwargs.setdefault("connect_args", {"check_same_thread": False})
            kwargs.setdefault("echo", False)
        
        engine = create_engine(url, **kwargs)
        self.engines[name] = engine
        self.session_factories[name] = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine
        )
    
    def get_engine(self, name: str = 'default') -> Engine:
        """获取数据库引擎"""
        if name not in self.engines:
            raise ValueError(f"数据库 '{name}' 未配置")
        return self.engines[name]
    
    def get_session(self, name: str = 'default') -> Generator[Session, None, None]:
        """获取数据库会话
        
        Args:
            name: 数据库名称
            
        Yields:
            Session: 数据库会话
        """
        if name not in self.session_factories:
            raise ValueError(f"数据库 '{name}' 未配置")
        
        session_factory = self.session_factories[name]
        session = session_factory()
        try:
            yield session
        finally:
            session.close()
    
    @contextmanager
    def transaction(self, name: str = 'default'):
        """事务管理上下文
        
        Args:
            name: 数据库名称
            
        Yields:
            Session: 数据库会话（在事务中）
        """
        if name not in self.session_factories:
            raise ValueError(f"数据库 '{name}' 未配置")
        
        session_factory = self.session_factories[name]
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def create_all_tables(self, name: str = 'default') -> None:
        """创建所有表
        
        Args:
            name: 数据库名称
        """
        from .base import Base
        
        engine = self.get_engine(name)
        Base.metadata.create_all(bind=engine)
    
    def drop_all_tables(self, name: str = 'default') -> None:
        """删除所有表
        
        Args:
            name: 数据库名称
        """
        from .base import Base
        
        engine = self.get_engine(name)
        Base.metadata.drop_all(bind=engine)
    
    def initialize_default_databases(self) -> None:
        """初始化默认数据库配置"""
        if self._initialized:
            return
        
        # 确保数据目录存在
        data_dir = Path("db/data")
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # 主数据库
        main_db_url = os.getenv(
            "DATABASE_URL",
            "sqlite:///./db/data/aetherfolio.db"
        )
        self.add_database('default', main_db_url)
        
        # 认证数据库
        auth_db_url = os.getenv(
            "AUTH_DATABASE_URL",
            "sqlite:///./db/data/auth.db"
        )
        self.add_database('auth', auth_db_url)
        
        self._initialized = True

# 全局数据库管理器实例
db_manager = DatabaseManager()

# 兼容性函数
def get_db() -> Generator[Session, None, None]:
    """获取默认数据库会话（兼容性函数）
    
    这个函数保持与原有代码的兼容性。
    
    Yields:
        Session: 数据库会话
    """
    # 确保数据库已初始化
    if not db_manager._initialized:
        db_manager.initialize_default_databases()
    
    yield from db_manager.get_session('default')

def get_auth_db() -> Generator[Session, None, None]:
    """获取认证数据库会话
    
    Yields:
        Session: 认证数据库会话
    """
    # 确保数据库已初始化
    if not db_manager._initialized:
        db_manager.initialize_default_databases()
    
    yield from db_manager.get_session('auth')

def create_tables(db_name: str = 'default') -> None:
    """创建数据库表（兼容性函数）
    
    Args:
        db_name: 数据库名称
    """
    # 确保数据库已初始化
    if not db_manager._initialized:
        db_manager.initialize_default_databases()
    
    # 导入所有模型以确保它们被注册
    try:
        from .models.auth import User, InvitationCode, UserSession, AuditLog
        from .models.config import SystemConfig
    except ImportError:
        pass
    
    db_manager.create_all_tables(db_name)

def init_database() -> None:
    """初始化数据库（兼容性函数）"""
    # 确保数据库已初始化
    if not db_manager._initialized:
        db_manager.initialize_default_databases()
    
    # 创建表
    create_tables('default')
    create_tables('auth')
    
    # 创建默认管理员账户（如果不存在）
    with db_manager.transaction('default') as db:
        try:
            from .models.auth import User
            from services.auth_service import AuthService
            
            # 检查是否已有管理员账户
            admin_exists = db.query(User).filter(User.role == "admin").first()
            if not admin_exists:
                auth_service = AuthService(db, "your-secret-key")
                try:
                    admin_user = auth_service.create_admin_user("admin", "admin123")
                    print(f"默认管理员账户已创建: {admin_user.username}")
                    print("默认密码: admin123")
                    print("请登录后立即修改密码！")
                except Exception as e:
                    print(f"创建管理员账户失败: {e}")
        except Exception as e:
            print(f"初始化管理员账户时出错: {e}")

# 初始化默认数据库配置
db_manager.initialize_default_databases()