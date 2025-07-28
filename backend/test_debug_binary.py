#!/usr/bin/env python3
"""
调试二进制文件和UTF-8测试的API响应格式
"""

import pytest
from fastapi.testclient import TestClient
from io import BytesIO
from backend.main import app

client = TestClient(app)

def create_binary_file(content: bytes, filename: str = "test_rules.txt") -> tuple:
    """创建二进制测试文件"""
    return (
        filename,
        BytesIO(content),
        "text/plain"
    )

def test_debug_binary_content():
    """调试二进制文件内容响应"""
    print("\n=== Testing binary file content ===")
    
    binary_content = b'\x00\x01\x02\x03\xFF\xFE\xFD\xFC' + b'test -> replacement'
    files = {"rules_file": create_binary_file(binary_content)}
    
    response = client.post("/api/v1/batch-replace/validate", files=files)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Text: {response.text}")
    
    try:
        json_response = response.json()
        print(f"JSON Response: {json_response}")
        
        if 'message' in json_response:
            print(f"Message: {json_response['message']}")
        if 'error' in json_response:
            print(f"Error: {json_response['error']}")
        if 'data' in json_response:
            print(f"Data: {json_response['data']}")
        
    except Exception as e:
        print(f"Failed to parse JSON: {e}")
    
    assert True

def test_debug_malformed_utf8():
    """调试格式错误的UTF-8响应"""
    print("\n=== Testing malformed UTF-8 ===")
    
    invalid_utf8 = b'\xFF\xFE' + "test -> replacement".encode('utf-8')
    files = {"rules_file": create_binary_file(invalid_utf8)}
    
    response = client.post("/api/v1/batch-replace/validate", files=files)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Text: {response.text}")
    
    try:
        json_response = response.json()
        print(f"JSON Response: {json_response}")
        
        if 'message' in json_response:
            print(f"Message: {json_response['message']}")
        if 'error' in json_response:
            print(f"Error: {json_response['error']}")
        if 'data' in json_response:
            print(f"Data: {json_response['data']}")
        
    except Exception as e:
        print(f"Failed to parse JSON: {e}")
    
    assert True