#!/usr/bin/env python3
"""
测试脚本 - 验证Key处理逻辑和API响应格式
"""

import requests
import json
import time

# 测试配置
BASE_URL = "http://localhost:8080"
TEST_KEYS = [
    # 特殊格式key（应该被识别并直接使用）
    "70454cb612aa41ea8a04a602940e625f.5Xo9fjl3OX8SB6A1",
    "0886879b91f241459457e61d92dfa3ad.nmoXRmIOBXh7xeBz",
    # 普通key（应该回退到默认模式）
    "sk-test-key-12345",
    "invalid-key"
]

def test_key_format_detection():
    """测试key格式检测"""
    from app.utils.helpers import is_special_key_format
    
    print("🔍 测试Key格式检测...")
    
    test_cases = [
        ("70454cb612aa41ea8a04a602940e625f.5Xo9fjl3OX8SB6A1", True),
        ("0886879b91f241459457e61d92dfa3ad.nmoXRmIOBXh7xeBz", True),
        ("sk-test-key", False),
        ("invalid", False),
        ("", False),
        ("70454cb612aa41ea8a04a602940e625f", False),  # 缺少点号和后缀
        ("not-hex.suffix", False),  # 非十六进制
    ]
    
    for key, expected in test_cases:
        result = is_special_key_format(key)
        status = "✅" if result == expected else "❌"
        print(f"{status} {key[:20]}... -> {result} (期望: {expected})")

def test_models_endpoint():
    """测试模型列表端点"""
    print("\n📋 测试模型列表端点...")
    
    try:
        response = requests.get(f"{BASE_URL}/v1/models")
        if response.status_code == 200:
            data = response.json()
            print("✅ 模型列表获取成功")
            print(f"   可用模型数量: {len(data.get('data', []))}")
            for model in data.get('data', []):
                print(f"   - {model.get('id')}")
        else:
            print(f"❌ 模型列表获取失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")

def test_chat_completion(api_key, key_type):
    """测试聊天完成端点"""
    print(f"\n💬 测试聊天完成 ({key_type})...")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "GLM-4.5",
        "messages": [
            {"role": "user", "content": "Hello! This is a test message."}
        ],
        "stream": False,
        "max_tokens": 50
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 请求成功")
            print(f"   响应ID: {data.get('id')}")
            print(f"   模型: {data.get('model')}")
            print(f"   选择数量: {len(data.get('choices', []))}")
            if data.get('choices'):
                choice = data['choices'][0]
                print(f"   完成原因: {choice.get('finish_reason')}")
                message = choice.get('message', {})
                content = message.get('content', '')
                print(f"   内容长度: {len(content)}")
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")

def test_streaming_response(api_key, key_type):
    """测试流式响应"""
    print(f"\n🌊 测试流式响应 ({key_type})...")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "GLM-4.5",
        "messages": [
            {"role": "user", "content": "Count from 1 to 5"}
        ],
        "stream": True,
        "max_tokens": 30
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            headers=headers,
            json=payload,
            stream=True,
            timeout=30
        )
        
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ 流式响应开始")
            chunk_count = 0
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        chunk_count += 1
                        data_str = line_str[6:]  # 去掉 'data: '
                        if data_str == '[DONE]':
                            print(f"   流式响应完成，共收到 {chunk_count} 个块")
                            break
                        try:
                            chunk_data = json.loads(data_str)
                            if chunk_count <= 3:  # 只显示前3个块的详情
                                print(f"   块 {chunk_count}: {json.dumps(chunk_data, ensure_ascii=False)[:100]}...")
                        except json.JSONDecodeError:
                            pass
        else:
            print(f"❌ 流式请求失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 流式请求异常: {e}")

def main():
    """主测试函数"""
    print("🚀 开始API测试...")
    print("=" * 50)
    
    # 测试key格式检测
    test_key_format_detection()
    
    # 测试模型端点
    test_models_endpoint()
    
    # 测试不同类型的key
    for i, key in enumerate(TEST_KEYS[:2]):  # 只测试前两个key
        key_type = "特殊格式Key" if i < 2 else "普通Key"
        
        # 测试非流式响应
        test_chat_completion(key, key_type)
        
        # 测试流式响应
        test_streaming_response(key, key_type)
        
        time.sleep(1)  # 避免请求过快
    
    print("\n" + "=" * 50)
    print("🎉 测试完成！")

if __name__ == "__main__":
    main()