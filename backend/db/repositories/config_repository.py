"""系统配置数据访问仓储"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from .base import BaseRepository
from ..models.config import SystemConfig

class ConfigRepository(BaseRepository[SystemConfig]):
    """系统配置仓储类"""
    
    def __init__(self, session: Session):
        super().__init__(session, SystemConfig)
    
    def get_by_key(self, key: str) -> Optional[SystemConfig]:
        """根据配置键获取配置
        
        Args:
            key: 配置键
            
        Returns:
            Optional[SystemConfig]: 配置实例或None
        """
        return (
            self.session.query(SystemConfig)
            .filter(SystemConfig.key == key)
            .first()
        )
    
    def get_config_value(
        self, 
        key: str, 
        default: Any = None, 
        create_if_missing: bool = False
    ) -> Any:
        """获取配置值
        
        Args:
            key: 配置键
            default: 默认值
            create_if_missing: 如果不存在是否创建
            
        Returns:
            Any: 配置值
        """
        return SystemConfig.get_config(
            self.session, 
            key, 
            default, 
            create_if_missing
        )
    
    def set_config_value(
        self, 
        key: str, 
        value: Any, 
        description: str = None,
        category: str = "general",
        is_public: bool = False
    ) -> SystemConfig:
        """设置配置值
        
        Args:
            key: 配置键
            value: 配置值
            description: 配置描述
            category: 配置分类
            is_public: 是否公开
            
        Returns:
            SystemConfig: 配置实例
        """
        return SystemConfig.set_config(
            self.session,
            key,
            value,
            description,
            category,
            is_public
        )
    
    def get_configs_by_category(
        self, 
        category: str, 
        public_only: bool = False
    ) -> Dict[str, Any]:
        """根据分类获取配置
        
        Args:
            category: 配置分类
            public_only: 是否只获取公开配置
            
        Returns:
            Dict[str, Any]: 配置字典
        """
        return SystemConfig.get_configs_by_category(
            self.session,
            category,
            public_only
        )
    
    def get_public_configs(self) -> Dict[str, Any]:
        """获取所有公开配置
        
        Returns:
            Dict[str, Any]: 公开配置字典
        """
        configs = (
            self.session.query(SystemConfig)
            .filter(SystemConfig.is_public == True)
            .all()
        )
        
        return {
            config.key: config.get_typed_value()
            for config in configs
        }
    
    def get_editable_configs(self) -> List[SystemConfig]:
        """获取可编辑的配置
        
        Returns:
            List[SystemConfig]: 可编辑配置列表
        """
        return (
            self.session.query(SystemConfig)
            .filter(SystemConfig.is_editable == True)
            .order_by(SystemConfig.category, SystemConfig.key)
            .all()
        )
    
    def get_categories(self) -> List[str]:
        """获取所有配置分类
        
        Returns:
            List[str]: 分类列表
        """
        from sqlalchemy import distinct
        
        result = (
            self.session.query(distinct(SystemConfig.category))
            .order_by(SystemConfig.category)
            .all()
        )
        
        return [row[0] for row in result if row[0]]
    
    def create_config(
        self,
        key: str,
        value: Any,
        value_type: str = "string",
        description: str = None,
        category: str = "general",
        is_public: bool = False,
        is_editable: bool = True,
        validation_rules: Dict[str, Any] = None
    ) -> SystemConfig:
        """创建配置项
        
        Args:
            key: 配置键
            value: 配置值
            value_type: 值类型
            description: 配置描述
            category: 配置分类
            is_public: 是否公开
            is_editable: 是否可编辑
            validation_rules: 验证规则
            
        Returns:
            SystemConfig: 创建的配置实例
        """
        config = SystemConfig(
            key=key,
            value_type=value_type,
            description=description,
            category=category,
            is_public=is_public,
            is_editable=is_editable,
            validation_rules=validation_rules
        )
        
        config.set_typed_value(value)
        config.default_value = config.value
        
        self.session.add(config)
        self.session.commit()
        self.session.refresh(config)
        
        return config
    
    def update_config(
        self,
        key: str,
        value: Any = None,
        description: str = None,
        is_public: bool = None,
        is_editable: bool = None
    ) -> Optional[SystemConfig]:
        """更新配置项
        
        Args:
            key: 配置键
            value: 新值
            description: 新描述
            is_public: 是否公开
            is_editable: 是否可编辑
            
        Returns:
            Optional[SystemConfig]: 更新后的配置实例或None
        """
        config = self.get_by_key(key)
        
        if not config:
            return None
        
        if value is not None:
            config.set_typed_value(value)
        
        if description is not None:
            config.description = description
        
        if is_public is not None:
            config.is_public = is_public
        
        if is_editable is not None:
            config.is_editable = is_editable
        
        self.session.commit()
        self.session.refresh(config)
        
        return config
    
    def delete_config(self, key: str) -> bool:
        """删除配置项
        
        Args:
            key: 配置键
            
        Returns:
            bool: 是否删除成功
        """
        config = self.get_by_key(key)
        
        if config:
            self.session.delete(config)
            self.session.commit()
            return True
        
        return False
    
    def reset_config_to_default(self, key: str) -> bool:
        """重置配置为默认值
        
        Args:
            key: 配置键
            
        Returns:
            bool: 是否重置成功
        """
        config = self.get_by_key(key)
        
        if config:
            config.reset_to_default()
            self.session.commit()
            return True
        
        return False
    
    def validate_config_value(self, key: str, value: Any) -> bool:
        """验证配置值
        
        Args:
            key: 配置键
            value: 要验证的值
            
        Returns:
            bool: 是否通过验证
        """
        config = self.get_by_key(key)
        
        if config:
            return config.validate_value(value)
        
        return True  # 如果配置不存在，默认通过验证
    
    def bulk_update_configs(self, updates: Dict[str, Any]) -> Dict[str, bool]:
        """批量更新配置
        
        Args:
            updates: 更新字典，键为配置键，值为新值
            
        Returns:
            Dict[str, bool]: 更新结果字典
        """
        results = {}
        
        for key, value in updates.items():
            try:
                # 验证值
                if self.validate_config_value(key, value):
                    config = self.update_config(key, value)
                    results[key] = config is not None
                else:
                    results[key] = False
            except Exception:
                results[key] = False
        
        return results
    
    def export_configs(
        self, 
        category: str = None, 
        public_only: bool = False
    ) -> Dict[str, Dict[str, Any]]:
        """导出配置
        
        Args:
            category: 配置分类（可选）
            public_only: 是否只导出公开配置
            
        Returns:
            Dict[str, Dict[str, Any]]: 配置导出数据
        """
        query = self.session.query(SystemConfig)
        
        if category:
            query = query.filter(SystemConfig.category == category)
        
        if public_only:
            query = query.filter(SystemConfig.is_public == True)
        
        configs = query.all()
        
        return {
            config.key: {
                'value': config.get_typed_value(),
                'value_type': config.value_type,
                'description': config.description,
                'category': config.category,
                'is_public': config.is_public,
                'is_editable': config.is_editable,
                'default_value': config.get_default_typed_value(),
                'validation_rules': config.validation_rules
            }
            for config in configs
        }
    
    def import_configs(
        self, 
        config_data: Dict[str, Dict[str, Any]], 
        overwrite: bool = False
    ) -> Dict[str, bool]:
        """导入配置
        
        Args:
            config_data: 配置数据
            overwrite: 是否覆盖现有配置
            
        Returns:
            Dict[str, bool]: 导入结果字典
        """
        results = {}
        
        for key, data in config_data.items():
            try:
                existing_config = self.get_by_key(key)
                
                if existing_config and not overwrite:
                    results[key] = False
                    continue
                
                if existing_config:
                    # 更新现有配置
                    existing_config.set_typed_value(data.get('value'))
                    if 'description' in data:
                        existing_config.description = data['description']
                    if 'is_public' in data:
                        existing_config.is_public = data['is_public']
                    if 'is_editable' in data:
                        existing_config.is_editable = data['is_editable']
                    
                    self.session.commit()
                    results[key] = True
                else:
                    # 创建新配置
                    config = self.create_config(
                        key=key,
                        value=data.get('value'),
                        value_type=data.get('value_type', 'string'),
                        description=data.get('description'),
                        category=data.get('category', 'general'),
                        is_public=data.get('is_public', False),
                        is_editable=data.get('is_editable', True),
                        validation_rules=data.get('validation_rules')
                    )
                    results[key] = config is not None
                    
            except Exception:
                results[key] = False
        
        return results
    
    def search_configs(
        self, 
        search_term: str, 
        search_in_values: bool = False
    ) -> List[SystemConfig]:
        """搜索配置
        
        Args:
            search_term: 搜索词
            search_in_values: 是否在值中搜索
            
        Returns:
            List[SystemConfig]: 搜索结果
        """
        search_fields = ['key', 'description', 'category']
        
        if search_in_values:
            search_fields.append('value')
        
        return self.search(search_term, search_fields, 100)