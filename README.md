# SafetyVision-RAG

AI-Powered Safety Hazard Detection System using Vision-Language Models and Retrieval-Augmented Generation.

**基于视觉-语言模型和检索增强生成的AI安全隐患检测系统**

[![FastAPI](https://img.shields.io/badge/FastAPI-2.0.0-009688.svg)](https://fastapi.tiangolo.com)
[![LangChain](https://img.shields.io/badge/LangChain-1.0+-1C3C3C.svg)](https://python.langchain.com)
[![Qdrant](https://img.shields.io/badge/Qdrant-1.15+-DC382D.svg)](https://qdrant.tech)
[![vLLM](https://img.shields.io/badge/vLLM-latest-4B8BBE.svg)](https://github.com/vllm-project/vllm)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## ✨ 功能特性

### 核心功能
- 🎯 **智能图像分析**：使用 Qwen-VL-4B 多模态大模型识别安全隐患
- 📋 **结构化输出**：自动提取隐患描述、整改建议、规范引用
- 📚 **源文档溯源**：每条违规记录附带引用文档的文件名和精确位置
- 🔍 **高质量检索**：基于 BGE-m3 嵌入 + BGE-Reranker-v2-M3 重排序

### RAG 增强
- ✅ **多格式文档支持**：PDF、DOCX、DOC、XLSX、XLS
- ✅ **Excel 行级检索**：支持工作表名 + 行号的精确定位
- ✅ **相关性过滤**：相似度阈值 0.65 + Rerank 阈值 0.3
- ✅ **分数优化**：检索召回 30 条候选，重排序后取 Top-3
- ✅ **文档管理**：上传、删除、列表、去重

## 📐 系统架构

### 服务架构
```
┌─────────────────────────────────────────────────────┐
│          SafetyVision-RAG API (8080)                │
│   FastAPI + LangChain v1.0+ + Async/Await           │
│                                                     │
│  ┌──────────────┐  ┌────────────────────────────┐   │
│  │ VLM Pipeline │  │   RAG Pipeline             │   │
│  │ - 图像识别    │  │   - 相似度检索 (BGE-m3)    │   │
│  │ - 隐患提取    │  │   - 重排序 (Reranker-v2-M3)│   │
│  │ - 结构化输出  │  │   - 分数过滤 (0.65/0.3)     │   │
│  └──────────────┘  └────────────────────────────┘   │
└───────────────────────┬──────────────────────────┬──┘
                        ↓                          ↓
        ┌───────────────────────┐    ┌───────────────────┐
        │   Qdrant (6333)       │    │  vLLM GPU Cluster │
        │   向量数据库           │    │  ├─ Qwen-VL (8000)│
        │   - Collection管理    │    │  ├─ BGE-m3 (8001) │
        │   - 向量存储/检索      │    │  └─ Reranker(8002)│
        └───────────────────────┘    └───────────────────┘
```

### 代码架构（Clean Architecture）
```
SafetyVision-RAG/
├── app/                                # 应用主目录
│   ├── main.py                         # 应用入口 + 生命周期管理
│   │
│   ├── api/routes/                     # API 路由层（Presentation）
│   │   ├── analysis.py                 # 图像分析端点
│   │   └── documents.py                # 文档管理端点
│   │
│   ├── core/                           # 核心基础设施（Infrastructure）
│   │   ├── config.py                   # Pydantic Settings 配置
│   │   ├── deps.py                     # 依赖注入（DI Container）
│   │   └── retrieval.py                # 检索策略（Retriever）
│   │
│   ├── schemas/                        # 数据模型（DTO）
│   │   └── safety.py                   # API 请求/响应 Schema
│   │                                   #  - SafetyViolationLLM (LLM输出)
│   │                                   #  - SafetyViolation (完整模型)
│   │                                   #  - SourceReference (源文档引用)
│   │
│   └── services/                       # 业务逻辑层（Business Logic）
│       ├── analysis_service.py         # 安全分析服务
│       │   ├─ analyze_image()          #   主流程编排
│       │   ├─ _extract_hazards()       #   VLM 隐患提取
│       │   ├─ _batch_retrieve()        #   并行检索文档
│       │   └─ _generate_violation()    #   生成结构化违规
│       │
│       └── document_service.py         # 文档处理服务
│           ├─ upload_documents()       #   文档上传 + 向量化
│           ├─ delete_documents()       #   批量删除
│           └─ list_documents()         #   文档列表
│
├── src/document_processors.py          # 文档处理器工厂
│   ├─ PDFProcessor                     #   PDF 解析器
│   ├─ DOCXProcessor                    #   Word 解析器
│   └─ ExcelProcessor                   #   Excel 行级解析
│
└── file/                               # 上传文件存储目录
```

### 架构设计原则

**Clean Architecture 实践：**
- 🎯 **关注点分离**：API → Service → Retrieval → Data
- 🔌 **依赖注入**：使用 FastAPI `Depends()` 实现 IoC
- ⚙️ **配置管理**：Pydantic Settings 环境变量自动加载
- 📦 **类型安全**：完整的 Type Hints + Pydantic 验证
- 🧪 **可测试性**：服务层独立，易于 Mock 和单元测试

**LangChain v1.0+ 最佳实践：**
- ✅ `with_structured_output()`：类型安全的结构化输出
- ✅ `@chain` 装饰器：声明式 Pipeline 组合
- ✅ Async-first：全异步设计，支持并发
- ✅ Modular Retrieval：可组合的检索策略
- ✅ Document Metadata：完整的溯源信息

## 🚀 快速开始

### 前置要求

- Docker & Docker Compose
- NVIDIA GPU（支持 CUDA）
- 至少 16GB GPU 显存（推荐 24GB+）

### 1. 启动所有服务

```bash
# 启动 5 个容器（API + 3个模型 + Qdrant）
docker compose up -d

# 等待所有服务健康检查通过（约 2-3 分钟）
docker compose ps
```

### 2. 验证服务状态

```bash
# 查看服务日志
docker compose logs -f safetyvision-api

# 检查健康状态
curl http://localhost:8080/docs  # API 文档（Swagger UI）
curl http://localhost:28000/health  # Qwen-VL 健康检查
curl http://localhost:28001/health  # BGE-m3 健康检查
curl http://localhost:28002/health  # Reranker 健康检查
curl http://localhost:6333/health  # Qdrant 健康检查
```

### 3. 初始化文档库（可选）

```bash
# 上传安全规范文档到向量数据库
curl -X POST "http://localhost:8080/api/documents/upload" \
  -F "files=@safety_rules.pdf" \
  -F "files=@regulations.xlsx"
```

### 4. 测试图像分析

```bash
# 分析包含安全隐患的图片
curl -X POST "http://localhost:8080/api/analysis/image" \
  -F "file=@construction_site.jpg" \
  | jq .
```

**预期输出**：
```json
{
  "report_id": "uuid-xxx",
  "violations": [
    {
      "hazard_id": 1,
      "hazard_description": "作业人员未佩戴安全帽",
      "recommendations": "1. 立即停止作业并佩戴安全帽\n2. 加强现场安全教育",
      "rule_reference": "根据《建筑施工安全规范.xlsx》，施工现场必须佩戴安全帽",
      "source_documents": [
        {
          "filename": "建筑施工安全规范.xlsx",
          "location": "工作表: 个人防护, 行: 5"
        }
      ]
    }
  ]
}
```

## 📚 API 使用指南

### 端点概览

| 端点 | 方法 | 功能 | 端口 |
|------|------|------|------|
| `/api/analysis/image` | POST | 图像安全分析 | 8080 |
| `/api/documents/upload` | POST | 上传文档 | 8080 |
| `/api/documents` | GET | 文档列表 | 8080 |
| `/api/documents` | DELETE | 删除文档 | 8080 |
| `/docs` | GET | Swagger UI | 8080 |

### 1. 图像安全分析

**端点**: `POST /api/analysis/image`

```bash
# 基本用法
curl -X POST "http://localhost:8080/api/analysis/image" \
  -F "file=@image.jpg"

# 使用 Python
import requests

response = requests.post(
    "http://localhost:8080/api/analysis/image",
    files={"file": open("image.jpg", "rb")}
)
result = response.json()

# 访问源文档引用
for violation in result["violations"]:
    print(f"隐患: {violation['hazard_description']}")
    print(f"规范: {violation['rule_reference']}")
    for doc in violation["source_documents"]:
        print(f"  来源: {doc['filename']} - {doc['location']}")
```

### 2. 文档管理

#### 上传文档

```bash
# 单个文档
curl -X POST "http://localhost:8080/api/documents/upload" \
  -F "files=@document.pdf"

# 多个文档（批量）
curl -X POST "http://localhost:8080/api/documents/upload" \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.xlsx" \
  -F "files=@doc3.docx"

# 跳过已存在的文档（推荐）
curl -X POST "http://localhost:8080/api/documents/upload?skip_existing=true" \
  -F "files=@document.pdf"
```

**支持的文件格式**：
- PDF：`.pdf`
- Word：`.docx`, `.doc`
- Excel：`.xlsx`, `.xls`

#### 查看文档列表

```bash
curl -X GET "http://localhost:8080/api/documents" | jq .
```

#### 删除文档

```bash
# 删除单个文档
curl -X DELETE "http://localhost:8080/api/documents" \
  -H "Content-Type: application/json" \
  -d '{"document_names": ["document.pdf"]}'

# 批量删除
curl -X DELETE "http://localhost:8080/api/documents" \
  -H "Content-Type: application/json" \
  -d '{"document_names": ["doc1.pdf", "doc2.xlsx", "doc3.docx"]}'
```

## ⚙️ 配置说明

### 环境变量（docker-compose.yaml）

```yaml
environment:
  QDRANT_HOST: qdrant-server              # Qdrant 主机
  QDRANT_COLLECTION: rag-test             # 向量集合名称
  VLLM_CHAT_URL: http://vllm-qwen-vl:8000/v1      # VLM 聊天端点
  VLLM_EMBED_URL: http://vllm-bge-m3:8000/v1      # 嵌入端点
  VLLM_RERANK_URL: http://vllm-bge-reranker:8000  # 重排序端点
  VLLM_MODEL_NAME: /model/qwen3-vl-4b             # VLM 模型路径
  VLLM_EMBED_MODEL: /model/bge-m3                 # 嵌入模型路径
  VLLM_RERANK_MODEL: /model/bge-reranker-v2-m3    # 重排序模型路径
```

### 核心参数（app/core/config.py）

```python
class Settings(BaseSettings):
    # 文本分割
    chunk_size: int = 1000              # 文本块大小
    chunk_overlap: int = 200            # 文本块重叠
    
    # RAG 检索参数
    retrieval_score_threshold: float = 0.65   # 相似度阈值
    rerank_score_threshold: float = 0.3       # 重排序阈值
    
    # 文件上传
    max_file_size: int = 500 * 1024 * 1024    # 50MB
    max_files: int = 10                        # 最大文件数
```

### 模型 GPU 内存分配

在 `docker-compose.yaml` 中调整每个模型的显存占用：

```yaml
# Qwen-VL（最大）
--gpu-memory-utilization 0.7    # 70% 显存

# BGE-m3（中等）
--gpu-memory-utilization 0.2    # 20% 显存

# Reranker（最小）
--gpu-memory-utilization 0.15   # 15% 显存
```

**显存需求参考**：
- Qwen-VL-4B: ~8GB
- BGE-m3: ~2GB
- Reranker-v2-M3: ~1.5GB
- **总计**: ~12GB（推荐 16GB+ GPU）

## 💾 数据持久化

### Qdrant 向量数据库

```bash
# 数据存储位置
./data/qdrant/           # 项目目录下（便于备份）

# 备份数据
tar -czf qdrant_backup.tar.gz ./data/qdrant/

# 恢复数据
tar -xzf qdrant_backup.tar.gz

# 清空所有数据
docker compose down
rm -rf ./data/qdrant/
docker compose up -d
```

### 上传文件存储

```bash
# 文件存储位置
./file/                  # 原始文档存储

# 注意：删除文档时不会删除原始文件
# 手动清理文件存储
rm -rf ./file/*
```

## ❓ 常见问题

### Q1: 如何避免重复上传文档？

在上传 API 中使用 `skip_existing=true` 参数（默认开启）：
```bash
curl -X POST "http://localhost:8080/api/documents/upload?skip_existing=true" \
  -F "files=@document.pdf"
```

### Q2: 为什么有的 violation 返回多个 source_documents？

每个隐患会检索 **Top-3 最相关的文档**：
- `source_documents[0]`：相关性最高（Rerank 分数最高）
- `source_documents[1]`：相关性次之
- `source_documents[2]`：相关性第三

如果只检索到 1-2 个高分文档（≥0.3），则返回更少。

### Q3: recommendations 是根据检索文档生成的吗？

**是的**。生成逻辑：
1. RAG 检索到相关安全规范文档（最多 1200 字符）
2. LLM 基于文档内容 + 通用安全知识生成整改建议
3. 如果文档明确写有整改措施，LLM 会直接引用

### Q4: rule_reference 会编造标准吗？

**不会**。System prompt 明确要求：
- 判断文档是否与隐患相关
- 不相关则返回："未检索到相关规范"
- 相关则简要引用，包含文件名
- **不要编造标准编号**

### Q5: 如何清空所有文档？

```bash
# 方法1: 通过 API 批量删除（推荐）
curl -X GET "http://localhost:8080/api/documents" | \
  jq -r '.documents[].filename' | \
  jq -Rs 'split("\n")[:-1] | {document_names: .}' | \
  curl -X DELETE "http://localhost:8080/api/documents" \
    -H "Content-Type: application/json" -d @-

# 方法2: 删除 Qdrant collection
curl -X DELETE "http://localhost:6333/collections/rag-test"

# 方法3: 清空数据目录（最彻底）
docker compose down
rm -rf ./data/qdrant/
docker compose up -d
```

### Q6: 服务启动失败怎么办？

```bash
# 1. 查看日志定位问题
docker compose logs safetyvision-api
docker compose logs vllm-qwen-vl
docker compose logs vllm-bge-m3
docker compose logs vllm-bge-reranker

# 2. 检查 GPU 状态
nvidia-smi

# 3. 重启服务
docker compose restart

# 4. 完全重建
docker compose down
docker compose up -d --build
```

### Q7: 如何调整检索精度？

修改 `app/core/config.py` 中的阈值参数：

```python
# 更严格（精度高，召回低）
retrieval_score_threshold: float = 0.75  # 提高到 0.75
rerank_score_threshold: float = 0.4      # 提高到 0.4

# 更宽松（精度低，召回高）
retrieval_score_threshold: float = 0.55  # 降低到 0.55
rerank_score_threshold: float = 0.2      # 降低到 0.2
```

## 🛠️ 开发指南

### 本地开发环境

```bash
# 1. 安装 Python 依赖
pip install -r requirements.txt

# 2. 启动后端服务（GPU 模型 + 数据库）
docker compose up -d qdrant-server vllm-qwen-vl vllm-bge-m3 vllm-bge-reranker

# 3. 本地运行 API（支持热重载）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 运行测试

```bash
# 测试图像分析
python -c "
import requests
response = requests.post(
    'http://localhost:8080/api/analysis/image',
    files={'file': open('test.jpg', 'rb')}
)
print(response.json())
"

# 测试文档上传
curl -X POST "http://localhost:8080/api/documents/upload" \
  -F "files=@test.pdf"
```

### 代码风格

```bash
# 格式化代码
black app/ src/

# 类型检查
mypy app/ --ignore-missing-imports

# 排序导入
isort app/ src/
```

## 🚀 性能优化

### 1. 检索性能优化

**当前配置**（平衡精度和速度）：
```python
# 第一阶段：相似度检索
fetch_k = 30  # 召回 30 个候选

# 第二阶段：重排序
rerank_score_threshold = 0.3  # 过滤低分文档
k = 3  # 返回 Top-3

# 相似度阈值
retrieval_score_threshold = 0.65
```

**高精度配置**（牺牲速度）：
```python
fetch_k = 50  # 增加召回量
rerank_score_threshold = 0.4  # 提高过滤阈值
retrieval_score_threshold = 0.75
```

**高速度配置**（牺牲精度）：
```python
fetch_k = 10  # 减少召回量
rerank_score_threshold = 0.2
retrieval_score_threshold = 0.55
```

### 2. Token 预算优化

```python
# 文档内容截断（app/services/analysis_service.py）
MAX_DOC_LENGTH = 600       # 单文档最大字符数
MAX_CONTEXT_LENGTH = 1200  # 总上下文最大字符数

# LLM 输出限制（app/core/deps.py）
max_tokens = 4096  # 足够生成完整的结构化输出
```

### 3. 并发处理优化

当前使用 `asyncio.gather()` 并行处理：
- 多个隐患的文档检索（并行）
- 多个 violation 的生成（并行）

如需进一步优化，可以使用 `asyncio.Semaphore` 限制并发数。

## 📊 技术栈

### 核心框架
- **FastAPI** 0.115+：异步 Web 框架
- **LangChain** 1.0+：RAG 框架，结构化输出
- **Pydantic** 2.0+：数据验证和配置管理

### AI 模型
- **Qwen-VL-4B**：多模态视觉-语言模型（图像理解）
- **BGE-m3**：多语言文本嵌入模型（768维）
- **BGE-Reranker-v2-M3**：文档重排序模型

### 基础设施
- **vLLM**：高性能 LLM 推理引擎
- **Qdrant**：向量数据库（HNSW 索引）
- **Docker Compose**：容器编排

### 文档处理
- **pypdf**：PDF 解析
- **python-docx**：Word 文档解析
- **openpyxl/xlrd**：Excel 解析
- **antiword**：旧版 DOC 解析

## 📁 项目结构详解

```
SafetyVision-RAG/
├── app/                                # 主应用
│   ├── main.py                         # FastAPI 应用工厂
│   ├── api/routes/                     # API 路由
│   │   ├── analysis.py                 # POST /api/analysis/image
│   │   └── documents.py                # CRUD /api/documents
│   ├── core/                           # 核心基础设施
│   │   ├── config.py                   # Settings (环境变量)
│   │   ├── deps.py                     # DI (依赖注入)
│   │   └── retrieval.py                # SafetyRetriever (检索策略)
│   ├── schemas/                        # Pydantic 模型
│   │   └── safety.py                   # SafetyViolation, SourceReference
│   └── services/                       # 业务逻辑
│       ├── analysis_service.py         # 图像分析服务
│       └── document_service.py         # 文档管理服务
├── src/                                # 工具模块
│   └── document_processors.py          # 文档处理器工厂
├── data/                               # 数据持久化
│   └── qdrant/                         # Qdrant 向量存储
├── file/                               # 上传文件存储
├── docker-compose.yaml                 # 服务编排
├── Dockerfile                          # API 镜像构建
├── requirements.txt                    # Python 依赖
├── ARCHITECTURE.md                     # 架构设计文档
└── README.md                           # 本文件
```

## 🔗 相关资源

- [LangChain 官方文档](https://python.langchain.com)
- [Qdrant 向量数据库](https://qdrant.tech)
- [vLLM 推理引擎](https://github.com/vllm-project/vllm)
- [FastAPI 文档](https://fastapi.tiangolo.com)
- [Qwen-VL 模型](https://github.com/QwenLM/Qwen-VL)

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 📝 更新日志

### v2.0.0 (2025-12-03) - RAG Quality & Architecture Optimization
**架构优化：**
- ✅ Clean Architecture 重构（领域驱动设计）
- ✅ LangChain v1.0+ 最佳实践（`with_structured_output`）
- ✅ 依赖注入模式（FastAPI `Depends()`）
- ✅ Pydantic Settings 配置管理
- ✅ 代码简化（-30 行冗余代码）

**RAG 质量提升：**
- ✅ 两阶段检索策略（Similarity Search + Rerank）
- ✅ 相关性过滤（相似度 0.65 + Rerank 0.3）
- ✅ 源文档溯源（`SourceReference` 模型）
- ✅ Token 预算优化（输入 900 + 输出 4096）
- ✅ 结构化输出优化（分离 LLM 输出和完整模型）

**新增功能：**
- ✅ 多格式文档支持（PDF, DOCX, DOC, XLSX, XLS）
- ✅ Excel 行级语义搜索（精确到工作表+行号）
- ✅ BGE-Reranker-v2-M3 重排序模型集成
- ✅ Per-Hazard Retrieval（每个隐患独立检索）

**性能优化：**
- ✅ 异步并行处理（`asyncio.gather`）
- ✅ 热重载开发环境（volume 挂载）
- ✅ Docker 健康检查优化
- ✅ 推理速度提升（从 1-2 分钟 → 几秒钟）

### v1.0.0 (2025-11-10) - Initial Release
- ✅ 图像安全分析（Qwen-VL-4B）
- ✅ 文档管理 API（上传、删除、列表）
- ✅ 基础 RAG 检索（BGE-m3 嵌入）
- ✅ Docker Compose 容器编排

---

**Built with ❤️ by AI Safety Team**
