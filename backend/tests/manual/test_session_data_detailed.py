#!/usr/bin/env python3
"""
详细测试会话数据存储和获取
"""

import asyncio
import requests
import json
import os

BASE_URL = "http://localhost:8000"

async def test_session_data_detailed():
    print("=== 详细测试会话数据存储和获取 ===")
    
    # 1. 上传EPUB文件
    print("\n1. 上传EPUB文件...")
    
    with open("references/simple.epub", "rb") as f:
        files = {"file": ("simple.epub", f, "application/epub+zip")}
        response = requests.post(f"{BASE_URL}/api/v1/upload/epub", files=files)
    
    print(f"上传响应状态码: {response.status_code}")
    print(f"上传响应内容: {response.text}")
    
    if response.status_code != 200:
        print("❌ 上传失败")
        return
    
    upload_data = response.json()
    session_id = upload_data["data"]["session_id"]
    print(f"✓ 上传成功! Session ID: {session_id}")
    
    # 2. 直接调用会话服务API测试会话数据
    print("\n2. 测试会话数据获取...")
    
    # 获取会话信息
    session_response = requests.get(f"{BASE_URL}/api/v1/sessions/{session_id}")
    print(f"会话信息响应状态码: {session_response.status_code}")
    print(f"会话信息响应内容: {session_response.text}")
    
    # 3. 测试文件树获取
    print("\n3. 测试文件树获取...")
    
    tree_response = requests.get(f"{BASE_URL}/api/v1/files/tree?session_id={session_id}")
    print(f"文件树响应状态码: {tree_response.status_code}")
    print(f"文件树响应内容: {tree_response.text[:500]}..." if len(tree_response.text) > 500 else f"文件树响应内容: {tree_response.text}")
    
    # 4. 测试批量替换
    print("\n4. 测试批量替换...")
    
    replace_data = {
        "rules": [
            {"old_text": "test", "new_text": "测试"}
        ]
    }
    
    replace_response = requests.post(
        f"{BASE_URL}/api/v1/batch-replace/execute",
        params={"session_id": session_id, "case_sensitive": False, "use_regex": False},
        json=replace_data
    )
    
    print(f"批量替换响应状态码: {replace_response.status_code}")
    print(f"批量替换响应内容: {replace_response.text}")
    
    if replace_response.status_code == 200:
        print("✓ 批量替换成功!")
    else:
        print("❌ 批量替换失败")

if __name__ == "__main__":
    asyncio.run(test_session_data_detailed())