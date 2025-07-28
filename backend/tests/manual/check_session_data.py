#!/usr/bin/env python3

import requests
import json

def check_session_data():
    base_url = "http://localhost:8000/api/v1"
    
    # 1. 上传EPUB文件
    print("1. 上传EPUB文件...")
    epub_path = "references/simple.epub"
    
    with open(epub_path, 'rb') as f:
        files = {'file': (epub_path, f, 'application/epub+zip')}
        response = requests.post(f"{base_url}/upload/epub", files=files)
    
    if response.status_code != 200:
        print(f"上传失败: {response.status_code} - {response.text}")
        return
    
    upload_result = response.json()
    session_id = upload_result['data']['session_id']
    print(f"✓ 上传成功! Session ID: {session_id}")
    
    # 2. 检查会话信息
    print("\n2. 检查会话信息...")
    response = requests.get(f"{base_url}/sessions/{session_id}")
    if response.status_code == 200:
        session_info = response.json()
        print(f"会话信息: {json.dumps(session_info, indent=2, ensure_ascii=False)}")
    else:
        print(f"获取会话信息失败: {response.status_code} - {response.text}")
    
    # 3. 尝试获取文件树
    print("\n3. 尝试获取文件树...")
    response = requests.get(f"{base_url}/files/tree", params={'session_id': session_id})
    if response.status_code == 200:
        print("✓ 文件树获取成功")
    else:
        print(f"文件树获取失败: {response.status_code} - {response.text}")

if __name__ == "__main__":
    check_session_data()