#!/bin/bash
set -e

echo "==================================="
echo "SafetyVision-RAG System Initializing"
echo "==================================="

# 等待 Qdrant 服务就绪
echo "等待 Qdrant 服务启动..."
until curl -sf http://qdrant-server:6333/ > /dev/null 2>&1; do
    echo "Qdrant 未就绪，等待中..."
    sleep 2
done
echo "✅ Qdrant 服务就绪"

# 等待 VLM (Qwen-VL) 服务就绪
echo "等待 VLM (Qwen-VL) 服务启动..."
until curl -sf http://vllm-qwen-vl:8000/health > /dev/null 2>&1; do
    echo "VLM 服务未就绪，等待中..."
    sleep 5
done
echo "✅ VLM (Qwen-VL) 服务就绪"

# 等待 Embedding (BGE-m3) 服务就绪
echo "等待 Embedding (BGE-m3) 服务启动..."
until curl -sf http://vllm-bge-m3:8000/health > /dev/null 2>&1; do
    echo "Embedding 服务未就绪，等待中..."
    sleep 2
done
echo "✅ Embedding (BGE-m3) 服务就绪"

echo "==================================="
echo "All Services Ready - Starting API"
echo "==================================="

# 启动 API 服务
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
