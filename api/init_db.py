"""数据库初始化函数 - Vercel Serverless 适配版

为 Vercel serverless 环境提供数据库初始化功能。
"""

import os
import json
from typing import Dict, Any
from database import get_db_connection, execute_query

def handler(request):
    """Vercel serverless 函数入口点
    
    处理数据库初始化请求
    """
    if request.method != 'POST':
        return {
            'statusCode': 405,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Method not allowed'})
        }
    
    try:
        # 解析请求体
        body = json.loads(request.body) if request.body else {}
        action = body.get('action', 'init')
        
        if action == 'init':
            result = initialize_database()
        elif action == 'create_tables':
            result = create_tables()
        elif action == 'seed_data':
            result = seed_initial_data()
        elif action == 'check_status':
            result = check_database_status()
        else:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Invalid action'})
            }
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(result)
        }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }

def initialize_database() -> Dict[str, Any]:
    """初始化数据库
    
    创建所有必要的表和初始数据
    """
    try:
        # 创建表
        create_result = create_tables()
        if not create_result['success']:
            return create_result
        
        # 插入初始数据
        seed_result = seed_initial_data()
        if not seed_result['success']:
            return seed_result
        
        return {
            'success': True,
            'message': '数据库初始化成功',
            'tables_created': create_result.get('tables_created', []),
            'data_seeded': seed_result.get('data_seeded', [])
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': f'数据库初始化失败: {str(e)}'
        }

def create_tables() -> Dict[str, Any]:
    """创建数据库表"""
    tables_created = []
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 用户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) DEFAULT 'user',
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        tables_created.append('users')
        
        # 用户会话表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                session_token VARCHAR(255) UNIQUE NOT NULL,
                refresh_token VARCHAR(255) UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        tables_created.append('user_sessions')
        
        # 邀请码表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invitation_codes (
                id SERIAL PRIMARY KEY,
                code VARCHAR(50) UNIQUE NOT NULL,
                created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                used_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                expires_at TIMESTAMP,
                is_used BOOLEAN DEFAULT false,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        tables_created.append('invitation_codes')
        
        # 审计日志表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                action VARCHAR(100) NOT NULL,
                resource_type VARCHAR(50),
                resource_id VARCHAR(100),
                details JSONB,
                ip_address INET,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        tables_created.append('audit_logs')
        
        # 系统配置表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_configs (
                id SERIAL PRIMARY KEY,
                key VARCHAR(100) UNIQUE NOT NULL,
                value TEXT,
                value_type VARCHAR(20) DEFAULT 'string',
                description TEXT,
                category VARCHAR(50) DEFAULT 'general',
                is_public BOOLEAN DEFAULT false,
                is_editable BOOLEAN DEFAULT true,
                default_value TEXT,
                validation_rules JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        tables_created.append('system_configs')
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invitation_codes_code ON invitation_codes(code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_system_configs_key ON system_configs(key)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_system_configs_category ON system_configs(category)")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            'success': True,
            'message': '数据库表创建成功',
            'tables_created': tables_created
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': f'创建数据库表失败: {str(e)}'
        }

def seed_initial_data() -> Dict[str, Any]:
    """插入初始数据"""
    data_seeded = []
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查是否已有管理员用户
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = cursor.fetchone()[0]
        
        if admin_count == 0:
            # 创建默认管理员账户
            import bcrypt
            password_hash = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role)
                VALUES (%s, %s, %s, %s)
            """, ('admin', 'admin@aetherfolio.com', password_hash, 'admin'))
            data_seeded.append('admin_user')
        
        # 插入默认系统配置
        default_configs = [
            ('app_name', 'AetherFolio', 'string', '应用名称', 'general', True),
            ('app_version', '1.0.0', 'string', '应用版本', 'general', True),
            ('max_file_size', '10485760', 'integer', '最大文件大小(字节)', 'upload', False),
            ('allowed_file_types', '["epub", "txt", "md"]', 'json', '允许的文件类型', 'upload', False),
            ('session_timeout', '86400', 'integer', '会话超时时间(秒)', 'auth', False),
            ('enable_registration', 'false', 'boolean', '是否开放注册', 'auth', False),
            ('require_invitation', 'true', 'boolean', '是否需要邀请码', 'auth', False)
        ]
        
        for key, value, value_type, description, category, is_public in default_configs:
            cursor.execute("""
                INSERT INTO system_configs (key, value, value_type, description, category, is_public, default_value)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (key) DO NOTHING
            """, (key, value, value_type, description, category, is_public, value))
        
        data_seeded.append('system_configs')
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            'success': True,
            'message': '初始数据插入成功',
            'data_seeded': data_seeded
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': f'插入初始数据失败: {str(e)}'
        }

def check_database_status() -> Dict[str, Any]:
    """检查数据库状态"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        # 检查用户数量
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        # 检查管理员是否存在
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return {
            'success': True,
            'database_connected': True,
            'tables': tables,
            'user_count': user_count,
            'admin_exists': admin_count > 0,
            'status': 'healthy'
        }
    
    except Exception as e:
        return {
            'success': False,
            'database_connected': False,
            'error': str(e),
            'status': 'error'
        }