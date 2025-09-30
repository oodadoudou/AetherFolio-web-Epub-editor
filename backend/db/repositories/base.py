"""基础仓储类

提供通用的数据访问操作。
"""

from typing import TypeVar, Generic, List, Optional, Dict, Any, Type
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, desc, asc

from ..base import BaseModel

T = TypeVar('T', bound=BaseModel)

class BaseRepository(Generic[T]):
    """基础仓储类
    
    提供通用的CRUD操作和查询方法。
    """
    
    def __init__(self, session: Session, model: Type[T]):
        """初始化仓储
        
        Args:
            session: 数据库会话
            model: 数据模型类
        """
        self.session = session
        self.model = model
    
    def create(self, **kwargs) -> T:
        """创建记录
        
        Args:
            **kwargs: 模型字段值
            
        Returns:
            T: 创建的模型实例
            
        Raises:
            IntegrityError: 数据完整性错误
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        try:
            self.session.commit()
            self.session.refresh(instance)
            return instance
        except IntegrityError:
            self.session.rollback()
            raise
    
    def get_by_id(self, id: int) -> Optional[T]:
        """根据ID获取记录
        
        Args:
            id: 记录ID
            
        Returns:
            Optional[T]: 模型实例或None
        """
        return self.session.query(self.model).filter(self.model.id == id).first()
    
    def get_by_ids(self, ids: List[int]) -> List[T]:
        """根据ID列表获取记录
        
        Args:
            ids: ID列表
            
        Returns:
            List[T]: 模型实例列表
        """
        return self.session.query(self.model).filter(self.model.id.in_(ids)).all()
    
    def get_all(
        self, 
        limit: int = 100, 
        offset: int = 0, 
        order_by: str = None,
        desc_order: bool = False
    ) -> List[T]:
        """获取所有记录
        
        Args:
            limit: 限制数量
            offset: 偏移量
            order_by: 排序字段
            desc_order: 是否降序
            
        Returns:
            List[T]: 模型实例列表
        """
        query = self.session.query(self.model)
        
        if order_by and hasattr(self.model, order_by):
            order_field = getattr(self.model, order_by)
            if desc_order:
                query = query.order_by(desc(order_field))
            else:
                query = query.order_by(asc(order_field))
        
        return query.offset(offset).limit(limit).all()
    
    def count(self, **filters) -> int:
        """统计记录数量
        
        Args:
            **filters: 过滤条件
            
        Returns:
            int: 记录数量
        """
        query = self.session.query(self.model)
        
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)
        
        return query.count()
    
    def exists(self, **filters) -> bool:
        """检查记录是否存在
        
        Args:
            **filters: 过滤条件
            
        Returns:
            bool: 是否存在
        """
        return self.count(**filters) > 0
    
    def find_by(self, **filters) -> List[T]:
        """根据条件查找记录
        
        Args:
            **filters: 过滤条件
            
        Returns:
            List[T]: 模型实例列表
        """
        query = self.session.query(self.model)
        
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)
        
        return query.all()
    
    def find_one_by(self, **filters) -> Optional[T]:
        """根据条件查找单个记录
        
        Args:
            **filters: 过滤条件
            
        Returns:
            Optional[T]: 模型实例或None
        """
        query = self.session.query(self.model)
        
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)
        
        return query.first()
    
    def update(self, id: int, **kwargs) -> Optional[T]:
        """更新记录
        
        Args:
            id: 记录ID
            **kwargs: 要更新的字段值
            
        Returns:
            Optional[T]: 更新后的模型实例或None
        """
        instance = self.get_by_id(id)
        if instance:
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            
            try:
                self.session.commit()
                self.session.refresh(instance)
                return instance
            except IntegrityError:
                self.session.rollback()
                raise
        
        return None
    
    def update_by_dict(self, id: int, data: Dict[str, Any]) -> Optional[T]:
        """通过字典更新记录
        
        Args:
            id: 记录ID
            data: 更新数据字典
            
        Returns:
            Optional[T]: 更新后的模型实例或None
        """
        instance = self.get_by_id(id)
        if instance:
            instance.update_from_dict(data)
            
            try:
                self.session.commit()
                self.session.refresh(instance)
                return instance
            except IntegrityError:
                self.session.rollback()
                raise
        
        return None
    
    def delete(self, id: int) -> bool:
        """删除记录
        
        Args:
            id: 记录ID
            
        Returns:
            bool: 是否删除成功
        """
        instance = self.get_by_id(id)
        if instance:
            self.session.delete(instance)
            try:
                self.session.commit()
                return True
            except IntegrityError:
                self.session.rollback()
                raise
        
        return False
    
    def delete_by(self, **filters) -> int:
        """根据条件删除记录
        
        Args:
            **filters: 过滤条件
            
        Returns:
            int: 删除的记录数量
        """
        query = self.session.query(self.model)
        
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)
        
        count = query.count()
        query.delete(synchronize_session=False)
        
        try:
            self.session.commit()
            return count
        except IntegrityError:
            self.session.rollback()
            raise
    
    def bulk_create(self, data_list: List[Dict[str, Any]]) -> List[T]:
        """批量创建记录
        
        Args:
            data_list: 数据字典列表
            
        Returns:
            List[T]: 创建的模型实例列表
        """
        instances = [self.model(**data) for data in data_list]
        self.session.add_all(instances)
        
        try:
            self.session.commit()
            for instance in instances:
                self.session.refresh(instance)
            return instances
        except IntegrityError:
            self.session.rollback()
            raise
    
    def bulk_update(self, updates: List[Dict[str, Any]]) -> int:
        """批量更新记录
        
        Args:
            updates: 更新数据列表，每个字典必须包含'id'字段
            
        Returns:
            int: 更新的记录数量
        """
        count = 0
        
        for update_data in updates:
            if 'id' not in update_data:
                continue
            
            record_id = update_data.pop('id')
            if self.update(record_id, **update_data):
                count += 1
        
        return count
    
    def paginate(
        self, 
        page: int = 1, 
        per_page: int = 20, 
        order_by: str = None,
        desc_order: bool = False,
        **filters
    ) -> Dict[str, Any]:
        """分页查询
        
        Args:
            page: 页码（从1开始）
            per_page: 每页数量
            order_by: 排序字段
            desc_order: 是否降序
            **filters: 过滤条件
            
        Returns:
            Dict[str, Any]: 分页结果
        """
        query = self.session.query(self.model)
        
        # 应用过滤条件
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)
        
        # 统计总数
        total = query.count()
        
        # 应用排序
        if order_by and hasattr(self.model, order_by):
            order_field = getattr(self.model, order_by)
            if desc_order:
                query = query.order_by(desc(order_field))
            else:
                query = query.order_by(asc(order_field))
        
        # 应用分页
        offset = (page - 1) * per_page
        items = query.offset(offset).limit(per_page).all()
        
        # 计算分页信息
        total_pages = (total + per_page - 1) // per_page
        has_prev = page > 1
        has_next = page < total_pages
        
        return {
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'has_prev': has_prev,
            'has_next': has_next,
            'prev_page': page - 1 if has_prev else None,
            'next_page': page + 1 if has_next else None
        }
    
    def search(
        self, 
        search_term: str, 
        search_fields: List[str],
        limit: int = 50
    ) -> List[T]:
        """搜索记录
        
        Args:
            search_term: 搜索词
            search_fields: 搜索字段列表
            limit: 限制数量
            
        Returns:
            List[T]: 搜索结果
        """
        query = self.session.query(self.model)
        
        # 构建搜索条件
        search_conditions = []
        for field in search_fields:
            if hasattr(self.model, field):
                field_attr = getattr(self.model, field)
                search_conditions.append(field_attr.like(f"%{search_term}%"))
        
        if search_conditions:
            query = query.filter(or_(*search_conditions))
        
        return query.limit(limit).all()