#!/usr/bin/env python3
"""
调试递归替换深度检测的测试
"""

import pytest
import asyncio
from backend.services.replace_service import ReplaceService

@pytest.mark.asyncio
async def test_debug_recursive_replacement_depth():
    """调试递归替换深度检测"""
    print("\n=== Testing recursive replacement depth ===")
    
    replace_service = ReplaceService()
    
    # 创建深度递归替换链
    recursive_rules = []
    for i in range(15):  # 创建15层深度的替换链
        recursive_rules.append(f"level_{i} -> level_{i+1} | Recursive level {i}")
    
    recursive_content = "\n".join(recursive_rules)
    print(f"Recursive content:\n{recursive_content}")
    
    result = await replace_service.validate_rules_detailed(recursive_content)
    
    print(f"\nValidation result: {result}")
    print(f"Total rules: {result.get('total_rules', 'N/A')}")
    print(f"Valid rules: {result.get('valid_rules', 'N/A')}")
    print(f"Invalid rules: {result.get('invalid_rules', 'N/A')}")
    print(f"Warnings: {result.get('warnings', [])}")
    print(f"Dangerous operations: {result.get('dangerous_operations', [])}")
    
    # 检查是否有任何警告
    warnings = result.get('warnings', [])
    print(f"\nNumber of warnings: {len(warnings)}")
    
    for i, warning in enumerate(warnings):
        print(f"Warning {i+1}: {warning}")
    
    # 检查是否有递归相关的警告
    depth_warnings = [w for w in warnings 
                     if isinstance(w, dict) and (
                         "recursive" in w.get("message", "").lower() or 
                         "depth" in w.get("message", "").lower() or
                         "chain" in w.get("message", "").lower()
                     )]
    
    print(f"\nDepth-related warnings: {len(depth_warnings)}")
    for warning in depth_warnings:
        print(f"  - {warning}")
    
    # 这个测试总是通过，只是为了调试
    assert True

if __name__ == "__main__":
    asyncio.run(test_debug_recursive_replacement_depth())