#!/usr/bin/env python3
"""
调试API响应格式的测试
"""

import pytest
from fastapi.testclient import TestClient
from io import BytesIO
from backend.main import app

client = TestClient(app)

def create_test_file(content: str, filename: str = "test_rules.txt", content_type: str = "text/plain") -> tuple:
    """创建测试文件"""
    file_content = content.encode('utf-8')
    return (
        filename,
        BytesIO(file_content),
        content_type
    )

def test_debug_malicious_extension():
    """调试恶意文件扩展名响应"""
    print("\n=== Testing malicious file extension ===")
    
    files = {"rules_file": create_test_file("test -> replacement", "malicious.exe")}
    
    response = client.post("/api/v1/batch-replace/validate", files=files)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Text: {response.text}")
    
    try:
        json_response = response.json()
        print(f"JSON Response: {json_response}")
        print(f"Detail type: {type(json_response.get('detail', 'N/A'))}")
        print(f"Detail content: {json_response.get('detail', 'N/A')}")
        
        # 检查detail结构
        detail = json_response.get('detail', {})
        if isinstance(detail, dict):
            print(f"Detail keys: {list(detail.keys())}")
            print(f"Message: {detail.get('message', 'N/A')}")
        
    except Exception as e:
        print(f"Failed to parse JSON: {e}")
    
    # 这个测试总是通过，只是为了调试
    assert True

def test_debug_empty_filename():
    """调试空文件名响应"""
    print("\n=== Testing empty filename ===")
    
    files = {"rules_file": create_test_file("test -> replacement", "")}
    
    response = client.post("/api/v1/batch-replace/validate", files=files)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Text: {response.text}")
    
    try:
        json_response = response.json()
        print(f"JSON Response: {json_response}")
        
        # 检查detail结构
        detail = json_response.get('detail', {})
        if isinstance(detail, dict):
            print(f"Detail keys: {list(detail.keys())}")
            print(f"Message: {detail.get('message', 'N/A')}")
        elif isinstance(detail, list):
            print(f"Detail is list with {len(detail)} items")
            for i, item in enumerate(detail):
                print(f"  Item {i}: {item}")
        
    except Exception as e:
        print(f"Failed to parse JSON: {e}")
    
    # 这个测试总是通过，只是为了调试
    assert True