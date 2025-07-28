#!/usr/bin/env python3

import requests
import json
import tempfile
import os

def test_debug_redos_api():
    """调试ReDoS API测试"""
    
    # 创建包含ReDoS模式的测试文件
    redos_content = """# ReDoS攻击测试
(a+)+b -> replacement | Catastrophic backtracking | regex
(x+x+)+y -> replacement | Another ReDoS pattern | regex
([a-zA-Z]+)*$ -> replacement | Nested quantifiers | regex
"""
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(redos_content)
        temp_file_path = f.name
    
    try:
        # 发送API请求
        with open(temp_file_path, 'rb') as f:
            files = {'rules_file': f}
            response = requests.post('http://localhost:8000/api/v1/batch-replace/validate', files=files)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Text: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response JSON: {json.dumps(data, indent=2)}")
            
            if 'data' in data:
                validation_result = data['data']
                print(f"Is Valid: {validation_result.get('is_valid')}")
                print(f"Total Rules: {validation_result.get('total_rules')}")
                print(f"Valid Rules: {validation_result.get('valid_rules')}")
                print(f"Invalid Rules: {validation_result.get('invalid_rules')}")
                print(f"Warnings: {validation_result.get('warnings_count')}")
                print(f"Dangerous Operations: {validation_result.get('dangerous_operations_count')}")
                
                if 'warnings' in validation_result:
                    print("\nWarnings:")
                    for warning in validation_result['warnings']:
                        print(f"  - {warning}")
                        
                if 'dangerous_operations' in validation_result:
                    print("\nDangerous Operations:")
                    for danger in validation_result['dangerous_operations']:
                        print(f"  - {danger}")
        else:
            print(f"Error response: {response.text}")
            
    finally:
        # 清理临时文件
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

if __name__ == "__main__":
    test_debug_redos_api()