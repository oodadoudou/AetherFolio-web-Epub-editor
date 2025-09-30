"""AetherFolio 数据库模块

这个模块包含了所有数据库相关的功能：
- 数据库连接管理
- 数据模型定义
- 数据访问层（Repository）
- 数据库迁移
- 种子数据
- 数据库脚本
"""

from .connection import db_manager, get_db
from .base import Base

__version__ = "1.0.0"
__all__ = ["db_manager", "get_db", "Base"]