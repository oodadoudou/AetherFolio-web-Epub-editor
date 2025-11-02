#!/usr/bin/env python3
"""
数据库初始化脚本
用于创建数据库表结构和初始管理员账户
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from db.connection import DatabaseManager
from db.models.auth import User
from db.repositories.user_repository import UserRepository
from sqlalchemy.exc import IntegrityError

def create_admin_user(db_manager: DatabaseManager, username: str, password: str):
    """
    创建管理员用户
    """
    print(f"正在创建管理员用户: {username}...")
    
    try:
        with db_manager.transaction('auth') as session:
            user_repo = UserRepository(session)
            
            # 检查是否已存在该用户名
            existing_user = user_repo.get_by_username(username)
            if existing_user:
                if existing_user.is_admin():
                    print(f"✓ 管理员用户 {username} 已存在")
                    return existing_user
                else:
                    print(f"✗ 用户名 {username} 已被普通用户使用")
                    return None
            
            # 创建管理员用户
            admin_user = user_repo.create_user(
                username=username,
                password=password,
                role="admin",
                is_active=True
            )
            
            print(f"✓ 管理员用户 {username} 创建成功")
            print(f"  用户ID: {admin_user.id}")
            print(f"  角色: {admin_user.role}")
            print(f"  状态: {'激活' if admin_user.is_active else '未激活'}")
            
            return admin_user
            
    except IntegrityError as e:
        print(f"✗ 创建管理员用户失败 - 数据完整性错误: {e}")
        return None
    except Exception as e:
        print(f"✗ 创建管理员用户失败: {e}")
        return None

def verify_admin_user(db_manager: DatabaseManager, username: str, password: str):
    """
    验证管理员用户
    """
    print(f"正在验证管理员用户: {username}...")
    
    try:
        # 使用生成器方式获取会话
        for session in db_manager.get_session('auth'):
            user_repo = UserRepository(session)
            
            user = user_repo.get_by_username(username)
            if not user:
                print(f"✗ 用户 {username} 不存在")
                return False
            
            if not user.is_admin():
                print(f"✗ 用户 {username} 不是管理员")
                return False
            
            if not user.verify_password(password):
                print(f"✗ 用户 {username} 密码验证失败")
                return False
            
            print(f"✓ 管理员用户 {username} 验证成功")
            return True
            
    except Exception as e:
        print(f"✗ 验证管理员用户失败: {e}")
        return False

def main():
    """
    主函数
    """
    print("=" * 50)
    print("AetherFolio 数据库初始化")
    print("=" * 50)
    
    # 初始化数据库管理器
    try:
        db_manager = DatabaseManager()
        print("数据库连接初始化成功")
        print()
        
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        return False
    
    # 创建数据库表
    try:
        print("正在创建数据库表...")
        db_manager.initialize_default_databases()
        db_manager.create_all_tables('default')
        db_manager.create_all_tables('auth')
        print("✓ 数据库表创建成功")
        print()
        
    except Exception as e:
        print(f"✗ 数据库表创建失败: {e}")
        return False
    
    # 创建管理员用户
    admin_username = "dadoudouoo"
    admin_password = "niwodeyibao"
    
    admin_user = create_admin_user(db_manager, admin_username, admin_password)
    if not admin_user:
        return False
    
    print()
    
    # 验证管理员用户
    if not verify_admin_user(db_manager, admin_username, admin_password):
        return False
    
    print()
    print("=" * 50)
    print("数据库初始化完成!")
    print("=" * 50)
    print(f"管理员账户信息:")
    print(f"  用户名: {admin_username}")
    print(f"  密码: {admin_password}")
    print(f"  角色: 管理员")
    print("=" * 50)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)