#!/usr/bin/env python3
"""测试批量替换功能"""

import requests
import os

def test_batch_replace():
    """测试批量替换功能"""
    
    # 1. 首先上传EPUB文件
    print("1. 上传EPUB文件...")
    epub_path = "/Users/doudouda/Downloads/Personal_doc/Study/Proj/AetherFolio-web-Epub-editor/references/别有用心的恋爱史 미필적 고의에 의한 연애사_org.epub"
    
    with open(epub_path, 'rb') as f:
        files = {'file': ('test.epub', f, 'application/epub+zip')}
        response = requests.post(
            'http://localhost:8000/api/v1/upload/epub',
            files=files,
            timeout=30
        )
    
    if response.status_code != 200:
        print(f"上传失败: {response.status_code} - {response.text}")
        return
    
    upload_result = response.json()
    session_id = upload_result['data']['session_id']
    print(f"✓ 上传成功! Session ID: {session_id}")
    
    # 2. 执行批量替换（包含规则文件上传）
    print("\n2. 执行批量替换...")
    rules_path = "/Users/doudouda/Downloads/Personal_doc/Study/Proj/AetherFolio-web-Epub-editor/references/rules-别有用心.txt"
    
    with open(rules_path, 'rb') as f:
        files = {'rules_file': ('rules.txt', f, 'text/plain')}
        params = {
            'session_id': session_id,
            'case_sensitive': False,
            'use_regex': False
        }
        response = requests.post(
            'http://localhost:8000/api/v1/batch-replace/execute',
            files=files,
            params=params,
            timeout=60
        )
    
    if response.status_code != 200:
        print(f"批量替换失败: {response.status_code} - {response.text}")
        return
    
    replace_result = response.json()
    print("✓ 批量替换任务已启动!")
    print(f"  任务信息: {replace_result.get('data', {})}")
    
    # 3. 获取替换报告
    print("\n3. 获取替换报告...")
    response = requests.get(
        f'http://localhost:8000/api/v1/batch-replace/report/{session_id}',
        timeout=30
    )
    
    if response.status_code != 200:
        print(f"获取报告失败: {response.status_code} - {response.text}")
        return
    
    print("✓ 报告获取成功!")
    
    # 4. 下载处理后的EPUB
    print("\n4. 下载处理后的EPUB...")
    response = requests.get(
        f'http://localhost:8000/api/v1/export/{session_id}',
        timeout=30
    )
    
    if response.status_code != 200:
        print(f"下载失败: {response.status_code} - {response.text}")
        return
    
    # 保存下载的文件
    output_path = "processed_epub.epub"
    with open(output_path, 'wb') as f:
        f.write(response.content)
    
    print(f"✓ 下载成功! 文件保存为: {output_path}")
    print(f"  文件大小: {len(response.content)} bytes")
    
    print("\n🎉 批量替换流程测试完成!")

if __name__ == "__main__":
    test_batch_replace()