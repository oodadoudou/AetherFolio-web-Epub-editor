"""系统配置相关数据模型"""

from sqlalchemy import Column, String, Text, Boolean, JSON
from sqlalchemy.orm import validates
from typing import Any, Dict
import json

from ..base import BaseModel

class SystemConfig(BaseModel):
    """系统配置模型"""
    __tablename__ = "system_configs"
    
    key = Column(String(100), unique=True, index=True, nullable=False, comment="配置键")
    value = Column(Text, comment="配置值")
    value_type = Column(String(20), default="string", comment="值类型")
    description = Column(Text, comment="配置描述")
    category = Column(String(50), default="general", comment="配置分类")
    is_public = Column(Boolean, default=False, comment="是否公开")
    is_editable = Column(Boolean, default=True, comment="是否可编辑")
    default_value = Column(Text, comment="默认值")
    validation_rules = Column(JSON, comment="验证规则")
    
    @validates('value_type')
    def validate_value_type(self, key, value_type):
        """验证值类型"""
        allowed_types = ['string', 'integer', 'float', 'boolean', 'json', 'list']
        if value_type not in allowed_types:
            raise ValueError(f"值类型必须是以下之一: {', '.join(allowed_types)}")
        return value_type
    
    def get_typed_value(self) -> Any:
        """获取类型化的值
        
        Returns:
            Any: 根据value_type转换后的值
        """
        if self.value is None:
            return None
        
        try:
            if self.value_type == 'integer':
                return int(self.value)
            elif self.value_type == 'float':
                return float(self.value)
            elif self.value_type == 'boolean':
                return self.value.lower() in ('true', '1', 'yes', 'on')
            elif self.value_type == 'json':
                return json.loads(self.value)
            elif self.value_type == 'list':
                return json.loads(self.value) if self.value.startswith('[') else self.value.split(',')
            else:  # string
                return self.value
        except (ValueError, json.JSONDecodeError) as e:
            # 如果转换失败，返回原始字符串值
            return self.value
    
    def set_typed_value(self, value: Any) -> None:
        """设置类型化的值
        
        Args:
            value: 要设置的值
        """
        if value is None:
            self.value = None
            return
        
        if self.value_type == 'json' or self.value_type == 'list':
            self.value = json.dumps(value, ensure_ascii=False)
        elif self.value_type == 'boolean':
            self.value = 'true' if value else 'false'
        else:
            self.value = str(value)
    
    def get_default_typed_value(self) -> Any:
        """获取类型化的默认值
        
        Returns:
            Any: 根据value_type转换后的默认值
        """
        if self.default_value is None:
            return None
        
        # 临时设置value为default_value来使用get_typed_value方法
        original_value = self.value
        self.value = self.default_value
        try:
            result = self.get_typed_value()
        finally:
            self.value = original_value
        
        return result
    
    def reset_to_default(self) -> None:
        """重置为默认值"""
        self.value = self.default_value
    
    def validate_value(self, value: Any) -> bool:
        """验证值是否符合规则
        
        Args:
            value: 要验证的值
            
        Returns:
            bool: 是否通过验证
        """
        if not self.validation_rules:
            return True
        
        rules = self.validation_rules
        
        # 检查必填
        if rules.get('required', False) and value is None:
            return False
        
        # 检查最小值/最小长度
        if 'min' in rules:
            if self.value_type in ['integer', 'float']:
                if value < rules['min']:
                    return False
            elif self.value_type == 'string':
                if len(str(value)) < rules['min']:
                    return False
        
        # 检查最大值/最大长度
        if 'max' in rules:
            if self.value_type in ['integer', 'float']:
                if value > rules['max']:
                    return False
            elif self.value_type == 'string':
                if len(str(value)) > rules['max']:
                    return False
        
        # 检查枚举值
        if 'enum' in rules:
            if value not in rules['enum']:
                return False
        
        # 检查正则表达式
        if 'pattern' in rules and self.value_type == 'string':
            import re
            if not re.match(rules['pattern'], str(value)):
                return False
        
        return True
    
    @classmethod
    def get_config(
        cls, 
        session, 
        key: str, 
        default: Any = None, 
        create_if_missing: bool = False
    ) -> Any:
        """获取配置值
        
        Args:
            session: 数据库会话
            key: 配置键
            default: 默认值
            create_if_missing: 如果不存在是否创建
            
        Returns:
            Any: 配置值
        """
        config = session.query(cls).filter(cls.key == key).first()
        
        if config:
            return config.get_typed_value()
        
        if create_if_missing and default is not None:
            # 推断值类型
            value_type = 'string'
            if isinstance(default, bool):
                value_type = 'boolean'
            elif isinstance(default, int):
                value_type = 'integer'
            elif isinstance(default, float):
                value_type = 'float'
            elif isinstance(default, (dict, list)):
                value_type = 'json'
            
            config = cls(
                key=key,
                value_type=value_type,
                description=f"自动创建的配置项: {key}"
            )
            config.set_typed_value(default)
            config.default_value = config.value
            
            session.add(config)
            session.commit()
            
            return default
        
        return default
    
    @classmethod
    def set_config(
        cls, 
        session, 
        key: str, 
        value: Any, 
        description: str = None,
        category: str = "general",
        is_public: bool = False
    ) -> 'SystemConfig':
        """设置配置值
        
        Args:
            session: 数据库会话
            key: 配置键
            value: 配置值
            description: 配置描述
            category: 配置分类
            is_public: 是否公开
            
        Returns:
            SystemConfig: 配置实例
        """
        config = session.query(cls).filter(cls.key == key).first()
        
        if config:
            config.set_typed_value(value)
            if description:
                config.description = description
        else:
            # 推断值类型
            value_type = 'string'
            if isinstance(value, bool):
                value_type = 'boolean'
            elif isinstance(value, int):
                value_type = 'integer'
            elif isinstance(value, float):
                value_type = 'float'
            elif isinstance(value, (dict, list)):
                value_type = 'json'
            
            config = cls(
                key=key,
                value_type=value_type,
                description=description or f"配置项: {key}",
                category=category,
                is_public=is_public
            )
            config.set_typed_value(value)
            config.default_value = config.value
            
            session.add(config)
        
        session.commit()
        return config
    
    @classmethod
    def get_configs_by_category(
        cls, 
        session, 
        category: str, 
        public_only: bool = False
    ) -> Dict[str, Any]:
        """根据分类获取配置
        
        Args:
            session: 数据库会话
            category: 配置分类
            public_only: 是否只获取公开配置
            
        Returns:
            Dict[str, Any]: 配置字典
        """
        query = session.query(cls).filter(cls.category == category)
        
        if public_only:
            query = query.filter(cls.is_public == True)
        
        configs = query.all()
        
        return {
            config.key: config.get_typed_value()
            for config in configs
        }