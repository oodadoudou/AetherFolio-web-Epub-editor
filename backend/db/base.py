"""数据库基础类

定义所有数据模型的基类和通用功能。
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, DateTime, func
from datetime import datetime

# 创建基础模型类
Base = declarative_base()

class TimestampMixin:
    """时间戳混入类
    
    为模型添加创建时间和更新时间字段。
    """
    
    created_at = Column(
        DateTime,
        default=func.now(),
        nullable=False,
        comment="创建时间"
    )
    
    updated_at = Column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间"
    )

class BaseModel(Base, TimestampMixin):
    """基础模型类
    
    所有数据模型的基类，包含通用字段和方法。
    """
    
    __abstract__ = True
    
    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        comment="主键ID"
    )
    
    def to_dict(self):
        """转换为字典"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def update_from_dict(self, data: dict):
        """从字典更新属性"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def __repr__(self):
        """字符串表示"""
        return f"<{self.__class__.__name__}(id={self.id})>"