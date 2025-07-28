#!/usr/bin/env python3

import requests
import json

def check_sessions():
    """检查当前活跃的会话"""
    base_url = "http://localhost:8000"
    
    try:
        # 获取会话列表
        response = requests.get(f"{base_url}/api/v1/sessions")
        
        if response.status_code == 200:
            response_data = response.json()
            sessions = response_data.get('data', [])
            print(f"当前活跃会话数量: {len(sessions)}")
            
            if sessions:
                print("\n活跃会话列表:")
                for session in sessions:
                    if isinstance(session, dict):
                        print(f"  - Session ID: {session.get('session_id', 'N/A')}")
                        print(f"    创建时间: {session.get('created_at', 'N/A')}")
                        print(f"    过期时间: {session.get('expires_at', 'N/A')}")
                        print(f"    文件名: {session.get('original_filename', 'N/A')}")
                    else:
                        print(f"  - Session: {session}")
                    print()
            else:
                print("没有活跃的会话")
        else:
            print(f"获取会话列表失败: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"检查会话时出错: {e}")

if __name__ == "__main__":
    check_sessions()