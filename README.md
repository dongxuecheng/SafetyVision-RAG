# SafetyVision-RAG

AI-Powered Safety Hazard Detection System using Vision-Language Models and Retrieval-Augmented Generation.

**基于视觉-语言模型和检索增强生成的AI安全隐患检测系统**

[![FastAPI](https://img.shields.io/badge/FastAPI-2.0.0-009688.svg)](https://fastapi.tiangolo.com)
[![Qdrant](https://img.shields.io/badge/Qdrant-1.15+-DC382D.svg)](https://qdrant.tech)
[![vLLM](https://img.shields.io/badge/vLLM-latest-4B8BBE.svg)](https://github.com/vllm-project/vllm)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 功能特性

- ✅ 图像安全违规检测（使用 Qwen3-VL-4B 视觉模型）
- ✅ PDF 文档上传与向量化存储
- ✅ 文档管理（上传、删除、列表）
- ✅ 基于语义检索的问答
- ✅ 支持批量操作和去重

## 📐 系统架构

```
┌──────────────────────────────────────────┐
│       SafetyVision-RAG API (8080)        │
│  FastAPI + LangChain + Vision-Language   │
└────────────────┬─────────────────────────┘
                 │
      ┌──────────┼──────────┐
      ↓          ↓          ↓
┌─────────┐ ┌─────────┐ ┌─────────┐
│ Qdrant  │ │Qwen3-VL │ │ BGE-m3  │
│  6333   │ │  8000   │ │  8000   │
└─────────┘ └─────────┘ └─────────┘
向量数据库    视觉模型    嵌入模型
```

## 快速开始

### 1. 启动服务

```bash
docker-compose up -d
```

### 2. 等待服务就绪

```bash
# 检查服务状态
docker-compose ps

# 查看日志
docker-compose logs -f safetyvision-api
```

### 3. 访问 API 文档

浏览器打开: http://localhost:8000/docs

## API 使用指南

### 图像安全分析

```bash
# 分析单张图片
curl -X POST "http://localhost:8000/analyze" \
  -F "file=@image.jpg"
```

### 文档管理

#### 1. 上传文档

```bash
# 上传单个 PDF
curl -X POST "http://localhost:8000/api/documents/upload?skip_existing=true" \
  -F "files=@document.pdf"

# 批量上传（使用脚本）
./scripts/batch_upload_pdfs.sh ./file http://localhost:8000
```

#### 2. 查看文档列表

```bash
curl -X GET "http://localhost:8000/api/documents"
```

#### 3. 删除文档

```bash
# 删除单个文档
curl -X DELETE "http://localhost:8000/api/documents" \
  -H "Content-Type: application/json" \
  -d '{"document_names": ["document.pdf"]}'

# 批量删除
curl -X DELETE "http://localhost:8000/api/documents" \
  -H "Content-Type: application/json" \
  -d '{"document_names": ["doc1.pdf", "doc2.pdf"]}'
```

## 批量上传脚本

提供了便捷的批量上传脚本，用于初始化或迁移大量 PDF 文件：

```bash
# 基本用法
./scripts/batch_upload_pdfs.sh /path/to/pdf/directory

# 指定 API 地址
./scripts/batch_upload_pdfs.sh /path/to/pdf/directory http://localhost:8000

# 示例
./scripts/batch_upload_pdfs.sh ./file
```

脚本特性：
- ✅ 自动跳过已存在的文档
- ✅ 详细的上传进度显示
- ✅ 统计成功/失败数量
- ✅ 错误处理和日志记录

## 配置说明

### 环境变量（docker-compose.yaml）

```yaml
environment:
  - QDRANT_URL=http://qdrant-server:6333
  - COLLECTION_NAME=rag-test
  - VLM_URL=http://vllm-qwen3-vl:8001/v1
  - EMBEDDING_URL=http://vllm-bge-m3:8000/v1
```

### 文本分割参数（main.py）

```python
chunk_size = 500        # 每个文本块的大小
chunk_overlap = 50      # 文本块之间的重叠
```

## 数据持久化

- Qdrant 数据存储在 Docker volume `qdrant_storage` 中
- 重启容器不会丢失数据
- 如需清空数据：`docker-compose down -v`

## 常见问题

### 1. 如何批量导入已有 PDF？

使用批量上传脚本：
```bash
./scripts/batch_upload_pdfs.sh ./your-pdf-directory
```

### 2. 如何避免重复文档？

所有上传 API 默认使用 `skip_existing=true` 参数，会自动跳过已存在的文档。

### 3. 如何清空所有文档？

```bash
# 方法1: 删除 Qdrant collection（推荐）
curl -X DELETE "http://localhost:6333/collections/rag-test"

# 方法2: 重建 volume
docker-compose down -v
docker-compose up -d
```

### 4. 服务启动失败怎么办？

```bash
# 查看日志
docker-compose logs rag-api
docker-compose logs qdrant-server
docker-compose logs vllm-bge-m3

# 重启服务
docker-compose restart
```

## 开发指南

### 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 启动依赖服务
docker-compose up -d qdrant-server vllm-bge-m3 vllm-qwen3-vl

# 本地运行 API
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 测试

```bash
# 测试图像分析
python -c "
import requests
response = requests.post('http://localhost:8000/analyze', 
    files={'file': open('test.jpg', 'rb')})
print(response.json())
"

# 测试文档上传
curl -X POST "http://localhost:8000/api/documents/upload" \
  -F "files=@test.pdf"
```

## 性能优化建议

1. **批量上传**: 使用批量上传接口，减少网络开销
2. **并发控制**: 默认单线程处理，避免 OOM
3. **文本分割**: 根据文档类型调整 chunk_size
4. **模型选择**: 
   - BGE-m3: 高质量多语言嵌入
   - Qwen3-VL-4B: 高性能视觉理解

## 许可证

MIT License

## 更新日志

### v2.0.0 (2025-11-13) - SafetyVision-RAG
- ✅ 项目重命名为 SafetyVision-RAG
- ✅ 移除 `load_pdf.py`，简化架构
- ✅ 完善文档管理 API（上传、删除、列表）
- ✅ 新增批量上传脚本
- ✅ 优化数据持久化（项目目录存储）
- ✅ 完善健康检查机制
- ✅ 优化错误处理和日志

### v1.0.0 (2025-11-10)
- ✅ 初始版本
- ✅ 图像安全分析
- ✅ PDF 文档加载
