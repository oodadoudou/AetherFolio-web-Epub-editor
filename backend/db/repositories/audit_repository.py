"""审计日志数据访问仓储"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from datetime import datetime, timedelta

from .base import BaseRepository
from ..models.auth import AuditLog

class AuditRepository(BaseRepository[AuditLog]):
    """审计日志仓储类"""
    
    def __init__(self, session: Session):
        super().__init__(session, AuditLog)
    
    def create_log(
        self,
        action: str,
        user_id: int = None,
        resource_type: str = None,
        resource_id: str = None,
        details: Dict[str, Any] = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> AuditLog:
        """创建审计日志
        
        Args:
            action: 操作类型
            user_id: 用户ID
            resource_type: 资源类型
            resource_id: 资源ID
            details: 详细信息
            ip_address: IP地址
            user_agent: 用户代理
            
        Returns:
            AuditLog: 创建的审计日志实例
        """
        audit_log = AuditLog.create_log(
            action=action,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.session.add(audit_log)
        self.session.commit()
        self.session.refresh(audit_log)
        
        return audit_log
    
    def get_user_logs(
        self,
        user_id: int,
        limit: int = 100,
        offset: int = 0,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> List[AuditLog]:
        """获取用户的审计日志
        
        Args:
            user_id: 用户ID
            limit: 限制数量
            offset: 偏移量
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            List[AuditLog]: 审计日志列表
        """
        query = (
            self.session.query(AuditLog)
            .filter(AuditLog.user_id == user_id)
            .order_by(desc(AuditLog.created_at))
        )
        
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)
        
        return query.offset(offset).limit(limit).all()
    
    def get_logs_by_action(
        self,
        action: str,
        limit: int = 100,
        offset: int = 0,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> List[AuditLog]:
        """根据操作类型获取审计日志
        
        Args:
            action: 操作类型
            limit: 限制数量
            offset: 偏移量
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            List[AuditLog]: 审计日志列表
        """
        query = (
            self.session.query(AuditLog)
            .filter(AuditLog.action == action)
            .order_by(desc(AuditLog.created_at))
        )
        
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)
        
        return query.offset(offset).limit(limit).all()
    
    def get_logs_by_resource(
        self,
        resource_type: str,
        resource_id: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """根据资源获取审计日志
        
        Args:
            resource_type: 资源类型
            resource_id: 资源ID（可选）
            limit: 限制数量
            offset: 偏移量
            
        Returns:
            List[AuditLog]: 审计日志列表
        """
        query = (
            self.session.query(AuditLog)
            .filter(AuditLog.resource_type == resource_type)
            .order_by(desc(AuditLog.created_at))
        )
        
        if resource_id:
            query = query.filter(AuditLog.resource_id == resource_id)
        
        return query.offset(offset).limit(limit).all()
    
    def get_logs_by_ip(
        self,
        ip_address: str,
        limit: int = 100,
        offset: int = 0,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> List[AuditLog]:
        """根据IP地址获取审计日志
        
        Args:
            ip_address: IP地址
            limit: 限制数量
            offset: 偏移量
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            List[AuditLog]: 审计日志列表
        """
        query = (
            self.session.query(AuditLog)
            .filter(AuditLog.ip_address == ip_address)
            .order_by(desc(AuditLog.created_at))
        )
        
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)
        
        return query.offset(offset).limit(limit).all()
    
    def get_recent_logs(
        self,
        hours: int = 24,
        limit: int = 100
    ) -> List[AuditLog]:
        """获取最近的审计日志
        
        Args:
            hours: 最近小时数
            limit: 限制数量
            
        Returns:
            List[AuditLog]: 审计日志列表
        """
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        return (
            self.session.query(AuditLog)
            .filter(AuditLog.created_at >= start_time)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
            .all()
        )
    
    def search_logs(
        self,
        search_term: str,
        search_fields: List[str] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """搜索审计日志
        
        Args:
            search_term: 搜索词
            search_fields: 搜索字段列表
            limit: 限制数量
            
        Returns:
            List[AuditLog]: 搜索结果
        """
        if not search_fields:
            search_fields = ['action', 'resource_type', 'resource_id']
        
        return self.search(search_term, search_fields, limit)
    
    def get_action_stats(
        self,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict[str, int]:
        """获取操作统计
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Dict[str, int]: 操作统计字典
        """
        query = self.session.query(AuditLog.action, self.session.query(AuditLog).filter(AuditLog.action == AuditLog.action).count().label('count'))
        
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)
        
        # 使用原生SQL进行分组统计
        from sqlalchemy import text
        
        sql = """
        SELECT action, COUNT(*) as count
        FROM audit_logs
        WHERE 1=1
        """
        
        params = {}
        
        if start_date:
            sql += " AND created_at >= :start_date"
            params['start_date'] = start_date
        
        if end_date:
            sql += " AND created_at <= :end_date"
            params['end_date'] = end_date
        
        sql += " GROUP BY action ORDER BY count DESC"
        
        result = self.session.execute(text(sql), params)
        
        return {row.action: row.count for row in result}
    
    def get_user_activity_stats(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取用户活动统计
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            limit: 限制数量
            
        Returns:
            List[Dict[str, Any]]: 用户活动统计列表
        """
        from sqlalchemy import text, func
        
        sql = """
        SELECT 
            al.user_id,
            u.username,
            COUNT(*) as activity_count,
            COUNT(DISTINCT al.action) as unique_actions,
            MAX(al.created_at) as last_activity
        FROM audit_logs al
        LEFT JOIN users u ON al.user_id = u.id
        WHERE al.user_id IS NOT NULL
        """
        
        params = {}
        
        if start_date:
            sql += " AND al.created_at >= :start_date"
            params['start_date'] = start_date
        
        if end_date:
            sql += " AND al.created_at <= :end_date"
            params['end_date'] = end_date
        
        sql += """
        GROUP BY al.user_id, u.username
        ORDER BY activity_count DESC
        LIMIT :limit
        """
        
        params['limit'] = limit
        
        result = self.session.execute(text(sql), params)
        
        return [
            {
                'user_id': row.user_id,
                'username': row.username,
                'activity_count': row.activity_count,
                'unique_actions': row.unique_actions,
                'last_activity': row.last_activity
            }
            for row in result
        ]
    
    def cleanup_old_logs(self, days: int = 90) -> int:
        """清理旧的审计日志
        
        Args:
            days: 保留天数
            
        Returns:
            int: 清理的日志数量
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        old_logs = (
            self.session.query(AuditLog)
            .filter(AuditLog.created_at < cutoff_date)
            .all()
        )
        
        count = len(old_logs)
        
        for log in old_logs:
            self.session.delete(log)
        
        self.session.commit()
        return count
    
    def get_security_events(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """获取安全相关事件
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            limit: 限制数量
            
        Returns:
            List[AuditLog]: 安全事件列表
        """
        security_actions = [
            'login_failed',
            'login_success',
            'logout',
            'password_change',
            'account_locked',
            'account_unlocked',
            'permission_denied',
            'admin_action'
        ]
        
        query = (
            self.session.query(AuditLog)
            .filter(AuditLog.action.in_(security_actions))
            .order_by(desc(AuditLog.created_at))
        )
        
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)
        
        return query.limit(limit).all()
    
    def get_failed_login_attempts(
        self,
        hours: int = 24,
        ip_address: str = None
    ) -> List[AuditLog]:
        """获取失败的登录尝试
        
        Args:
            hours: 最近小时数
            ip_address: IP地址（可选）
            
        Returns:
            List[AuditLog]: 失败登录尝试列表
        """
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        query = (
            self.session.query(AuditLog)
            .filter(AuditLog.action == 'login_failed')
            .filter(AuditLog.created_at >= start_time)
            .order_by(desc(AuditLog.created_at))
        )
        
        if ip_address:
            query = query.filter(AuditLog.ip_address == ip_address)
        
        return query.all()