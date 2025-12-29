#!/bin/bash
# 阿里云API版本快速启动脚本

set -e

echo "========================================="
echo "SafetyVision-RAG 阿里云API版本启动脚本"
echo "========================================="
echo

# 检查.env文件
if [ ! -f .env ]; then
    echo "⚠️  未找到.env文件，正在从示例创建..."
    if [ -f .env.aliyun.example ]; then
        cp .env.aliyun.example .env
        echo "✅ 已创建.env文件，请编辑并填入你的DASHSCOPE_API_KEY"
        echo
        echo "获取API Key: https://help.aliyun.com/zh/model-studio/get-api-key"
        echo
        read -p "按Enter继续（确保已配置API Key）..." 
    else
        echo "❌ 未找到.env.aliyun.example文件"
        exit 1
    fi
fi

# 检查API Key
source .env
if [ -z "$DASHSCOPE_API_KEY" ] || [ "$DASHSCOPE_API_KEY" == "sk-your-api-key-here" ]; then
    echo "❌ 请先在.env文件中配置DASHSCOPE_API_KEY"
    echo "   编辑命令: nano .env"
    exit 1
fi

echo "✅ API Key已配置"
echo

# 显示配置信息
echo "📋 当前配置:"
echo "   - VLM模型: ${VLM_MODEL_NAME:-qwen3-vl-plus}"
echo "   - LLM模型: ${LLM_MODEL_NAME:-qwen3-max-preview}"
echo "   - Base URL: ${DASHSCOPE_BASE_URL:-https://dashscope.aliyuncs.com/compatible-mode/v1}"
echo

# 启动服务
echo "🚀 启动服务..."
docker compose -f docker-compose.aliyun.yaml up -d

echo
echo "✅ 服务启动完成！"
echo
echo "📡 服务访问地址:"
echo "   - API文档: http://localhost:8080/docs"
echo "   - Chainlit UI: http://localhost:25810"
echo "   - Qdrant管理: http://localhost:6333/dashboard"
echo
echo "📊 查看日志: docker compose -f docker-compose.aliyun.yaml logs -f"
echo "🛑 停止服务: docker compose -f docker-compose.aliyun.yaml down"
