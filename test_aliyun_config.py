#!/usr/bin/env python3
"""
测试阿里云API配置是否正确
"""

import os
import sys
from openai import OpenAI

def test_dashscope_api():
    """测试阿里云DashScope API连接"""
    
    api_key = os.getenv("DASHSCOPE_API_KEY")
    base_url = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    
    if not api_key:
        print("❌ 错误: 未设置DASHSCOPE_API_KEY环境变量")
        print("   请先配置: export DASHSCOPE_API_KEY=sk-your-key")
        return False
    
    print("🔍 测试阿里云API连接...")
    print(f"   API Key: {api_key[:10]}...{api_key[-4:]}")
    print(f"   Base URL: {base_url}")
    print()
    
    try:
        # 测试文本模型
        print("1️⃣ 测试文本模型 (qwen3-max-preview)...")
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        response = client.chat.completions.create(
            model="qwen3-max-preview",
            messages=[
                {"role": "system", "content": "你是一个友好的助手"},
                {"role": "user", "content": "请用一句话介绍你自己"}
            ],
            max_tokens=100
        )
        
        print(f"✅ 文本模型响应: {response.choices[0].message.content}")
        print()
        
        # 测试多模态模型（不需要实际图片，只测试模型可用性）
        print("2️⃣ 测试多模态模型 (qwen3-vl-plus)...")
        response = client.chat.completions.create(
            model="qwen3-vl-plus",
            messages=[
                {"role": "user", "content": "你好"}
            ],
            max_tokens=50
        )
        
        print(f"✅ 多模态模型响应: {response.choices[0].message.content}")
        print()
        
        print("=" * 50)
        print("✅ 所有测试通过！阿里云API配置正确")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        print()
        print("常见问题排查:")
        print("1. 检查API Key是否正确")
        print("2. 检查网络是否能访问阿里云")
        print("3. 检查API Key是否有qwen模型的访问权限")
        print("4. 确认API Key是否过期")
        return False

def test_env_file():
    """测试.env文件配置"""
    print("📋 检查.env文件配置...")
    
    if not os.path.exists(".env"):
        print("⚠️  未找到.env文件")
        if os.path.exists(".env.aliyun.example"):
            print("   建议: cp .env.aliyun.example .env")
        return False
    
    print("✅ .env文件存在")
    
    # 读取并显示关键配置
    with open(".env", "r") as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                if "DASHSCOPE_API_KEY" in line:
                    key, value = line.split("=", 1)
                    if value and value != "sk-your-api-key-here":
                        print(f"✅ {key}已配置")
                    else:
                        print(f"⚠️  {key}未配置或使用默认值")
                        return False
                elif any(x in line for x in ["MODEL_NAME", "BASE_URL"]):
                    print(f"   {line}")
    
    print()
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("SafetyVision-RAG 阿里云API配置测试")
    print("=" * 50)
    print()
    
    # 测试.env文件
    if not test_env_file():
        print("请先配置.env文件")
        sys.exit(1)
    
    # 加载.env文件
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ 已加载.env配置")
        print()
    except ImportError:
        print("⚠️  未安装python-dotenv，将使用系统环境变量")
        print("   安装: pip install python-dotenv")
        print()
    
    # 测试API连接
    success = test_dashscope_api()
    
    sys.exit(0 if success else 1)
