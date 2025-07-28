#!/usr/bin/env python3
"""简单的EPUB上传测试"""

import requests
import sys
import os

def test_upload_epub():
    """测试上传EPUB文件"""
    epub_path = "/Users/doudouda/Downloads/Personal_doc/Study/Proj/AetherFolio-web-Epub-editor/references/别有用心的恋爱史 미필적 고의에 의한 연애사_org.epub"
    
    if not os.path.exists(epub_path):
        print(f"EPUB文件不存在: {epub_path}")
        return False
    
    print(f"开始上传EPUB文件: {epub_path}")
    
    try:
        with open(epub_path, 'rb') as f:
            files = {
                'file': ('test.epub', f, 'application/epub+zip')
            }
            
            response = requests.post(
                'http://localhost:8000/api/v1/upload/epub',
                files=files,
                timeout=30
            )
            
            print(f"响应状态码: {response.status_code}")
            print(f"响应头: {response.headers}")
            print(f"响应内容: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"上传成功! Session ID: {data.get('data', {}).get('session_id')}")
                return True
            else:
                print(f"上传失败: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        print(f"上传过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_upload_epub()
    sys.exit(0 if success else 1)