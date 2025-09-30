"""HTML 报告生成服务"""

import html
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from services.base import BaseService
from db.models.schemas import BatchReplaceReport, ReplaceResult
from core.config import settings


class ReportService(BaseService):
    """HTML 报告生成服务"""
    
    def __init__(self):
        super().__init__("report")
        self.template_cache = {}
    
    async def _initialize(self):
        """初始化服务"""
        await super()._initialize()
        self.log_info("Report service initialized")
    
    async def generate_html_report(
        self,
        report: BatchReplaceReport,
        source_filename: str,
        style: str = "green"
    ) -> str:
        """生成 HTML 格式的替换报告
        
        Args:
            report: 批量替换报告
            source_filename: 源文件名
            style: 报告样式 (green, minimal)
            
        Returns:
            str: HTML 报告内容
        """
        async with self.performance_context("generate_html_report"):
            try:
                # 获取模板
                template_content = await self._get_template(style)
                
                # 按替换规则归类
                rule_groups = await self._group_by_rules(report.results)
                
                # 生成报告数据
                total_instances = sum(len(group['instances']) for group in rule_groups.values())
                sorted_rule_groups = sorted(rule_groups.values(), key=lambda x: len(x['instances']), reverse=True)
                
                # 生成规则列表项
                rules_list_items = await self._generate_rules_list(sorted_rule_groups)
                
                # 生成内容区域
                content_sections = await self._generate_content_sections(sorted_rule_groups)
                
                # 替换模板中的占位符
                html_content = template_content.replace('{{source_filename}}', html.escape(source_filename))
                html_content = html_content.replace('{{rules_count}}', str(len(sorted_rule_groups)))
                html_content = html_content.replace('{{total_instances}}', str(total_instances))
                html_content = html_content.replace('{{rules_list_items}}', rules_list_items)
                html_content = html_content.replace('{{content_sections}}', content_sections)
                html_content = html_content.replace('{{generation_time}}', 
                                                  datetime.fromtimestamp(report.generated_at).strftime('%Y-%m-%d %H:%M:%S'))
                
                self.log_info(
                    "HTML report generated",
                    task_id=report.task_id,
                    style=style,
                    rules_count=len(sorted_rule_groups),
                    total_instances=total_instances
                )
                
                return html_content
                
            except Exception as e:
                self.log_error("Failed to generate HTML report", e, task_id=report.task_id)
                raise
    
    async def _get_template(self, style: str) -> str:
        """获取报告模板
        
        Args:
            style: 样式名称
            
        Returns:
            str: 模板内容
        """
        if style in self.template_cache:
            return self.template_cache[style]
        
        # 尝试从 public 目录读取模板
        template_paths = [
            f"public/batch_replacer_{style}_template.html",
            f"public/report_template_{style}.html",
            "references/report_template.html"  # 备用模板
        ]
        
        for template_path in template_paths:
            # 使用当前工作目录作为项目根目录
            project_root = Path.cwd()
            full_path = project_root / template_path
            if full_path.exists():
                try:
                    template_content = full_path.read_text(encoding='utf-8')
                    self.template_cache[style] = template_content
                    return template_content
                except Exception as e:
                    self.log_warning(f"Failed to read template {full_path}", e)
                    continue
        
        # 如果没有找到模板，使用默认模板
        return await self._get_default_template()
    
    async def _get_default_template(self) -> str:
        """获取默认模板"""
        return '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>批量替换报告 - {{source_filename}}</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }
        .stats {
            display: flex;
            justify-content: center;
            gap: 40px;
            margin-top: 20px;
        }
        .stat-item {
            text-align: center;
        }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            display: block;
        }
        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
        }
        .content {
            padding: 30px;
        }
        .rule-group {
            margin-bottom: 30px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            overflow: hidden;
        }
        .rule-header {
            background: #f8f9fa;
            padding: 20px;
            cursor: pointer;
            border-bottom: 1px solid #e0e0e0;
        }
        .rule-title {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 10px;
        }
        .rule-badge {
            background: #28a745;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
        }
        .rule-description {
            font-size: 1.1em;
            color: #333;
        }
        .rule-arrow {
            color: #666;
            margin: 0 10px;
        }
        .instances-container {
            max-height: 400px;
            overflow-y: auto;
        }
        .instance-item {
            padding: 20px;
            border-bottom: 1px solid #f0f0f0;
        }
        .instance-item:last-child {
            border-bottom: none;
        }
        .instance-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        .section-title {
            font-weight: bold;
            color: #666;
            margin-bottom: 8px;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .text-content {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #007bff;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.9em;
            line-height: 1.5;
        }
        .highlight {
            background-color: #fff3cd;
            color: #856404;
            padding: 2px 4px;
            border-radius: 3px;
            font-weight: bold;
        }
        .footer {
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            border-top: 1px solid #e0e0e0;
        }
        .toggle-icon {
            transition: transform 0.3s ease;
        }
        .collapsed .toggle-icon {
            transform: rotate(-90deg);
        }
        .collapsed .instances-container {
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>批量替换报告</h1>
            <div class="stats">
                <div class="stat-item">
                    <span class="stat-number">{{rules_count}}</span>
                    <span class="stat-label">替换规则</span>
                </div>
                <div class="stat-item">
                    <span class="stat-number">{{total_instances}}</span>
                    <span class="stat-label">替换次数</span>
                </div>
            </div>
        </div>
        
        <div class="content">
            {{content_sections}}
        </div>
        
        <div class="footer">
            <p>报告生成时间: {{generation_time}} | 源文件: {{source_filename}}</p>
        </div>
    </div>
    
    <script>
        function toggleInstances(groupIndex) {
            const group = document.querySelector(`[data-group-index="${groupIndex}"]`);
            const container = document.getElementById(`instances-${groupIndex}`);
            const icon = document.getElementById(`toggle-${groupIndex}`);
            
            if (container.style.display === 'none') {
                container.style.display = 'block';
                icon.textContent = '▼';
                group.classList.remove('collapsed');
            } else {
                container.style.display = 'none';
                icon.textContent = '▶';
                group.classList.add('collapsed');
            }
        }
        
        function jumpToRule(ruleIndex) {
            const ruleGroup = document.querySelector(`[data-group-index="${ruleIndex}"]`);
            if (ruleGroup) {
                ruleGroup.scrollIntoView({ behavior: 'smooth', block: 'start' });
                // 展开规则组
                const container = document.getElementById(`instances-${ruleIndex}`);
                if (container.style.display === 'none') {
                    toggleInstances(ruleIndex);
                }
            }
        }
    </script>
</body>
</html>
        '''
    
    async def _group_by_rules(self, results: List[Any]) -> Dict[str, Dict[str, Any]]:
        """按替换规则归类
        
        Args:
            results: 替换结果列表 (ReplaceFileResult 或 ReplaceResult)
            
        Returns:
            Dict[str, Dict[str, Any]]: 按规则分组的数据
        """
        rule_groups = {}
        
        for result in results:
            # 适配不同的结果类型
            if hasattr(result, 'replacements'):  # ReplaceResult 类型
                for replacement in result.replacements:
                    original_text = replacement.get('original', '')
                    replacement_text = replacement.get('replacement', '')
                    rule_key = f"{original_text} → {replacement_text}"
                    
                    if rule_key not in rule_groups:
                        rule_groups[rule_key] = {
                            'original_text': original_text,
                            'replacement_text': replacement_text,
                            'instances': []
                        }
                    
                    # 创建实例数据
                    instance = {
                        'original': replacement.get('original', ''),
                        'modified': replacement.get('replacement', ''),
                        'position': replacement.get('position', 0),
                        'file_path': result.file_path
                    }
                    
                    rule_groups[rule_key]['instances'].append(instance)
            else:  # ReplaceFileResult 类型 - 创建简化的规则组
                if result.replacements_count > 0:
                    # 为每个应用的规则创建一个简化的条目
                    for rule_name in result.rules_applied:
                        rule_key = f"规则: {rule_name}"
                        
                        if rule_key not in rule_groups:
                            rule_groups[rule_key] = {
                                'original_text': f'应用规则: {rule_name}',
                                'replacement_text': f'在 {result.file_path} 中替换了 {result.replacements_count} 次',
                                'instances': []
                            }
                        
                        # 创建简化的实例数据
                        instance = {
                            'original': f'文件: {result.file_path}',
                            'modified': f'成功替换 {result.replacements_count} 次',
                            'position': 0,
                            'file_path': result.file_path
                        }
                        
                        rule_groups[rule_key]['instances'].append(instance)
        
        return rule_groups
    
    async def _generate_rules_list(self, sorted_rule_groups: List[Dict[str, Any]]) -> str:
        """生成规则列表项
        
        Args:
            sorted_rule_groups: 排序后的规则组列表
            
        Returns:
            str: 规则列表 HTML
        """
        rules_list_items = ""
        
        for i, group in enumerate(sorted_rule_groups):
            rules_list_items += f'''
                <div class="rule-list-item" onclick="jumpToRule({i})">
                    <div class="rule-text">
                        <span class="rule-original">{html.escape(group["original_text"])}</span> → 
                        <span class="rule-replacement">{html.escape(group["replacement_text"])}</span>
                    </div>
                    <div class="rule-count">{len(group["instances"])} 次</div>
                </div>
            '''
        
        return rules_list_items
    
    async def _generate_content_sections(self, sorted_rule_groups: List[Dict[str, Any]]) -> str:
        """生成内容区域
        
        Args:
            sorted_rule_groups: 排序后的规则组列表
            
        Returns:
            str: 内容区域 HTML
        """
        content_sections = ""
        
        for group_index, group in enumerate(sorted_rule_groups):
            instance_count = len(group['instances'])
            content_sections += f'''
                <div class="rule-group" data-group-index="{group_index}">
                    <div class="rule-header" onclick="toggleInstances({group_index})">
                        <div class="rule-title">
                            <span class="rule-badge">{instance_count} 次</span>
                            <span class="toggle-icon" id="toggle-{group_index}">▼</span>
                        </div>
                        <div class="rule-description">
                            <span><strong>{html.escape(group['original_text'])}</strong></span>
                            <span class="rule-arrow">→</span>
                            <span><strong>{html.escape(group['replacement_text'])}</strong></span>
                        </div>
                    </div>
                    <div class="instances-container" id="instances-{group_index}">
            '''
            
            # 按位置排序实例
            sorted_instances = sorted(group['instances'], key=lambda x: x.get('position', 0))
            
            for instance in sorted_instances:
                content_sections += f'''
                        <div class="instance-item">
                            <div class="instance-content">
                                <div class="original-section">
                                    <div class="section-title">原文</div>
                                    <div class="text-content">{instance['original']}</div>
                                </div>
                                <div class="modified-section">
                                    <div class="section-title">修改后</div>
                                    <div class="text-content">{instance['modified']}</div>
                                </div>
                            </div>
                        </div>
                '''
            
            content_sections += '''
                    </div>
                </div>
            '''
        
        return content_sections
    
    async def save_report(
        self,
        report_html: str,
        task_id: str,
        filename: Optional[str] = None
    ) -> Path:
        """保存报告到文件
        
        Args:
            report_html: 报告 HTML 内容
            task_id: 任务 ID
            filename: 文件名（可选）
            
        Returns:
            Path: 保存的文件路径
        """
        async with self.performance_context("save_report"):
            try:
                # 确保报告目录存在
                reports_dir = Path.cwd() / "backend" / "reports"
                reports_dir.mkdir(parents=True, exist_ok=True)
                
                # 生成文件名
                if not filename:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"replace_report_{task_id}_{timestamp}.html"
                
                report_path = reports_dir / filename
                
                # 写入文件
                report_path.write_text(report_html, encoding='utf-8')
                
                self.log_info("Report saved", task_id=task_id, file_path=str(report_path))
                
                return report_path
                
            except Exception as e:
                self.log_error("Failed to save report", e, task_id=task_id)
                raise
    
    async def _cleanup(self):
        """清理服务资源"""
        # ReportService 没有需要特别清理的资源
        # 调用父类的清理方法
        await super()._cleanup()


# 创建全局服务实例
report_service = ReportService()


# 导出
__all__ = ["ReportService", "report_service"]