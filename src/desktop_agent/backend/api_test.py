# test_api.py
import os
import requests
import json
from datetime import datetime

# 设置环境变量（使用你生成的token）
API_URL = "http://127.0.0.1:8001"  # 根据你的实际端口调整
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJuYV91c3Jfc1U0S3pQeWFFVjdLS0FoSVhMM3kiLCJlbWFpbCI6ImRlZmF1bHRAc3lzdGVtLmxvY2FsIiwibmFtZSI6IkRlZmF1bHQgU3lzdGVtIFVzZXIiLCJleHAiOjE3ODYwODA4NDN9.42miae0EIiCSzR0RwXF0EWJwqqDqII5HqyhWjWdULGQ"


def test_api_endpoints():
    """测试API端点的可访问性"""

    endpoints_to_test = [
        # 测试不需要认证的端点
        ("GET", "/", "根路径"),
        ("GET", "/health", "健康检查"),

        # 测试需要认证的端点（应该在移除认证后变成不需要认证）
        ("POST", "/apps/threads", "创建线程"),
    ]

    headers_without_auth = {"Content-Type": "application/json"}
    headers_with_auth = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TOKEN}"
    }

    print("=" * 60)
    print("API 端点测试")
    print("=" * 60)

    for method, endpoint, description in endpoints_to_test:
        url = f"{API_URL}{endpoint}"

        print(f"\n🔍 测试: {description}")
        print(f"URL: {method} {url}")

        # 测试不带认证
        print("\n📋 不带认证:")
        try:
            if method == "GET":
                response = requests.get(url, headers=headers_without_auth, timeout=5)
            elif method == "POST":
                # 对于POST请求，提供基本的有效载荷
                payload = {"task": "test task"} if "threads" in endpoint else {}
                response = requests.post(url, json=payload, headers=headers_without_auth, timeout=5)

            print(f"  状态码: {response.status_code}")
            print(f"  响应: {response.text[:200]}...")

        except Exception as e:
            print(f"  ❌ 错误: {e}")

        # 测试带认证
        print("\n🔑 带认证:")
        try:
            if method == "GET":
                response = requests.get(url, headers=headers_with_auth, timeout=5)
            elif method == "POST":
                payload = {"task": "test task"} if "threads" in endpoint else {}
                response = requests.post(url, json=payload, headers=headers_with_auth, timeout=5)

            print(f"  状态码: {response.status_code}")
            print(f"  响应: {response.text[:200]}...")

        except Exception as e:
            print(f"  ❌ 错误: {e}")

        print("-" * 40)


def check_token_validity():
    """检查token的有效性"""
    import jwt

    print("\n" + "=" * 60)
    print("Token 验证")
    print("=" * 60)

    try:
        # 不验证签名，只解码查看内容
        decoded = jwt.decode(TOKEN, options={"verify_signature": False})
        print("✅ Token 解码成功:")
        for key, value in decoded.items():
            if key == 'exp':
                exp_date = datetime.fromtimestamp(value)
                print(f"  {key}: {value} ({exp_date})")
            else:
                print(f"  {key}: {value}")

        # 检查是否过期
        exp_timestamp = decoded.get('exp')
        if exp_timestamp:
            exp_date = datetime.fromtimestamp(exp_timestamp)
            if datetime.now() > exp_date:
                print("⚠️  Token 已过期!")
            else:
                print("✅ Token 仍然有效")

    except Exception as e:
        print(f"❌ Token 解码失败: {e}")


def test_specific_endpoint():
    """测试特定的失败端点"""
    url = f"{API_URL}/apps/threads"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TOKEN}"
    }
    payload = {"task": "test desktop task"}

    print("\n" + "=" * 60)
    print("具体端点测试")
    print("=" * 60)
    print(f"URL: POST {url}")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"\n状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        print(f"响应体: {response.text}")

    except Exception as e:
        print(f"❌ 请求失败: {e}")


if __name__ == "__main__":
    print("开始测试 NeuralAgent API...")
    check_token_validity()
    test_specific_endpoint()
    test_api_endpoints()
