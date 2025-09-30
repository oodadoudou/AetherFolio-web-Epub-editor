#!/usr/bin/env python3
"""
Session清理脚本

自动清理一周前的session文件和数据库记录。
可以作为定时任务运行，防止session文件堆积。

使用方法:
    python cleanup_sessions.py [--dry-run] [--days=7]
    
参数:
    --dry-run: 只显示将要删除的文件，不实际删除
    --days: 清理多少天前的session，默认7天
"""

import os
import sys
import argparse
import asyncio
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core.config import settings
from db.connection import get_database
from services.session_service import session_service
from utils.logger import get_logger

logger = get_logger(__name__)


class SessionCleaner:
    """Session清理器"""
    
    def __init__(self, days: int = 7, dry_run: bool = False):
        self.days = days
        self.dry_run = dry_run
        self.cutoff_date = datetime.now() - timedelta(days=days)
        
    async def cleanup_sessions(self) -> Tuple[int, int, int]:
        """清理过期的session
        
        Returns:
            Tuple[int, int, int]: (清理的数据库记录数, 清理的文件目录数, 释放的磁盘空间MB)
        """
        logger.info(f"开始清理 {self.days} 天前的session数据...")
        logger.info(f"截止日期: {self.cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if self.dry_run:
            logger.info("[DRY RUN] 模拟运行，不会实际删除文件")
        
        # 获取过期的session列表
        expired_sessions = await self._get_expired_sessions()
        logger.info(f"找到 {len(expired_sessions)} 个过期session")
        
        if not expired_sessions:
            logger.info("没有需要清理的session")
            return 0, 0, 0
        
        # 清理文件目录
        cleaned_dirs, freed_space_mb = await self._cleanup_session_directories(expired_sessions)
        
        # 清理数据库记录
        cleaned_db_records = await self._cleanup_database_records(expired_sessions)
        
        logger.info(f"清理完成: 数据库记录 {cleaned_db_records} 个, 文件目录 {cleaned_dirs} 个, 释放空间 {freed_space_mb:.2f} MB")
        
        return cleaned_db_records, cleaned_dirs, freed_space_mb
    
    async def _get_expired_sessions(self) -> List[dict]:
        """获取过期的session列表"""
        try:
            # 获取数据库连接
            db = await get_database()
            
            # 查询过期的session
            query = """
                SELECT session_id, created_at, metadata 
                FROM sessions 
                WHERE created_at < ?
                ORDER BY created_at
            """
            
            cursor = await db.execute(query, (self.cutoff_date,))
            rows = await cursor.fetchall()
            
            expired_sessions = []
            for row in rows:
                expired_sessions.append({
                    'session_id': row[0],
                    'created_at': row[1],
                    'metadata': row[2]
                })
            
            return expired_sessions
            
        except Exception as e:
            logger.error(f"获取过期session列表失败: {str(e)}")
            return []
    
    async def _cleanup_session_directories(self, expired_sessions: List[dict]) -> Tuple[int, float]:
        """清理session文件目录
        
        Returns:
            Tuple[int, float]: (清理的目录数, 释放的空间MB)
        """
        cleaned_dirs = 0
        total_freed_space = 0
        
        for session in expired_sessions:
            session_id = session['session_id']
            
            try:
                # 获取session目录路径
                session_dir = await session_service.get_session_directory(session_id)
                
                if session_dir and os.path.exists(session_dir):
                    # 计算目录大小
                    dir_size = self._get_directory_size(session_dir)
                    dir_size_mb = dir_size / (1024 * 1024)
                    
                    logger.info(f"清理session目录: {session_id} ({dir_size_mb:.2f} MB)")
                    
                    if not self.dry_run:
                        # 删除目录
                        shutil.rmtree(session_dir)
                        logger.info(f"已删除session目录: {session_dir}")
                    else:
                        logger.info(f"[DRY RUN] 将删除目录: {session_dir}")
                    
                    cleaned_dirs += 1
                    total_freed_space += dir_size_mb
                else:
                    logger.debug(f"Session目录不存在: {session_id}")
                    
            except Exception as e:
                logger.error(f"清理session目录失败 {session_id}: {str(e)}")
                continue
        
        return cleaned_dirs, total_freed_space
    
    async def _cleanup_database_records(self, expired_sessions: List[dict]) -> int:
        """清理数据库中的session记录
        
        Returns:
            int: 清理的记录数
        """
        if not expired_sessions:
            return 0
        
        try:
            if self.dry_run:
                logger.info(f"[DRY RUN] 将删除 {len(expired_sessions)} 条数据库记录")
                return len(expired_sessions)
            
            # 获取数据库连接
            db = await get_database()
            
            # 批量删除session记录
            session_ids = [session['session_id'] for session in expired_sessions]
            placeholders = ','.join(['?' for _ in session_ids])
            
            query = f"DELETE FROM sessions WHERE session_id IN ({placeholders})"
            cursor = await db.execute(query, session_ids)
            await db.commit()
            
            deleted_count = cursor.rowcount
            logger.info(f"已删除 {deleted_count} 条数据库记录")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"清理数据库记录失败: {str(e)}")
            return 0
    
    def _get_directory_size(self, directory: str) -> int:
        """计算目录大小（字节）"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
        except Exception as e:
            logger.warning(f"计算目录大小失败 {directory}: {str(e)}")
        
        return total_size
    
    async def get_cleanup_statistics(self) -> dict:
        """获取清理统计信息"""
        try:
            # 获取数据库连接
            db = await get_database()
            
            # 统计总session数
            cursor = await db.execute("SELECT COUNT(*) FROM sessions")
            total_sessions = (await cursor.fetchone())[0]
            
            # 统计过期session数
            cursor = await db.execute(
                "SELECT COUNT(*) FROM sessions WHERE created_at < ?", 
                (self.cutoff_date,)
            )
            expired_sessions = (await cursor.fetchone())[0]
            
            # 计算数据目录总大小
            # 使用项目根目录下的data/session
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
            data_dir = os.path.join(project_root, "data", "session")
            total_size_mb = 0
            if os.path.exists(data_dir):
                total_size_mb = self._get_directory_size(data_dir) / (1024 * 1024)
            
            return {
                'total_sessions': total_sessions,
                'expired_sessions': expired_sessions,
                'active_sessions': total_sessions - expired_sessions,
                'total_size_mb': total_size_mb,
                'cutoff_date': self.cutoff_date.strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            return {}


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='清理过期的session文件和数据库记录')
    parser.add_argument('--days', type=int, default=7, help='清理多少天前的session (默认: 7)')
    parser.add_argument('--dry-run', action='store_true', help='只显示将要删除的文件，不实际删除')
    parser.add_argument('--stats', action='store_true', help='只显示统计信息，不执行清理')
    
    args = parser.parse_args()
    
    # 创建清理器
    cleaner = SessionCleaner(days=args.days, dry_run=args.dry_run)
    
    try:
        if args.stats:
            # 只显示统计信息
            stats = await cleaner.get_cleanup_statistics()
            print("\n=== Session统计信息 ===")
            print(f"总session数: {stats.get('total_sessions', 0)}")
            print(f"过期session数: {stats.get('expired_sessions', 0)}")
            print(f"活跃session数: {stats.get('active_sessions', 0)}")
            print(f"数据目录总大小: {stats.get('total_size_mb', 0):.2f} MB")
            print(f"截止日期: {stats.get('cutoff_date', 'N/A')}")
        else:
            # 执行清理
            db_records, dirs, space_mb = await cleaner.cleanup_sessions()
            
            print("\n=== 清理结果 ===")
            print(f"清理的数据库记录: {db_records} 个")
            print(f"清理的文件目录: {dirs} 个")
            print(f"释放的磁盘空间: {space_mb:.2f} MB")
            
            if args.dry_run:
                print("\n注意: 这是模拟运行，没有实际删除文件")
                print("要执行实际清理，请移除 --dry-run 参数")
    
    except Exception as e:
        logger.error(f"清理过程中发生错误: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())