"""规则管理API路由"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
import os
import tempfile
import json
import uuid
from datetime import datetime
from pathlib import Path

from core.logging import performance_logger
from core.security import security_validator

router = APIRouter(prefix="/api/v1/rules", tags=["rules"])

# 内存中存储规则（实际项目中应该使用数据库）
rules_storage: Dict[str, Dict[str, Any]] = {}


@router.post("/upload")
async def upload_rule_file(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None)
):
    """上传规则文件"""
    try:
        # 验证文件类型
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in [".txt"]:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件格式: {file_ext}。仅支持 .txt 文件"
            )
        
        # 读取文件内容
        content = await file.read()
        
        # 验证文本文件内容
        try:
            rules_text = content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                rules_text = content.decode('gbk')
            except UnicodeDecodeError:
                raise HTTPException(
                    status_code=422,
                    detail="无效的文本文件：文件内容不是有效的文本格式"
                )
        
        # 解析规则
        rules = parse_rules(rules_text)
        
        if not rules:
            raise HTTPException(
                status_code=422,
                detail="规则文件中没有找到有效的规则"
            )
        
        # 生成规则ID
        rule_id = str(uuid.uuid4())
        
        # 存储规则
        rule_data = {
            "id": rule_id,
            "name": name or file.filename,
            "filename": file.filename,
            "rules": rules,
            "rules_count": len(rules),
            "created_at": datetime.now().isoformat(),
            "content": rules_text
        }
        
        rules_storage[rule_id] = rule_data
        
        performance_logger.info(
            f"Rule file uploaded successfully: {file.filename}",
            extra={
                "rule_id": rule_id,
                "rules_count": len(rules)
            }
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "rule_id": rule_id,
                "message": "规则文件上传成功",
                "data": {
                    "rule_id": rule_id,
                    "name": rule_data["name"],
                    "rules_count": len(rules),
                    "created_at": rule_data["created_at"]
                }
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        performance_logger.error(f"Rule upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail="规则文件上传失败")


@router.get("")
async def get_rules_list():
    """获取规则列表"""
    try:
        rules_list = []
        for rule_id, rule_data in rules_storage.items():
            rules_list.append({
                "id": rule_data["id"],
                "name": rule_data["name"],
                "filename": rule_data["filename"],
                "rules_count": rule_data["rules_count"],
                "created_at": rule_data["created_at"]
            })
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "rules": rules_list,
                    "total": len(rules_list)
                }
            }
        )
        
    except Exception as e:
        performance_logger.error(f"Get rules list failed: {str(e)}")
        raise HTTPException(status_code=500, detail="获取规则列表失败")


@router.get("/{rule_id}")
async def get_rule_details(rule_id: str):
    """获取规则详情"""
    try:
        if rule_id not in rules_storage:
            raise HTTPException(status_code=404, detail="规则不存在")
        
        rule_data = rules_storage[rule_id]
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": rule_data
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        performance_logger.error(f"Get rule details failed: {str(e)}")
        raise HTTPException(status_code=500, detail="获取规则详情失败")


@router.post("/{rule_id}/preview")
async def get_rule_preview(rule_id: str, request_data: dict):
    """获取规则预览"""
    try:
        if rule_id not in rules_storage:
            raise HTTPException(status_code=404, detail="规则不存在")
        
        text = request_data.get("text", "")
        if not text:
            raise HTTPException(status_code=400, detail="文本内容不能为空")
        
        rule_data = rules_storage[rule_id]
        rules = rule_data["rules"]
        
        # 应用规则
        result_text = apply_rules(text, rules)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "original": text,
                    "result": result_text,
                    "rules_applied": len(rules)
                },
                "result": result_text  # 为了兼容测试代码
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        performance_logger.error(f"Rule preview failed: {str(e)}")
        raise HTTPException(status_code=500, detail="规则预览失败")


@router.put("/{rule_id}")
async def update_rule(rule_id: str, rule_data: dict):
    """更新规则"""
    try:
        if rule_id not in rules_storage:
            raise HTTPException(status_code=404, detail="规则不存在")
        
        # 更新规则数据
        existing_rule = rules_storage[rule_id]
        
        if "name" in rule_data:
            existing_rule["name"] = rule_data["name"]
        
        if "content" in rule_data:
            rules = parse_rules(rule_data["content"])
            existing_rule["rules"] = rules
            existing_rule["rules_count"] = len(rules)
            existing_rule["content"] = rule_data["content"]
        
        existing_rule["updated_at"] = datetime.now().isoformat()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "规则更新成功",
                "data": existing_rule
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        performance_logger.error(f"Update rule failed: {str(e)}")
        raise HTTPException(status_code=500, detail="更新规则失败")


@router.delete("/{rule_id}")
async def delete_rule(rule_id: str):
    """删除规则"""
    try:
        if rule_id not in rules_storage:
            raise HTTPException(status_code=404, detail="规则不存在")
        
        del rules_storage[rule_id]
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "规则删除成功"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        performance_logger.error(f"Delete rule failed: {str(e)}")
        raise HTTPException(status_code=500, detail="删除规则失败")


def parse_rules(rules_text: str) -> List[Dict[str, str]]:
    """解析规则文本"""
    rules = []
    
    for line in rules_text.split('\n'):
        line = line.strip()
        
        # 跳过空行和注释
        if not line or line.startswith('#'):
            continue
        
        # 解析规则
        if '->' in line:
            parts = line.split('->', 1)
            if len(parts) == 2:
                original = parts[0].strip()
                replacement = parts[1].strip()
                
                if original and replacement:
                    rules.append({
                        "original": original,
                        "replacement": replacement,
                        "type": "regex" if original.startswith('/') and original.endswith('/') else "simple"
                    })
    
    return rules


def apply_rules(text: str, rules: List[Dict[str, str]]) -> str:
    """应用规则到文本"""
    result = text
    
    for rule in rules:
        original = rule["original"]
        replacement = rule["replacement"]
        rule_type = rule.get("type", "simple")
        
        if rule_type == "regex":
            # 处理正则表达式规则
            if original.startswith('/') and original.endswith('/'):
                import re
                pattern = original[1:-1]  # 去掉前后的斜杠
                try:
                    result = re.sub(pattern, replacement, result)
                except re.error:
                    # 如果正则表达式无效，跳过这个规则
                    continue
        else:
            # 简单字符串替换
            result = result.replace(original, replacement)
    
    return result