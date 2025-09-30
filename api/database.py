import os
import psycopg2
from urllib.parse import urlparse

def get_db_connection():
    """获取数据库连接"""
    database_url = os.environ.get('POSTGRES_URL')
    if not database_url:
        raise ValueError("POSTGRES_URL environment variable not set")
    
    # 解析数据库 URL
    url = urlparse(database_url)
    
    conn = psycopg2.connect(
        host=url.hostname,
        port=url.port,
        database=url.path[1:],
        user=url.username,
        password=url.password,
        sslmode='require'
    )
    return conn

def execute_query(query, params=None, fetch=False):
    """执行数据库查询"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if fetch:
            result = cursor.fetchall()
            return result
        else:
            conn.commit()
            return cursor.rowcount
    
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def execute_query_one(query, params=None):
    """执行查询并返回单行结果"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        result = cursor.fetchone()
        return result
    
    except Exception as e:
        raise e
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()