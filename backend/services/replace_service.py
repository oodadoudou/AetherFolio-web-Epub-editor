"""批量替换服务"""

import re
import asyncio
import time
from typing import List, Dict, Optional, AsyncGenerator, Tuple
from dataclasses import dataclass
from pathlib import Path
from bs4 import BeautifulSoup

from services.base import AsyncTaskService
from services.epub_service import epub_service
from services.text_service import text_service
from services.report_service import report_service
from services.session_service import session_service
from db.models.schemas import (
    ReplaceRule, ReplaceResult, ReplaceProgress, BatchReplaceReport,
    RuleValidationResult, FileType, ResponseStatus, ErrorCode
)
from core.config import settings
from core.security import security_validator


@dataclass
class ReplaceTask:
    """替换任务"""
    session_id: str
    rules: List[ReplaceRule]
    case_sensitive: bool
    use_regex: bool
    target_files: Optional[List[str]] = None
    progress_callback: Optional[callable] = None


class ReplaceService(AsyncTaskService):
    """批量替换服务"""
    
    def __init__(self):
        super().__init__("replace", max_concurrent_tasks=settings.worker_processes)
        self.progress_data: Dict[str, ReplaceProgress] = {}
        self.replace_reports: Dict[str, BatchReplaceReport] = {}
        self.session_to_task: Dict[str, str] = {}  # session_id -> task_id 映射
    
    async def _initialize(self):
        """初始化服务"""
        await super()._initialize()
        self.log_info("Replace service initialized")
    
    async def _cleanup(self):
        """清理服务"""
        self.progress_data.clear()
        self.replace_reports.clear()
        await super()._cleanup()
    
    async def validate_rules(self, rules_content: str) -> RuleValidationResult:
        """验证替换规则的语法和安全性
        
        对规则文件内容进行全面验证，包括语法检查、正则表达式验证、
        危险操作检测（如ReDoS攻击模式）等。
        
        Args:
            rules_content (str): 规则文件内容，支持多种格式：
                - 箭头格式: "old_text -> new_text"
                - 正则格式: "pattern -> replacement (Mode: Regex)"
                - 管道格式: "search|replace|is_regex|enabled|description"
            
        Returns:
            RuleValidationResult: 验证结果对象，包含：
                - is_valid: 是否所有规则都有效
                - total_rules: 总规则数
                - valid_rules: 有效规则数
                - invalid_rules: 无效规则列表及错误信息
                - warnings: 警告信息列表
                
        Example:
            >>> rules_content = "hello -> world\ntest -> example (Mode: Text)"
            >>> result = await replace_service.validate_rules(rules_content)
            >>> if result.is_valid:
            ...     print(f"所有 {result.total_rules} 条规则都有效")
        """
        async with self.performance_context("validate_rules"):
            try:
                # 检查空文件
                if not rules_content.strip():
                    return RuleValidationResult(
                        is_valid=False,
                        total_rules=0,
                        valid_rules=0,
                        invalid_rules=[{
                            "line": 0,
                            "rule": {},
                            "error": "规则文件为空，请添加有效的替换规则"
                        }],
                        warnings=[]
                    )
                
                rules = await self._parse_rules(rules_content)
                
                # 如果解析后没有规则（只有注释或空行），也认为是无效的
                if len(rules) == 0:
                    return RuleValidationResult(
                        is_valid=False,
                        total_rules=0,
                        valid_rules=0,
                        invalid_rules=[{
                            "line": 0,
                            "rule": {},
                            "error": "文件中没有有效的替换规则"
                        }],
                        warnings=[]
                    )
                
                # 验证规则
                valid_rules = []
                invalid_rules = []
                dangerous_operations = []
                
                for i, rule in enumerate(rules):
                    try:
                        # 验证规则格式
                        if not rule.original.strip():
                            invalid_rules.append({
                                "line": i + 1,
                                "rule": rule.model_dump(),
                                "error": "搜索文本不能为空"
                            })
                            continue
                        
                        # 如果是正则表达式，验证语法
                        if rule.is_regex:
                            try:
                                re.compile(rule.original)
                            except re.error as e:
                                invalid_rules.append({
                                    "line": i + 1,
                                    "rule": rule.model_dump(),
                                    "error": f"正则表达式语法错误: {str(e)}"
                                })
                                continue
                        
                        # 检测危险操作（包括ReDoS模式）
                        danger_checks = await self._check_dangerous_operations(rule, i + 1, f"{rule.original} -> {rule.replacement}")
                        dangerous_operations.extend(danger_checks)
                        
                        # 检查是否有高危险操作
                        has_high_severity_danger = any(
                            danger.get('severity') == 'high' or 
                            danger.get('type') in ['redos_pattern', 'catastrophic_backtracking', 'exponential_backtracking']
                            for danger in danger_checks
                        )
                        
                        if has_high_severity_danger:
                            # 将高危险规则标记为无效
                            danger_messages = [danger.get('message', '未知危险操作') for danger in danger_checks 
                                             if danger.get('severity') == 'high' or 
                                                danger.get('type') in ['redos_pattern', 'catastrophic_backtracking', 'exponential_backtracking']]
                            invalid_rules.append({
                                 "line": i + 1,
                                 "rule": rule.model_dump(),
                                 "error": f"Dangerous regex pattern detected: {'; '.join(danger_messages)}"
                             })
                        else:
                            valid_rules.append(rule)
                        
                    except Exception as e:
                        invalid_rules.append({
                            "line": i + 1,
                            "rule": rule.model_dump() if hasattr(rule, 'model_dump') else str(rule),
                            "error": f"规则解析错误: {str(e)}"
                        })
                
                # 检查是否有高危险操作（如ReDoS模式）
                has_critical_dangers = any(
                    danger.get('severity') == 'high' or 
                    danger.get('type') in ['redos_pattern', 'catastrophic_backtracking']
                    for danger in dangerous_operations
                )
                
                return RuleValidationResult(
                    is_valid=len(invalid_rules) == 0 and not has_critical_dangers,
                    total_rules=len(rules),
                    valid_rules=len(valid_rules),
                    invalid_rules=invalid_rules,
                    warnings=[]
                )
                
            except Exception as e:
                self.log_error("Failed to validate rules", e)
                return RuleValidationResult(
                    is_valid=False,
                    total_rules=0,
                    valid_rules=0,
                    invalid_rules=[{
                        "line": 0,
                        "rule": {},
                        "error": f"规则文件解析失败: {str(e)}"
                    }],
                    warnings=[]
                )
    
    async def validate_rules_detailed(self, rules_content: str) -> Dict:
        """详细验证替换规则（用于BE-03任务）
        
        Args:
            rules_content: 规则文件内容
            
        Returns:
            Dict: 详细验证结果
        """
        async with self.performance_context("validate_rules_detailed"):
            try:
                # 检查空文件
                if not rules_content.strip():
                    return {
                        "is_valid": False,
                        "total_rules": 0,
                        "total_rules_count": 0,
                        "valid_rules_count": 0,
                        "invalid_rules_count": 1,
                        "warnings_count": 0,
                        "dangerous_operations_count": 0,
                        "valid_rules": [],
                        "invalid_rules": [{
                            "line": 0,
                            "rule_text": "",
                            "parsed_rule": None,
                            "errors": ["规则文件为空，请添加有效的替换规则"]
                        }],
                        "warnings": [],
                        "dangerous_operations": [],
                        "rule_preview": [],
                        "statistics": {"total_lines": 0, "non_empty_lines": 0, "comment_lines": 0, "empty_lines": 0},
                        "validation_summary": {
                            "can_proceed": False,
                            "has_warnings": False,
                            "recommendation": "规则文件为空，请添加有效的替换规则"
                        }
                    }
                
                lines = rules_content.strip().split('\n')
                total_lines = len(lines)
                
                valid_rules = []
                invalid_rules = []
                warnings = []
                dangerous_operations = []
                
                for line_num, line in enumerate(lines, 1):
                    original_line = line
                    line = line.strip()
                    
                    # 跳过空行和注释
                    if not line or line.startswith('#'):
                        continue
                    
                    try:
                        # 解析规则
                        try:
                            rule = await self._parse_single_rule(line, line_num)
                        except ValueError as parse_error:
                            # 规则解析失败，直接添加到无效规则列表
                            invalid_rules.append({
                                "line": line_num,
                                "rule_text": original_line,
                                "parsed_rule": None,
                                "errors": [f"规则格式不正确: {str(parse_error)}"]
                            })
                            continue
                        
                        # 基本验证
                        validation_errors = []
                        
                        # 检查搜索文本
                        if not rule.original.strip():
                            validation_errors.append("搜索文本不能为空")
                        
                        # 验证正则表达式语法
                        if rule.is_regex:
                            try:
                                compiled_regex = re.compile(rule.original)
                                # 检查正则表达式复杂度
                                if len(rule.original) > 200:
                                    warnings.append({
                                        "line": line_num,
                                        "message": "正则表达式过于复杂，可能影响性能",
                                        "rule_text": original_line
                                    })
                            except re.error as e:
                                validation_errors.append(f"正则表达式语法错误: {str(e)}")
                        
                        # 检测危险操作
                        danger_checks = await self._check_dangerous_operations(rule, line_num, original_line)
                        dangerous_operations.extend(danger_checks)
                        
                        # 性能警告
                        if len(rule.original) > 100:
                            warnings.append({
                                "line": line_num,
                                "message": "搜索文本较长，可能影响替换性能",
                                "rule_text": original_line
                            })
                        
                        if validation_errors:
                            invalid_rules.append({
                                "line": line_num,
                                "rule_text": original_line,
                                "parsed_rule": {
                                    "original": rule.original,
                                    "replacement": rule.replacement,
                                    "is_regex": rule.is_regex,
                                    "enabled": rule.enabled
                                },
                                "errors": validation_errors
                            })
                        else:
                            valid_rules.append({
                                "line": line_num,
                                "rule_text": original_line,
                                "parsed_rule": {
                                    "original": rule.original,
                                    "replacement": rule.replacement,
                                    "is_regex": rule.is_regex,
                                    "enabled": rule.enabled,
                                    "description": rule.description
                                }
                            })
                            
                    except Exception as e:
                        invalid_rules.append({
                            "line": line_num,
                            "rule_text": original_line,
                            "parsed_rule": None,
                            "errors": [f"规则解析错误: {str(e)}"]
                        })
                
                # 检测循环引用
                circular_warnings = await self._check_circular_references(valid_rules)
                warnings.extend(circular_warnings)
                
                # 检测递归深度
                depth_warnings = await self._check_recursive_depth(valid_rules)
                warnings.extend(depth_warnings)
                
                # 生成规则预览（前5条有效规则）
                rule_preview = valid_rules[:5]
                
                # 统计信息
                stats = {
                    "total_lines": total_lines,
                    "non_empty_lines": len([line for line in lines if line.strip() and not line.strip().startswith('#')]),
                    "comment_lines": len([line for line in lines if line.strip().startswith('#')]),
                    "empty_lines": len([line for line in lines if not line.strip()])
                }
                
                # 检查是否有高危险操作（如ReDoS模式）
                has_critical_dangers = any(
                    danger.get('severity') == 'high' or 
                    danger.get('type') in ['redos_pattern', 'catastrophic_backtracking']
                    for danger in dangerous_operations
                )
                
                # 如果没有有效规则（只有注释或空行），认为是无效的
                if len(valid_rules) == 0 and len(invalid_rules) == 0:
                    return {
                        "is_valid": False,
                        "total_rules": 0,
                        "total_rules_count": 0,
                        "valid_rules_count": 0,
                        "invalid_rules_count": 1,
                        "warnings_count": len(warnings),
                        "dangerous_operations_count": len(dangerous_operations),
                        "valid_rules": [],
                        "invalid_rules": [{
                            "line": 0,
                            "rule_text": "",
                            "parsed_rule": None,
                            "errors": ["文件中没有有效的替换规则"]
                        }],
                        "warnings": warnings,
                        "dangerous_operations": dangerous_operations,
                        "rule_preview": [],
                        "statistics": stats,
                        "validation_summary": {
                            "can_proceed": False,
                            "has_warnings": len(warnings) > 0,
                            "recommendation": "文件中没有有效的替换规则，请添加有效的规则"
                        }
                    }
                
                return {
                    "is_valid": len(invalid_rules) == 0 and not has_critical_dangers,
                    "total_rules": len(valid_rules) + len(invalid_rules),
                    "total_rules_count": len(valid_rules) + len(invalid_rules),
                    "valid_rules_count": len(valid_rules),
                    "invalid_rules_count": len(invalid_rules),
                    "warnings_count": len(warnings),
                    "dangerous_operations_count": len(dangerous_operations),
                    "valid_rules": valid_rules,
                    "invalid_rules": invalid_rules,
                    "warnings": warnings,
                    "dangerous_operations": dangerous_operations,
                    "rule_preview": rule_preview,
                    "statistics": stats,
                    "validation_summary": {
                        "can_proceed": len(invalid_rules) == 0 and len(dangerous_operations) == 0,
                        "has_warnings": len(warnings) > 0,
                        "recommendation": self._get_validation_recommendation(len(valid_rules), len(invalid_rules), len(warnings), len(dangerous_operations))
                    }
                }
                
            except Exception as e:
                self.log_error("Failed to validate rules detailed", e)
                return {
                    "is_valid": False,
                    "total_rules": 0,
                    "total_rules_count": 0,
                    "valid_rules_count": 0,
                    "invalid_rules_count": 1,
                    "warnings_count": 0,
                    "dangerous_operations_count": 0,
                    "valid_rules": [],
                    "invalid_rules": [{
                        "line": 0,
                        "rule_text": "",
                        "parsed_rule": None,
                        "errors": [f"规则文件解析失败: {str(e)}"]
                    }],
                    "warnings": [],
                    "dangerous_operations": [],
                    "rule_preview": [],
                    "statistics": {"total_lines": 0, "non_empty_lines": 0, "comment_lines": 0, "empty_lines": 0},
                    "validation_summary": {
                        "can_proceed": False,
                        "has_warnings": False,
                        "recommendation": "文件解析失败，请检查文件格式和编码"
                    }
                }
    
    async def _parse_rules(self, rules_content: str) -> List[ReplaceRule]:
        """解析替换规则
        
        Args:
            rules_content: 规则文件内容
            
        Returns:
            List[ReplaceRule]: 解析后的规则列表
        """
        rules = []
        lines = rules_content.strip().split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # 跳过空行和注释
            if not line or line.startswith('#'):
                continue
            
            try:
                # 支持两种格式：
                # 1. 参考实现格式：original -> replacement (Mode: Text|Regex)
                # 2. 管道分隔格式：search_text|replace_text|is_regex|enabled|description
                
                # 尝试解析参考实现格式
                match = re.match(r'^(.*?)\s*->\s*(.*?)\s*\(Mode:\s*(Text|Regex)\s*\)$', line, re.IGNORECASE)
                if match:
                    original, replacement, mode = match.groups()
                    rule = ReplaceRule(
                        original=original.strip(),
                        replacement=replacement.strip(),
                        is_regex=mode.strip().lower() == 'regex',
                        enabled=True,
                        description=f"{original.strip()} → {replacement.strip()}"
                    )
                    rules.append(rule)
                    continue
                
                # 尝试解析无替换文本的格式
                match_no_replacement = re.match(r'^(.*?)\s*(?:->|→)\s*\(Mode:\s*(Text|Regex)\s*\)$', line, re.IGNORECASE)
                if match_no_replacement:
                    original, mode = match_no_replacement.groups()
                    rule = ReplaceRule(
                        original=original.strip(),
                        replacement="",
                        is_regex=mode.strip().lower() == 'regex',
                        enabled=True,
                        description=f"{original.strip()} → (删除)"
                    )
                    rules.append(rule)
                    continue
                
                # 尝试解析简单箭头格式：search -> replace | description | regex
                arrow_match = re.match(r'^(.*?)\s*(?:->|→)\s*(.*?)(?:\s*\|\s*(.*))?$', line)
                if arrow_match:
                    search_text, replace_text, rest = arrow_match.groups()
                    search_text = search_text.strip()
                    replace_text = replace_text.strip()
                    
                    # 解析剩余部分
                    is_regex = False
                    description = f"{search_text} → {replace_text}"
                    
                    if rest:
                        rest_parts = rest.split('|')
                        if len(rest_parts) >= 1:
                            description = rest_parts[0].strip()
                        if len(rest_parts) >= 2:
                            is_regex = rest_parts[1].strip().lower() in ['true', 'regex']
                    
                    rule = ReplaceRule(
                        original=search_text,
                        replacement=replace_text,
                        is_regex=is_regex,
                        enabled=True,
                        description=description
                    )
                    rules.append(rule)
                    continue
                
                # 尝试解析管道分隔格式
                parts = line.split('|')
                if len(parts) >= 2:
                    search_text = parts[0].strip()
                    replace_text = parts[1].strip() if len(parts) > 1 else ""
                    is_regex = parts[2].strip().lower() == 'true' if len(parts) > 2 else False
                    enabled = parts[3].strip().lower() != 'false' if len(parts) > 3 else True
                    description = parts[4].strip() if len(parts) > 4 else f"{search_text} → {replace_text}"
                    
                    rule = ReplaceRule(
                        original=search_text,
                        replacement=replace_text,
                        is_regex=is_regex,
                        enabled=enabled,
                        description=description
                    )
                    rules.append(rule)
                    continue
                
                # 如果都不匹配，抛出错误
                raise ValueError("规则格式不正确")
                
            except Exception as e:
                raise ValueError(f"第{line_num}行规则解析错误: {str(e)}")
        
        return rules
    
    async def _parse_single_rule(self, line: str, line_num: int) -> ReplaceRule:
        """解析单个规则
        
        Args:
            line: 规则行内容
            line_num: 行号
            
        Returns:
            ReplaceRule: 解析后的规则
        """
        # 检查前缀标记
        is_regex = False
        case_sensitive = False
        
        # 处理前缀
        if line.startswith('REGEX:') or line.startswith('regex:'):
            is_regex = True
            line = line[6:].strip()
        elif line.startswith('CASE:REGEX:') or line.startswith('CASE:regex:'):
            is_regex = True
            case_sensitive = True
            line = line[11:].strip()
        elif line.startswith('CASE:'):
            case_sensitive = True
            line = line[5:].strip()
        
        # 尝试解析参考实现格式
        match = re.match(r'^(.*?)\s*(?:->|→)\s*(.*?)\s*\(Mode:\s*(Text|Regex)\s*\)$', line, re.IGNORECASE)
        if match:
            original, replacement, mode = match.groups()
            return ReplaceRule(
                 original=original.strip(),
                 replacement=replacement.strip(),
                 is_regex=mode.strip().lower() == 'regex' or is_regex,
                 enabled=True,
                 description=f"{original.strip()} → {replacement.strip()}"
             )
        
        # 尝试解析无替换文本的格式
        match_no_replacement = re.match(r'^(.*?)\s*(?:->|→)\s*\(Mode:\s*(Text|Regex)\s*\)$', line, re.IGNORECASE)
        if match_no_replacement:
            original, mode = match_no_replacement.groups()
            return ReplaceRule(
                 original=original.strip(),
                 replacement="",
                 is_regex=mode.strip().lower() == 'regex' or is_regex,
                 enabled=True,
                 description=f"{original.strip()} → (删除)"
             )
        
        # 尝试解析简单箭头格式：search -> replace | description | regex
        arrow_match = re.match(r'^(.*?)\s*(?:->|→)\s*(.*?)(?:\s*\|\s*(.*))?$', line)
        if arrow_match:
            search_text, replace_text, rest = arrow_match.groups()
            search_text = search_text.strip()
            replace_text = replace_text.strip()
            
            # 解析剩余部分
            description = f"{search_text} → {replace_text}"
            
            if rest:
                rest_parts = rest.split('|')
                if len(rest_parts) >= 1:
                    description = rest_parts[0].strip()
                if len(rest_parts) >= 2:
                    is_regex = rest_parts[1].strip().lower() in ['true', 'regex'] or is_regex
            
            return ReplaceRule(
                 original=search_text,
                 replacement=replace_text,
                 is_regex=is_regex,
                 enabled=True,
                 description=description
             )
        
        # 尝试解析管道分隔格式
        parts = line.split('|')
        if len(parts) >= 2:
            search_text = parts[0].strip()
            replace_text = parts[1].strip() if len(parts) > 1 else ""
            is_regex_part = parts[2].strip().lower() == 'true' if len(parts) > 2 else False
            enabled = parts[3].strip().lower() != 'false' if len(parts) > 3 else True
            description = parts[4].strip() if len(parts) > 4 else f"{search_text} → {replace_text}"
            
            return ReplaceRule(
                 original=search_text,
                 replacement=replace_text,
                 is_regex=is_regex_part or is_regex,
                 enabled=enabled,
                 description=description
             )
        
        # 如果都不匹配，抛出错误
        raise ValueError("规则格式不正确")
    
    async def _check_dangerous_operations(self, rule: ReplaceRule, line_num: int, original_line: str) -> List[Dict]:
        """检测危险操作
        
        Args:
            rule: 规则对象
            line_num: 行号
            original_line: 原始行内容
            
        Returns:
            List[Dict]: 危险操作列表
        """
        dangerous_ops = []
        
        # 检测空字符串替换（删除操作）
        if not rule.replacement.strip():
            dangerous_ops.append({
                "line": line_num,
                "type": "empty_replacement",
                "severity": "high",
                "message": "将文本替换为空字符串（删除操作），请确认这是预期行为",
                "rule_text": original_line,
                "recommendation": "如果确实要删除文本，建议在规则描述中明确说明"
            })
        
        # 检测ReDoS攻击模式
        if rule.is_regex:
            redos_patterns = [
                # 嵌套量词模式
                (r'\(.*\+.*\)\+', "嵌套量词可能导致灾难性回溯", "catastrophic_backtracking"),
                (r'\(.*\*.*\)\*', "嵌套星号量词可能导致指数级回溯", "exponential_backtracking"),
                # 选择分支与量词组合
                (r'\([^)]*\|[^)]*\)\*', "选择分支与量词组合可能导致ReDoS", "redos_pattern"),
                (r'\([^)]*\|[^)]*\)\+', "选择分支与量词组合可能导致ReDoS", "redos_pattern"),
                # 字符类与量词组合
                (r'\([a-zA-Z0-9\[\]\-\+]+\)\*', "字符类与量词组合可能导致ReDoS", "redos_pattern"),
                (r'\([a-zA-Z0-9\[\]\-\+]+\)\+', "字符类与量词组合可能导致ReDoS", "redos_pattern"),
                # 锚点与量词组合
                (r'\^\(.*\+.*\)\+\$', "锚点与嵌套量词组合可能导致ReDoS", "redos_pattern"),
                # 贪婪匹配与回溯
                (r'\(\.\*.*\)\{.*,.*\}', "贪婪匹配与量词组合可能导致回溯", "performance_issue"),
                # 重复的选择分支（如(a|a)*）
                (r'\(([a-zA-Z])\|\1\)', "重复的选择分支可能导致指数级回溯", "exponential_backtracking")
            ]
            
            for pattern, message, danger_type in redos_patterns:
                if re.search(pattern, rule.original):
                    dangerous_ops.append({
                        "line": line_num,
                        "type": danger_type,
                        "severity": "high",
                        "message": f"检测到潜在ReDoS攻击模式: {message}",
                        "rule_text": original_line,
                        "recommendation": "建议重写正则表达式以避免灾难性回溯"
                    })
            
            # 检测过于宽泛的正则表达式
            dangerous_patterns = [
                (r'^\.*$', "匹配任意字符的正则表达式过于宽泛"),
                (r'^\w*$', "匹配任意单词字符的正则表达式可能过于宽泛"),
                (r'^\s*$', "匹配空白字符的正则表达式可能影响文档格式"),
                (r'.*', "包含.*的正则表达式可能匹配过多内容")
            ]
            
            for pattern, message in dangerous_patterns:
                if re.search(pattern, rule.original):
                    dangerous_ops.append({
                        "line": line_num,
                        "type": "broad_regex",
                        "severity": "medium",
                        "message": message,
                        "rule_text": original_line,
                        "recommendation": "建议使用更具体的正则表达式模式"
                    })
                    break
        
        # 检测可能影响文档结构的替换
        structural_patterns = [
            (r'<[^>]*>', "HTML/XML标签"),
            (r'\{[^}]*\}', "花括号结构"),
            (r'\[[^\]]*\]', "方括号结构"),
            (r'"[^"]*"', "引号内容")
        ]
        
        for pattern, desc in structural_patterns:
            if re.search(pattern, rule.original):
                dangerous_ops.append({
                    "line": line_num,
                    "type": "structural_change",
                    "severity": "medium",
                    "message": f"替换{desc}可能影响文档结构",
                    "rule_text": original_line,
                    "recommendation": "请确认此替换不会破坏文档的完整性"
                })
        
        # 检测大量替换的风险
        if len(rule.original) <= 3 and not rule.is_regex:
            dangerous_ops.append({
                "line": line_num,
                "type": "high_frequency_replacement",
                "severity": "low",
                "message": "搜索文本过短，可能产生大量意外替换",
                "rule_text": original_line,
                "recommendation": "建议使用更具体的搜索条件"
            })
        
        return dangerous_ops
    
    async def _check_circular_references(self, valid_rules: List[Dict]) -> List[Dict]:
        """检测循环引用
        
        Args:
            valid_rules: 有效规则列表
            
        Returns:
            List[Dict]: 循环引用警告列表
        """
        warnings = []
        
        # 构建规则图：original -> replacement 的映射
        rule_graph = {}
        rule_lines = {}
        
        for rule_info in valid_rules:
            rule = rule_info["parsed_rule"]
            original = rule["original"]
            replacement = rule["replacement"]
            line_num = rule_info["line"]
            
            # 只检查非正则表达式的文本替换规则
            if not rule["is_regex"] and original and replacement:
                rule_graph[original] = replacement
                rule_lines[original] = line_num
        
        # 使用深度优先搜索检测循环
        visited = set()
        rec_stack = set()
        
        def dfs(node, path):
            if node in rec_stack:
                # 找到循环，构建循环路径
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                return cycle
            
            if node in visited:
                return None
            
            visited.add(node)
            rec_stack.add(node)
            
            if node in rule_graph:
                next_node = rule_graph[node]
                cycle = dfs(next_node, path + [node])
                if cycle:
                    return cycle
            
            rec_stack.remove(node)
            return None
        
        # 检查每个节点
        for start_node in rule_graph:
            if start_node not in visited:
                cycle = dfs(start_node, [])
                if cycle:
                    # 构建循环描述
                    cycle_description = " -> ".join(cycle)
                    affected_lines = [rule_lines.get(node, 0) for node in cycle[:-1]]  # 排除重复的最后一个节点
                    
                    warnings.append({
                        "line": min(affected_lines) if affected_lines else 0,
                        "message": f"Circular reference detected: {cycle_description}",
                        "rule_text": f"涉及行号: {', '.join(map(str, affected_lines))}",
                        "type": "circular_reference",
                        "severity": "medium",
                        "cycle_path": cycle[:-1],  # 排除重复的最后一个节点
                        "affected_lines": affected_lines
                    })
        
        return warnings
    
    async def _check_recursive_depth(self, valid_rules: List[Dict]) -> List[Dict]:
        """检测递归替换深度
        
        Args:
            valid_rules: 有效规则列表
            
        Returns:
            List[Dict]: 递归深度警告列表
        """
        warnings = []
        
        # 构建规则图：original -> replacement 的映射
        rule_graph = {}
        rule_lines = {}
        
        for rule_info in valid_rules:
            rule = rule_info["parsed_rule"]
            original = rule["original"]
            replacement = rule["replacement"]
            line_num = rule_info["line"]
            
            # 只检查非正则表达式的文本替换规则
            if not rule["is_regex"] and original and replacement:
                rule_graph[original] = replacement
                rule_lines[original] = line_num
        
        # 检查每个替换链的深度
        visited = set()
        
        def get_chain_depth(start_node, current_depth=0, path=None):
            if path is None:
                path = []
            
            if start_node in path:  # 检测到循环，停止
                return current_depth
            
            if start_node not in rule_graph:
                return current_depth
            
            next_node = rule_graph[start_node]
            return get_chain_depth(next_node, current_depth + 1, path + [start_node])
        
        # 检查每个起始节点的替换链深度
        for start_node in rule_graph:
            if start_node not in visited:
                depth = get_chain_depth(start_node)
                
                # 如果深度超过阈值（比如10），发出警告
                if depth > 10:
                    warnings.append({
                        "line": rule_lines.get(start_node, 0),
                        "message": f"Recursive replacement depth too high: {depth} levels detected",
                        "rule_text": f"Starting from line {rule_lines.get(start_node, 0)}",
                        "type": "recursive_depth",
                        "severity": "medium",
                        "depth": depth,
                        "start_node": start_node
                    })
                
                # 标记这个链中的所有节点为已访问
                current = start_node
                chain_visited = set()
                while current in rule_graph and current not in chain_visited:
                    visited.add(current)
                    chain_visited.add(current)
                    current = rule_graph[current]
        
        return warnings
    
    def _get_validation_recommendation(self, valid_count: int, invalid_count: int, warning_count: int, danger_count: int) -> str:
        """获取验证建议
        
        Args:
            valid_count: 有效规则数量
            invalid_count: 无效规则数量
            warning_count: 警告数量
            danger_count: 危险操作数量
            
        Returns:
            str: 验证建议
        """
        if invalid_count > 0:
            return f"发现{invalid_count}个无效规则，请修复后重新验证"
        
        if danger_count > 0:
            return f"发现{danger_count}个潜在危险操作，建议仔细检查后再执行"
        
        if warning_count > 0:
            return f"验证通过，但有{warning_count}个警告，建议优化规则以提高性能"
        
        if valid_count == 0:
            return "文件中没有找到有效的替换规则"
        
        return f"验证通过！共{valid_count}个有效规则，可以安全执行批量替换"
    
    async def execute_replace(
        self,
        session_id: str,
        rules_content: str,
        case_sensitive: bool = True,
        target_files: Optional[List[str]] = None
    ) -> Dict:
        """执行批量替换（API入口方法）
        
        Args:
            session_id: 会话ID
            rules_content: 规则文件内容
            case_sensitive: 是否区分大小写
            target_files: 目标文件列表
            
        Returns:
            Dict: 包含任务ID的响应
        """
        # 验证规则
        validation_result = await self.validate_rules(rules_content)
        if not validation_result.is_valid:
            raise ValueError(f"规则验证失败: {validation_result.invalid_rules}")
        
        # 解析规则
        rules = await self._parse_rules(rules_content)
        
        # 执行批量替换
        task_id = await self.execute_batch_replace(
            session_id=session_id,
            rules=rules,
            case_sensitive=case_sensitive,
            target_files=target_files
        )
        
        return {
            "task_id": task_id,
            "session_id": session_id,
            "status": "started",
            "message": "批量替换任务已启动"
        }

    async def start_batch_replace(
        self,
        session_id: str,
        rules_content: str,
        case_sensitive: bool = False,
        use_regex: bool = False,
        target_files: Optional[List[str]] = None
    ) -> str:
        """开始批量替换（从规则文件内容）
        
        这是另一个批量替换入口方法，接受规则文件内容字符串而不是ReplaceRule对象列表。
        会先解析规则内容，然后调用execute_batch_replace执行替换。
        
        Args:
            session_id (str): 会话ID，用于标识要处理的文件会话
            rules_content (str): 规则文件内容，支持多种格式
            case_sensitive (bool, optional): 是否区分大小写。默认为False
            use_regex (bool, optional): 是否强制使用正则表达式模式。默认为False
            target_files (Optional[List[str]], optional): 目标文件列表，如果为None则处理所有文件
            
        Returns:
            str: 任务ID，用于跟踪替换进度和获取结果
            
        Raises:
            ValueError: 当规则内容无效或会话不存在时
            
        Example:
            >>> rules_content = "old_text -> new_text\npattern -> replacement (Mode: Regex)"
            >>> task_id = await replace_service.start_batch_replace(
            ...     session_id="session_123",
            ...     rules_content=rules_content,
            ...     case_sensitive=True
            ... )
        """
        # 延长会话有效期，确保批量替换过程中不会过期
        # 批量替换可能需要较长时间，延长到2小时
        await session_service.extend_session(session_id, extend_seconds=7200)
        
        # 验证规则
        validation_result = await self.validate_rules(rules_content)
        if not validation_result.is_valid:
            raise ValueError(f"规则验证失败: {validation_result.invalid_rules}")
        
        # 解析规则
        rules = await self._parse_rules(rules_content)
        
        # 创建任务
        task_id = f"replace_{session_id}_{int(time.time())}"
        
        # 初始化进度
        self.progress_data[task_id] = ReplaceProgress(
            session_id=session_id,
            task_id=task_id,
            status="starting",
            total_files=0,
            processed_files=0,
            total_replacements=0,
            current_file="",
            progress_percentage=0.0,
            start_time=time.time(),
            estimated_remaining=0
        )
        
        # 创建替换任务
        replace_task = ReplaceTask(
            session_id=session_id,
            rules=rules,
            case_sensitive=case_sensitive,
            use_regex=use_regex,
            target_files=target_files
        )
        
        # 启动异步任务
        await self.run_task(
            task_id,
            self._execute_batch_replace(task_id, replace_task),
            timeout=settings.batch_replace_timeout
        )
        
        return task_id
    
    async def execute_batch_replace(
        self, 
        session_id: str, 
        rules: List[ReplaceRule], 
        case_sensitive: bool = True,
        target_files: Optional[List[str]] = None
    ) -> str:
        """执行批量替换操作
        
        这是批量替换的主要入口方法，用于对EPUB或文本文件执行大规模替换操作。
        支持正则表达式和普通文本替换，具有进度跟踪和错误处理功能。
        
        Args:
            session_id (str): 会话ID，用于标识要处理的文件会话
            rules (List[ReplaceRule]): 替换规则列表，每个规则包含：
                - original: 要搜索的原始文本或正则表达式
                - replacement: 替换文本
                - is_regex: 是否为正则表达式
                - enabled: 是否启用该规则
                - description: 规则描述
            case_sensitive (bool, optional): 是否区分大小写。默认为True
            target_files (Optional[List[str]], optional): 目标文件列表，如果为None则处理所有文件
            
        Returns:
            str: 任务ID，用于跟踪替换进度和获取结果
            
        Raises:
            ValueError: 当会话不存在或规则列表为空时
            HTTPException: 当会话已过期或其他HTTP相关错误时
            
        Example:
            >>> rules = [
            ...     ReplaceRule(original="old_text", replacement="new_text", is_regex=False),
            ...     ReplaceRule(original="\\d+", replacement="NUMBER", is_regex=True)
            ... ]
            >>> task_id = await replace_service.execute_batch_replace(
            ...     session_id="session_123",
            ...     rules=rules,
            ...     case_sensitive=True
            ... )
        """
        # 延长会话有效期，确保批量替换过程中不会过期
        # 批量替换可能需要较长时间，延长到2小时
        await session_service.extend_session(session_id, extend_seconds=7200)
        
        import uuid
        task_id = str(uuid.uuid4())
        
        # 记录session_id到task_id的映射
        self.session_to_task[session_id] = task_id
        
        # 初始化进度
        self.progress_data[task_id] = ReplaceProgress(
            session_id=session_id,
            task_id=task_id,
            status="running",
            total_files=0,
            processed_files=0,
            total_replacements=0,
            current_file="",
            progress_percentage=0.0,
            start_time=time.time(),
            estimated_remaining=0
        )
        
        # 创建任务
        task = ReplaceTask(
            session_id=session_id,
            rules=rules,
            case_sensitive=case_sensitive,
            use_regex=any(rule.is_regex for rule in rules),
            target_files=target_files
        )
        
        # 启动异步任务（不等待完成）
        async def _run_background_task():
            try:
                await self._execute_batch_replace(task_id, task)
            except Exception as e:
                self.log_error("Background task failed", e, task_id=task_id)
                try:
                    await self._update_progress(task_id, status="failed", error_message=str(e))
                except Exception as update_error:
                    self.log_error("Failed to update progress after error", update_error, task_id=task_id)
        
        # 创建后台任务并存储引用
        background_task = asyncio.create_task(_run_background_task())
        # 存储任务引用以防止被垃圾回收
        self._running_tasks[f"{task_id}_background"] = background_task
        
        return task_id
    
    async def _execute_batch_replace(self, task_id: str, task: ReplaceTask):
        """执行批量替换"""
        try:
            self.log_info("Starting batch replace", task_id=task_id, session_id=task.session_id)
            
            # 再次延长会话有效期，确保在执行过程中不会过期
            await session_service.extend_session(task.session_id, extend_seconds=7200)
            
            # 更新进度状态
            await self._update_progress(task_id, status="running")
            
            # 获取会话信息以确定文件类型
            session_info = await session_service.get_session(task.session_id)
            if not session_info:
                raise ValueError(f"Session {task.session_id} not found")
            
            file_type = session_info.metadata.get('file_type', 'epub')
            
            # 根据文件类型获取文件列表
            if file_type == 'text':
                # TEXT文件只有一个文件
                target_files = [session_info.metadata.get('original_filename', 'text_file.txt')]
            else:
                # EPUB文件获取文件树
                file_tree = await epub_service.get_file_tree(task.session_id)
                target_files = await self._get_target_files(file_tree, task.target_files)
            
            # 更新总文件数
            await self._update_progress(task_id, total_files=len(target_files))
            
            # 执行替换
            results = []
            total_replacements = 0
            
            for i, file_path in enumerate(target_files):
                try:
                    # 更新当前处理文件
                    await self._update_progress(
                        task_id,
                        current_file=file_path,
                        processed_files=i
                    )
                    
                    # 处理文件
                    file_result = await self._process_file(
                        task.session_id,
                        file_path,
                        task.rules,
                        task.case_sensitive,
                        task.use_regex,
                        file_type
                    )
                    
                    if file_result:
                        results.append(file_result)
                        total_replacements += file_result.replacement_count
                    
                    # 更新进度
                    progress_percentage = (i + 1) / len(target_files) * 100
                    await self._update_progress(
                        task_id,
                        processed_files=i + 1,
                        total_replacements=total_replacements,
                        progress_percentage=progress_percentage
                    )
                    
                except Exception as e:
                    self.log_error("Failed to process file", e, file_path=file_path)
                    # 继续处理其他文件
                    continue
            
            # 如果有替换，处理文件后续操作
            if total_replacements > 0:
                await self._update_progress(
                    task_id,
                    current_file="正在完成文件处理...",
                    progress_percentage=95.0
                )
                
                try:
                    # 创建会话目录
                    session_dir = Path("backend/sessions") / task.session_id
                    session_dir.mkdir(parents=True, exist_ok=True)
                    
                    if file_type == 'text':
                        # TEXT文件已经在处理过程中直接修改，无需额外操作
                        self.log_info("Text file processing completed", 
                                     session_id=task.session_id)
                    else:
                        # 导出处理后的EPUB文件
                        processed_epub_path = session_dir / "processed.epub"
                        await epub_service.export_epub(task.session_id, str(processed_epub_path))
                        
                        # 同时保存原始文件的副本（如果不存在）
                        original_epub_path = session_dir / "original.epub"
                        if not original_epub_path.exists():
                            # 从会话元数据获取原始文件信息
                            session_info = await session_service.get_session(task.session_id)
                            if session_info and hasattr(session_info, 'original_filename'):
                                # 这里可以考虑保存原始文件，但目前先跳过
                                pass
                        
                        self.log_info("EPUB repackaged successfully", 
                                     session_id=task.session_id,
                                     processed_path=str(processed_epub_path))
                    
                except Exception as e:
                    self.log_error(f"Failed to process {file_type} file", e, session_id=task.session_id)
                    # 不抛出异常，因为替换已经完成
            
            # 生成报告
            report = await self._generate_report(task_id, task.session_id, results)
            self.replace_reports[task_id] = report
            
            # 完成任务
            await self._update_progress(
                task_id,
                status="completed",
                progress_percentage=100.0
            )
            
            self.log_info("Batch replace completed", 
                         task_id=task_id, 
                         total_files=len(target_files),
                         total_replacements=total_replacements)
            
        except Exception as e:
            self.log_error("Batch replace failed", e, task_id=task_id)
            await self._update_progress(task_id, status="failed", error_message=str(e))
            raise
    
    async def _get_target_files(self, file_tree: List, target_files: Optional[List[str]]) -> List[str]:
        """获取目标文件列表"""
        all_files = []
        
        def collect_files(nodes):
            for node in nodes:
                if node.type in [FileType.HTML, FileType.TEXT, FileType.XML]:
                    all_files.append(node.path)
                if node.children:
                    collect_files(node.children)
        
        collect_files(file_tree)
        
        # 如果指定了目标文件，过滤
        if target_files:
            all_files = [f for f in all_files if f in target_files]
        
        return all_files
    
    async def _process_file(
        self,
        session_id: str,
        file_path: str,
        rules: List[ReplaceRule],
        case_sensitive: bool,
        use_regex: bool,
        file_type: str = 'epub'
    ) -> Optional[ReplaceResult]:
        """处理单个文件"""
        try:
            if file_type == 'text':
                # 处理文本文件
                return await self._process_text_file(
                    session_id, file_path, rules, case_sensitive, use_regex
                )
            else:
                # 处理 EPUB 文件（HTML/XML）
                return await self._process_epub_file(
                    session_id, file_path, rules, case_sensitive, use_regex
                )
            
        except Exception as e:
            self.log_error("Failed to process file", e, file_path=file_path)
            raise
    
    async def _process_text_file(
        self,
        session_id: str,
        file_path: str,
        rules: List[ReplaceRule],
        case_sensitive: bool,
        use_regex: bool
    ) -> Optional[ReplaceResult]:
        """处理文本文件"""
        try:
            # 从内存中获取TEXT文件内容
            from services.text_service import text_service
            
            # 检查text_service中是否有该会话的文件内容
            if not hasattr(text_service, 'file_contents') or session_id not in text_service.file_contents:
                self.log_info(f"Session file contents not found in memory: {session_id}")
                return None
            
            file_contents = text_service.file_contents[session_id]
            if file_path not in file_contents:
                self.log_info(f"Text file not found in memory, skipping: {file_path}")
                return None
            
            # 从内存中读取文件内容
            content_bytes = file_contents[file_path]
            original_content = content_bytes.decode('utf-8')
            
            # 创建文件内容对象
            from models.file_content import FileContent
            file_content = FileContent(
                path=file_path,
                content=original_content,
                encoding='utf-8',
                mime_type='text/plain',
                size=len(content_bytes),
                is_binary=False
            )
            
            # 使用文本服务处理文件
            modified_content, replacements = await text_service.process_text_file(
                full_file_path, file_content.content, rules
            )
            
            if replacements:
                # 更新内存中的文件内容
                text_service.file_contents[session_id][file_path] = modified_content.encode('utf-8')
                
                # 转换替换记录格式
                replacement_dicts = []
                for repl in replacements:
                    replacement_dicts.append({
                        "position": repl.position,
                        "original": repl.original_text,
                        "replacement": repl.replacement_text,
                        "rule_description": repl.rule_description
                    })
                
                return ReplaceResult(
                    file_path=file_path,
                    replacement_count=len(replacements),
                    replacements=replacement_dicts,
                    original_size=len(file_content.content),
                    new_size=len(modified_content)
                )
            
            return None
            
        except Exception as e:
            self.log_error("Failed to process text file", e, file_path=file_path)
            raise
    
    async def _process_epub_file(
        self,
        session_id: str,
        file_path: str,
        rules: List[ReplaceRule],
        case_sensitive: bool,
        use_regex: bool
    ) -> Optional[ReplaceResult]:
        """处理 EPUB 文件（HTML/XML）"""
        try:
            # 获取文件内容
            file_content = await epub_service.get_file_content(session_id, file_path)
            original_content = file_content.content
            modified_content = original_content
            
            replacements = []
            total_count = 0
            
            # 应用每个规则
            for rule in rules:
                if not rule.enabled:
                    continue
                
                # 执行替换
                new_content, count, rule_replacements = await self._apply_rule(
                    modified_content,
                    rule,
                    case_sensitive or rule.is_regex,  # 正则表达式默认区分大小写
                    use_regex or rule.is_regex
                )
                
                if count > 0:
                    modified_content = new_content
                    total_count += count
                    replacements.extend(rule_replacements)
            
            # 如果有替换，保存文件
            if total_count > 0:
                await epub_service.save_file_content(
                    session_id,
                    file_path,
                    modified_content,
                    file_content.encoding
                )
                
                return ReplaceResult(
                    file_path=file_path,
                    replacement_count=total_count,
                    replacements=replacements,
                    original_size=len(original_content),
                    new_size=len(modified_content)
                )
            
            return None
            
        except Exception as e:
            self.log_error("Failed to process epub file", e, file_path=file_path)
            raise
    
    async def _apply_rule(
        self,
        content: str,
        rule: ReplaceRule,
        case_sensitive: bool,
        use_regex: bool
    ) -> Tuple[str, int, List[Dict]]:
        """应用单个替换规则"""
        replacements = []
        count = 0
        
        try:
            if rule.is_regex or use_regex:
                # 正则表达式替换
                import re
                flags = 0 if case_sensitive else re.IGNORECASE
                pattern = re.compile(rule.original, flags)
                
                def replace_func(match):
                    nonlocal count
                    count += 1
                    replacements.append({
                        "position": match.start(),
                        "original": match.group(0),
                        "replacement": rule.replacement,
                        "rule_description": rule.description
                    })
                    return rule.replacement
                
                new_content = pattern.sub(replace_func, content)
                
            else:
                # 普通文本替换
                search_text = rule.original
                replace_text = rule.replacement
                
                if not case_sensitive:
                    # 不区分大小写的替换
                    import re
                    pattern = re.compile(re.escape(search_text), re.IGNORECASE)
                    
                    def replace_func(match):
                        nonlocal count
                        count += 1
                        replacements.append({
                            "position": match.start(),
                            "original": match.group(0),
                                                    "replacement": replace_text,
                            "rule_description": rule.description
                        })
                        return replace_text
                    
                    new_content = pattern.sub(replace_func, content)
                else:
                    # 区分大小写的替换
                    pos = 0
                    new_content = ""
                    
                    while True:
                        index = content.find(search_text, pos)
                        if index == -1:
                            new_content += content[pos:]
                            break
                        
                        new_content += content[pos:index] + replace_text
                        count += 1
                        replacements.append({
                            "position": index,
                            "original": search_text,
                            "replacement": replace_text,
                            "rule_description": rule.description
                        })
                        pos = index + len(search_text)
            
            return new_content, count, replacements
            
        except Exception as e:
            self.log_error("Failed to apply rule", e, rule=rule.model_dump())
            return content, 0, []
    
    async def _update_progress(self, task_id: str, **kwargs):
        """更新进度信息"""
        if task_id in self.progress_data:
            progress = self.progress_data[task_id]
            
            # 更新字段
            for key, value in kwargs.items():
                if hasattr(progress, key):
                    setattr(progress, key, value)
            
            # 计算预估剩余时间
            if progress.progress_percentage > 0:
                elapsed_time = time.time() - progress.start_time
                estimated_total = elapsed_time / (progress.progress_percentage / 100)
                progress.estimated_remaining = max(0, estimated_total - elapsed_time)
    
    async def _generate_report(self, task_id: str, session_id: str, results: List[ReplaceResult]) -> BatchReplaceReport:
        """生成替换报告"""
        total_files = len(results)
        total_replacements = sum(r.replacement_count for r in results)
        
        # 按文件分组统计
        file_stats = {}
        for result in results:
            file_stats[result.file_path] = {
                "replacement_count": result.replacement_count,
                "original_size": result.original_size,
                "new_size": result.new_size,
                "size_change": result.new_size - result.original_size
            }
        
        # 按规则分组统计
        rule_stats = {}
        for result in results:
            for replacement in result.replacements:
                rule_desc = replacement.get("rule_description", "未知规则")
                if rule_desc not in rule_stats:
                    rule_stats[rule_desc] = 0
                rule_stats[rule_desc] += 1
        
        # 创建报告对象
        report = BatchReplaceReport(
            task_id=task_id,
            session_id=session_id,
            total_files=total_files,
            total_replacements=total_replacements,
            results=results,
            file_stats=file_stats,
            rule_stats=rule_stats,
            generated_at=time.time()
        )
        
        # 生成 HTML 报告
        try:
            # 获取源文件名
            from services.session_service import session_service
            session = await session_service.get_session(session_id)
            source_filename = "unknown.epub"
            if session and session.get('original_filename'):
                source_filename = session['original_filename']
            elif session and session.metadata and session.metadata.get('original_filename'):
                source_filename = session.metadata.get('original_filename')
            
            html_report_content = await report_service.generate_html_report(
                report=report,
                source_filename=source_filename,
                style="green"
            )
            self.log_info("HTML report generated", task_id=task_id)
        except Exception as e:
            self.log_error("Failed to generate HTML report", e, task_id=task_id)
            html_report_content = None
        
        return report
    
    async def get_progress(self, task_id: str) -> Optional[ReplaceProgress]:
        """获取批量替换任务的实时进度信息
        
        Args:
            task_id (str): 任务ID，由execute_batch_replace方法返回
            
        Returns:
            Optional[ReplaceProgress]: 进度信息对象，包含：
                - status: 任务状态 ("pending", "running", "completed", "failed")
                - processed_files: 已处理文件数
                - total_files: 总文件数
                - current_file: 当前处理的文件名
                - progress_percentage: 进度百分比 (0.0-100.0)
                - start_time: 开始时间
                - estimated_remaining: 预估剩余时间（秒）
                如果任务不存在则返回None
                
        Example:
            >>> progress = await replace_service.get_progress("task_123")
            >>> if progress:
            ...     print(f"进度: {progress.progress_percentage:.1f}%")
            ...     print(f"状态: {progress.status}")
        """
        return self.progress_data.get(task_id)
    
    async def get_progress_stream(self, task_id: str) -> AsyncGenerator[str, None]:
        """获取进度流（SSE）
        
        Args:
            task_id: 任务ID
            
        Yields:
            str: SSE格式的进度数据
        """
        import json
        
        last_progress = None
        max_wait_time = 300  # 最大等待时间5分钟
        start_time = time.time()
        no_progress_count = 0  # 连续无进度更新计数
        
        # 立即发送初始状态消息
        current_progress = self.progress_data.get(task_id)
        if current_progress:
            data = current_progress.model_dump()
            yield f"data: {json.dumps(data)}\r\n\r\n"
            last_progress = current_progress
        else:
            # 如果任务不存在，发送等待状态
            initial_data = {
                "status": "waiting",
                "message": "Waiting for task to start",
                "task_id": task_id,
                "progress": 0.0
            }
            yield f"data: {json.dumps(initial_data)}\r\n\r\n"
        
        while True:
            current_progress = self.progress_data.get(task_id)
            
            # 检查是否超时
            if time.time() - start_time > max_wait_time:
                self.log_warning(f"Progress stream timeout for task {task_id}")
                break
            
            # 如果任务不存在且等待超过30秒，退出
            if current_progress is None:
                no_progress_count += 1
                if no_progress_count > 30:  # 30秒后退出
                    self.log_info(f"Task {task_id} not found, ending progress stream")
                    break
            else:
                no_progress_count = 0  # 重置计数
            
            if current_progress and current_progress != last_progress:
                # 发送进度更新
                data = current_progress.model_dump()
                yield f"data: {json.dumps(data)}\r\n\r\n"
                last_progress = current_progress
                
                # 如果任务完成或失败，结束流
                if current_progress.status in ["completed", "failed", "cancelled"]:
                    break
            
            # 等待一段时间再检查
            await asyncio.sleep(1)
    
    async def get_report(self, task_id: str) -> Optional[BatchReplaceReport]:
        """获取批量替换任务的详细报告
        
        Args:
            task_id (str): 任务ID，由execute_batch_replace方法返回
            
        Returns:
            Optional[BatchReplaceReport]: 替换报告对象，包含：
                - task_id: 任务ID
                - session_id: 会话ID
                - total_files: 总文件数
                - processed_files: 已处理文件数
                - total_replacements: 总替换次数
                - execution_time: 执行时间（秒）
                - results: 每个文件的详细替换结果列表
                - created_at: 报告创建时间
                如果任务不存在或未完成则返回None
                
        Example:
            >>> report = await replace_service.get_report("task_123")
            >>> if report:
            ...     print(f"处理了 {report.processed_files} 个文件")
            ...     print(f"总共替换 {report.total_replacements} 次")
        """
        return self.replace_reports.get(task_id)
    
    async def get_report_by_session(self, session_id: str) -> Optional[BatchReplaceReport]:
        """根据会话ID获取替换报告
        
        Args:
            session_id: 会话ID
            
        Returns:
            Optional[BatchReplaceReport]: 替换报告
        """
        task_id = self.session_to_task.get(session_id)
        if task_id:
            return self.replace_reports.get(task_id)
        return None
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消替换任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否取消成功
        """
        # 更新进度状态
        if task_id in self.progress_data:
            await self._update_progress(task_id, status="cancelled")
        
        # 取消异步任务
        return await super().cancel_task(task_id)
    
    async def cleanup_task_data(self, task_id: str):
        """清理任务数据
        
        Args:
            task_id: 任务ID
        """
        self.progress_data.pop(task_id, None)
        self.replace_reports.pop(task_id, None)
        
        # 清理session_to_task映射
        session_id_to_remove = None
        for session_id, mapped_task_id in self.session_to_task.items():
            if mapped_task_id == task_id:
                session_id_to_remove = session_id
                break
        if session_id_to_remove:
            self.session_to_task.pop(session_id_to_remove, None)
        
        self.log_info("Task data cleaned up", task_id=task_id)
    
    def get_template_content(self) -> str:
        """获取规则模板内容
        
        Returns:
            str: 模板文件内容
        """
        template_content = """# 批量替换规则模板
# 格式说明：
# 1. 基本格式：查找文本 → 替换文本
# 2. 带描述：查找文本 → 替换文本 | 描述信息
# 3. 正则表达式：查找文本 → 替换文本 | 描述 | true
# 4. 分隔符格式：查找文本\t替换文本\t是否正则\t是否启用\t描述
# 5. 删除文本：查找文本 → (Mode: Text) 或 查找文本 → (Mode: Regex)
#
# 注意事项：
# - 以 # 开头的行为注释，会被忽略
# - 空行会被忽略
# - 支持 UTF-8 编码
# - 正则表达式请谨慎使用，避免性能问题

# 示例替换规则（请根据需要修改）：

# 基本文本替换
旧文本 → 新文本

# 带描述的替换
错误拼写 → 正确拼写 | 修正拼写错误

# 正则表达式替换（将连续的空格替换为单个空格）
\\s+ → " " | 规范化空格 | true

# 删除特定文本
不需要的文本 → (Mode: Text)

# 分隔符格式示例
# 查找\t替换\tfalse\ttrue\t描述信息
"""
        return template_content


# 创建全局服务实例
replace_service = ReplaceService()


# 导出
__all__ = ["ReplaceService", "replace_service"]