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
- 💬 **智能问答 (Chainlit UI)**：流式对话，支持 LaTeX 公式，完整中文化
- 🎯 **智能图像分析**：使用 Qwen-VL-4B 多模态大模型识别安全隐患
- 📋 **结构化输出**：自动提取隐患描述、整改建议、规范引用
- 📚 **源文档溯源**：每条记录附带引用文档的文件名和精确位置

### RAG 增强
- ✅ **混合检索**：向量搜索 + 关键词匹配 + 文档名过滤
- ✅ **精确定位**：支持"《文档名》第X条"查询（自动转换阿拉伯/中文数字）
- ✅ **多格式文档**：PDF、DOCX、XLSX、Markdown
- ✅ **智能重排**：BGE-Reranker-v2-M3，相似度 0.2 + Rerank 0.3
- ✅ **对话记忆**：保留最近 10 条历史消息

## 📐 系统架构

### 服务架构
```
┌──────────────────────────────────────────────────────────┐
│           Chainlit UI (8000) - 用户交互层                 │
│   - 流式对话 + LaTeX 公式 + 中文化                        │
│   - 对话历史 (10轮) + Starter 推荐问题                   │
└───────────────────────────┬──────────────────────────────┘
                            ↓ (调用内部 API)
┌──────────────────────────────────────────────────────────┐
│        SafetyVision-RAG API (8080) - 业务逻辑层           │
│   FastAPI + LangChain + Async/Await                      │
│                                                           │
│  ┌──────────────┐  ┌───────────────────────────────────┐ │
│  │ VLM Pipeline │  │   RAG Pipeline (混合检索)          │ │
│  │ - 图像识别    │  │   ├─ 向量搜索 (BGE-m3)             │ │
│  │ - 隐患提取    │  │   ├─ 关键词匹配 (文档名+条款号)    │ │
│  │ - 结构化输出  │  │   ├─ 重排序 (Reranker-v2-M3)       │ │
│  └──────────────┘  │   └─ 精确匹配优先 (doc_article)    │ │
│                    └───────────────────────────────────┘ │
└──────────────────────┬──────────────────────┬────────────┘
                       ↓                      ↓
       ┌───────────────────────┐  ┌───────────────────────┐
       │  Qdrant (6333)        │  │  vLLM GPU Cluster     │
       │  向量数据库             │  │  ├─ Qwen-VL (8000)   │
       │  - rag-qa-knowledge   │  │  ├─ BGE-m3 (8001)     │
       │  - 14k+ chunks        │  │  └─ Reranker (8002)   │
       └───────────────────────┘  └───────────────────────┘
```

### 代码架构（Clean Architecture）
```
SafetyVision-RAG/
├── chainlit_app.py                     # Chainlit UI 入口
│   ├─ QA 对话流程                       #   - 流式回答 + LaTeX
│   ├─ Starter 推荐问题                  #   - 引导用户提问
│   └─ 历史消息管理 (10轮)               #   - 上下文连续对话
│
├── app/                                # FastAPI 后端应用
│   ├── main.py                         # API 入口 + 生命周期
│   │
│   ├── api/routes/                     # API 路由层
│   │   ├── qa.py                       # 问答端点（核心）
│   │   ├── analysis.py                 # 图像分析端点
│   │   └── documents.py                # 文档管理端点
│   │
│   ├── core/                           # 基础设施层
│   │   ├── config.py                   # 配置管理（45+ 参数）
│   │   ├── deps.py                     # 依赖注入
│   │   └── retrieval.py                # 混合检索策略
│   │       ├─ 向量搜索 + 关键词匹配     #   - BGE-m3 嵌入
│   │       ├─ 文档名+条款号过滤         #   - 精确定位
│   │       ├─ 重排序 (Reranker-v2-M3)  #   - 提升准确性
│   │       └─ 精确匹配优先              #   - doc_article 类型
│   │
│   ├── schemas/                        # 数据模型（DTO）
│   │   ├── qa.py                       # QA 请求/响应
│   │   └── safety.py                   # 图像分析模型
│   │
│   └── services/                       # 业务逻辑层
│       ├── qa_service.py               # 问答服务（核心）
│       │   ├─ ask_question()           #   主流程编排
│       │   ├─ _build_prompt()          #   Prompt 构建
│       │   └─ _format_sources()        #   源文档格式化
│       │
│       ├── analysis_service.py         # 安全分析服务
│       └── document_service.py         # 文档处理服务
│
├── .chainlit/                          # Chainlit 配置
│   ├── config.toml                     # UI 配置（中文化）
│   └── translations/zh-CN.json         # 界面翻译（自动生成）
│
├── chainlit.md                         # 默认欢迎页面
├── chainlit_zh-CN.md                   # 中文欢迎页面
│
└── data/qdrant/                        # 向量数据库存储
    └── rag-qa-knowledge/               # QA 知识库集合
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
curl http://localhost:8000           # Chainlit UI（推荐）
curl http://localhost:8080/docs      # API 文档（Swagger UI）
curl http://localhost:6333/dashboard # Qdrant 管理界面
```

**服务端口**：
- **Chainlit UI**: `http://localhost:8000` - 用户对话界面
- SafetyVision API: `http://localhost:8080` - 后端 API
- Qdrant: `http://localhost:6333` - 向量数据库

### 3. 使用 Chainlit UI（推荐）

打开浏览器访问 `http://localhost:8000`，开始对话：
- 点击推荐问题快速开始
- 支持连续追问和上下文理解
- 实时流式回答 + LaTeX 公式渲染

### 4. 上传知识库文档

```bash
# 使用上传脚本（支持项目选择）
./upload_documents.sh -p qa data/规范文档/

# 或使用 API
curl -X POST "http://localhost:8080/api/qa/documents" \
  -F "files=@安全生产法.pdf" \
  -F "files=@建筑施工规范.docx"
```

### 5. 测试图像分析（可选）

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
- 📄 **PDF**：`.pdf` → `rag-regulations` 集合
- 📝 **Word**：`.docx`, `.doc` → `rag-regulations` 集合
- 📊 **Excel**：`.xlsx`, `.xls` → `rag-hazard-db` 集合（优化处理，10行/块）
- 📋 **Markdown**：`.md` → `rag-regulations` 集合（HTML 清理，章节提取）

**多集合架构说明**：
- `rag-regulations`：存储安全规范、标准文件（PDF/Word/Markdown）
- `rag-hazard-db`：存储隐患数据库、检查表（Excel），独立优化避免向量污染

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
  QDRANT_PORT: 6333                       # Qdrant 端口
  VLLM_CHAT_URL: http://vllm-qwen-vl:8000/v1      # VLM 聊天端点
  VLLM_EMBED_URL: http://vllm-bge-m3:8000/v1      # 嵌入端点
  VLLM_RERANK_URL: http://vllm-bge-reranker:8000  # 重排序端点
  VLLM_MODEL_NAME: /model/qwen3-vl-4b             # VLM 模型路径
  VLLM_EMBED_MODEL: /model/bge-m3                 # 嵌入模型路径
  VLLM_RERANK_MODEL: /model/bge-reranker-v2-m3    # 重排序模型路径
```

### 核心参数（app/core/config.py）

详细配置请参考 [CONFIG_GUIDE.md](CONFIG_GUIDE.md)。以下是关键参数：

```python
class Settings(BaseSettings):
    # === 多集合策略 ===
    qdrant_regulations_collection: str = "rag-regulations"  # 规范文档集合
    qdrant_hazard_db_collection: str = "rag-hazard-db"      # 隐患数据库集合
    
    # === 文本分割 ===
    chunk_size: int = 1000              # 通用文本块大小
    chunk_overlap: int = 200            # 文本块重叠
    excel_rows_per_chunk: int = 10      # Excel 每块行数
    
    # === RAG 检索参数 ===
    retrieval_top_k: int = 3                      # 返回文档数
    retrieval_score_threshold: float = 0.4        # 相似度阈值（硬阈值）
    rerank_score_threshold: float = 0.3           # 重排序阈值
    fetch_k_multiplier: int = 50                  # fetch_k = k × 50
    rerank_top_n_multiplier: int = 10             # rerank_top_n = k × 10
    min_relevant_docs_per_hazard: int = 2         # 每个隐患最少文档数
    
    # === Token 预算（适配 Qwen3-VL-4B max_model_len=5840）===
    max_doc_length: int = 600            # 单文档最大字符数
    max_context_length: int = 1000       # 总上下文最大字符数
    llm_max_tokens: int = 1500           # LLM 输出 token 限制
    
    # === Excel 优化 ===
    excel_key_fields: list[str] = [
        "物品/设备名称", "危害", "个人防护装备（PPE）",
        "安全措施", "应急措施", "法律法规", "安全防护", ...
    ]
    
    # === 文件上传 ===
    max_file_size: int = 500 * 1024 * 1024    # 50MB
    max_files: int = 10                        # 最大文件数
```

**配置优化建议：**
- 📊 **高精度场景**：`retrieval_score_threshold=0.5`, `min_relevant_docs_per_hazard=3`
- ⚡ **高召回场景**：`retrieval_score_threshold=0.3`, `fetch_k_multiplier=100`
- 💾 **低显存场景**：`max_context_length=800`, `llm_max_tokens=1000`
- 📈 **Excel 密集场景**：`excel_rows_per_chunk=5`（更细粒度）

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

### Q1: 如何查询特定文档条款（如"第32条"）？

**直接提问即可**，系统会自动转换数字格式：
```
用户: 中华人民共和国行政许可法的第32条是什么？
系统: 自动搜索"第32条"和"第三十二条"，返回完整内容
```

核心技术：
- 阿拉伯/中文数字自动转换（32 ↔ 三十二）
- 文档名 + 条款号精确匹配（`min_should=1`）
- `doc_article` 类型优先排序

### Q2: 为什么回答中引用了多个文档？

每个问题会检索 **Top-5 最相关的文档**：
1. 向量搜索（召回 500 个候选）
2. 关键词匹配（文档名、条款号）
3. 重排序过滤（Rerank ≥0.3）
4. 精确匹配优先（`doc_article` 类型在前）

### Q3: 如何上传和管理文档？

```bash
# 上传到 QA 知识库（推荐使用脚本）
./upload_documents.sh -p qa data/法规文档/

# 或使用 API（支持批量 + skip_existing）
curl -X POST "http://localhost:8080/api/qa/documents?skip_existing=true" \
  -F "files=@安全生产法.pdf"

# 删除所有文档
./delete_all_documents.sh -p qa

# 查看文档列表
curl "http://localhost:8080/api/qa/documents"
```

### Q4: 如何清空对话历史？

Chainlit UI 支持：
- **新建对话**：点击界面左上角的新建按钮
- **历史记录**：系统自动保存最近 10 轮对话

### Q5: 服务启动失败怎么办？

```bash
# 1. 查看日志定位问题
docker compose logs chainlit-ui
docker compose logs safetyvision-api
docker compose logs vllm-qwen-vl

# 2. 检查 GPU 状态
nvidia-smi

# 3. 重启服务
docker compose restart

# 4. 完全重建
docker compose down && docker compose up -d --build
```

### Q6: 如何调整检索精度？

修改 `app/core/config.py`：

```python
# 当前默认（平衡精度和召回）
retrieval_score_threshold: float = 0.2   # 向量搜索阈值
rerank_score_threshold: float = 0.3      # 重排序阈值
fetch_k_multiplier: int = 100            # 召回倍数（k×100）

# 更严格（精度优先）
retrieval_score_threshold: float = 0.3
rerank_score_threshold: float = 0.4

# 更宽松（召回优先）
retrieval_score_threshold: float = 0.1
rerank_score_threshold: float = 0.2
```

### Q7: 如何自定义 Chainlit UI？

```toml
# 编辑 .chainlit/config.toml
[UI]
name = "安全生产大模型知识问答系统"  # 标题
language = "zh-CN"                    # 界面语言
# custom_css = "/public/custom.css"   # 自定义样式（可选）

[features]
latex = true                           # LaTeX 公式支持
```

创建中文欢迎页面：`chainlit_zh-CN.md`

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
# 配置文件：app/core/config.py
retrieval_top_k: int = 3                      # 返回 Top-3 文档
fetch_k_multiplier: int = 50                  # fetch_k = k × 50 = 150
rerank_top_n_multiplier: int = 10             # rerank_top_n = k × 10 = 30
retrieval_score_threshold: float = 0.4        # 硬阈值（平衡精度和召回）
rerank_score_threshold: float = 0.3           # 重排序阈值
min_relevant_docs_per_hazard: int = 2         # 每个隐患最少文档数
```

**高精度配置**（牺牲速度）：
```python
fetch_k_multiplier: int = 100                 # 更大召回量（k × 100）
retrieval_score_threshold: float = 0.5        # 提高阈值
rerank_score_threshold: float = 0.4
min_relevant_docs_per_hazard: int = 3         # 要求更多文档
```

**高速度配置**（牺牲精度）：
```python
fetch_k_multiplier: int = 20                  # 减少召回量（k × 20）
retrieval_score_threshold: float = 0.3        # 降低阈值
min_relevant_docs_per_hazard: int = 1         # 减少最小文档数
```

**实测性能指标**：
- 当前配置：~2-3 秒/请求（含图像分析 + RAG 检索 + LLM 生成）
- 优化后：~1.5-2 秒/请求（代码简化节省 ~35ms）
- 瓶颈：VLM 图像理解（~1秒）> RAG 检索（~500ms）> LLM 生成（~300ms）

### 2. Token 预算优化（适配 Qwen3-VL-4B）

```python
# 配置文件：app/core/config.py
max_doc_length: int = 600           # 单文档最大字符数
max_context_length: int = 1000      # 总上下文最大字符数（适配 max_model_len=5840）
llm_max_tokens: int = 1500          # LLM 输出 token 限制

# 完整 Token 预算分配（总计 ~5840）
# - System Prompt: ~500 tokens
# - 图像理解结果: ~500 tokens
# - RAG 上下文: ~1000 tokens (max_context_length)
# - 输出预留: ~1500 tokens (llm_max_tokens)
# - 安全边际: ~2340 tokens
```

**问题排查**：
- ⚠️ "输出超长度限制" 错误 → 降低 `max_context_length` 或 `llm_max_tokens`
- ⚠️ 文档内容被截断 → 增加 `max_doc_length`（需同步减少 `llm_max_tokens`）

### 3. 并发处理优化

**当前实现**（已优化）：
```python
# app/services/analysis_service.py

# 并行检索（多个隐患同时检索文档）
retrieval_tasks = [
    self._batch_retrieve_per_hazard(hazard, retriever, reranker)
    for hazard in hazards
]
docs_per_hazard = await asyncio.gather(*retrieval_tasks)

# 并行生成（多个 violation 同时调用 LLM）
violation_tasks = [
    self._generate_single_violation(hazard, docs, chain)
    for hazard, docs in zip(hazards, docs_per_hazard) if docs
]
violations = await asyncio.gather(*violation_tasks)
```

**进一步优化**（可选）：
```python
# 限制并发数（防止 OOM）
from asyncio import Semaphore

MAX_CONCURRENT_VIOLATIONS = 5  # 最多 5 个并发 LLM 调用
semaphore = Semaphore(MAX_CONCURRENT_VIOLATIONS)

async def _generate_with_limit(hazard, docs, chain):
    async with semaphore:
        return await self._generate_single_violation(hazard, docs, chain)

violations = await asyncio.gather(*[
    _generate_with_limit(h, d, chain)
    for h, d in zip(hazards, docs_per_hazard) if d
])
```

### 4. 代码质量优化（已完成）

**优化成果**：
- ✅ 删除冗余代码：~50 行（retrieve_with_mmr、双重判断逻辑、LLM 后处理截断）
- ✅ 简化判断逻辑：从 `if max_score >= 0.5 and len >= 2` 改为 `if len >= min_docs`
- ✅ 移除无用截断：LLM 输出已在 Prompt 中限制，无需后处理
- ✅ 性能提升：每个请求节省 ~35ms（逻辑简化 10ms + 截断移除 5ms × N 个隐患）

**代码审计清单**：
- [x] 移除未使用的方法（`retrieve_with_mmr`）
- [x] 简化条件判断（单条件 vs 双条件）
- [x] 删除冗余后处理（LLM 输出截断）
- [x] 配置整合（45+ 项统一管理）
- [ ] 实现并发限制（`Semaphore`，可选）
- [ ] 添加缓存层（重复请求优化，可选）

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
├── app/                                # 主应用（Clean Architecture）
│   ├── main.py                         # FastAPI 应用工厂
│   ├── api/routes/                     # API 路由层
│   │   ├── analysis.py                 # POST /api/analysis/image
│   │   └── documents.py                # CRUD /api/documents
│   ├── core/                           # 核心基础设施
│   │   ├── config.py                   # ⭐ 统一配置（45+ 项）
│   │   ├── deps.py                     # 依赖注入（LLM/Qdrant/Reranker）
│   │   └── retrieval.py                # SafetyRetriever（检索策略）
│   ├── schemas/                        # Pydantic 数据模型
│   │   └── safety.py                   # SafetyViolation, SourceReference
│   └── services/                       # 业务逻辑层
│       ├── analysis_service.py         # 图像分析服务（VLM + RAG + LLM）
│       └── document_service.py         # 文档管理服务（多集合路由）
├── src/                                # 工具模块
│   └── document_processors.py          # 文档处理器工厂（PDF/Word/Excel/Markdown）
├── data/                               # 数据持久化
│   └── qdrant/                         # Qdrant 向量存储
│       ├── rag-regulations/            # 规范文档集合
│       └── rag-hazard-db/              # 隐患数据库集合
├── file/                               # 上传文件存储
├── scripts/                            # 测试脚本
│   ├── delete_all_documents.sh         # 清空所有集合
│   ├── upload_documents.sh             # 批量上传测试
│   └── test_collections.sh             # 验证多集合功能
├── docker-compose.yaml                 # 服务编排（5 个容器）
├── Dockerfile                          # API 镜像构建
├── requirements.txt                    # Python 依赖
├── CONFIG_GUIDE.md                     # ⭐ 配置指南（详细说明）
└── README.md                           # ⭐ 本文件（项目总览）
```

**架构设计亮点**：
- 💬 **Chainlit 2.9+**：现代化对话 UI，流式回答，LaTeX 公式，完整中文化
- 🎯 **Clean Architecture**：领域驱动设计，依赖倒置
- 🔍 **混合检索**：向量 + 关键词 + 文档名过滤 + 精确匹配优先
- 🔢 **智能数字转换**：阿拉伯/中文数字自动转换（32 ↔ 三十二）
- ⚙️ **配置统一**：45+ 配置项集中管理，类型安全
- 🚀 **异步优先**：全异步设计，支持高并发

## 🔗 相关资源

- [Chainlit 官方文档](https://docs.chainlit.io) - 对话 UI 框架
- [LangChain](https://python.langchain.com) - LLM 应用框架
- [Qdrant](https://qdrant.tech) - 向量数据库
- [vLLM](https://github.com/vllm-project/vllm) - 高性能推理引擎
- [Qwen-VL](https://github.com/QwenLM/Qwen-VL) - 多模态大模型

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 📝 更新日志

### v3.1.0 (2025-12-17) - Chainlit UI & Hybrid Retrieval
**Chainlit 对话界面：**
- ✅ 流式对话 UI（`msg.stream_token()`）+ LaTeX 公式支持
- ✅ 完整中文化（`language = "zh-CN"` + `chainlit_zh-CN.md`）
- ✅ Starter 推荐问题（引导用户快速上手）
- ✅ 对话历史管理（最近 10 轮消息，支持上下文连续对话）
- ✅ 官方最佳实践（无需自定义 CSS hack）

**混合检索优化：**
- ✅ 向量搜索 + 关键词匹配 + 文档名过滤
- ✅ 精确定位支持：`《文档名》第X条` 查询
- ✅ 阿拉伯/中文数字自动转换（32 ↔ 三十二）
- ✅ `min_should` 过滤：强制匹配至少一个条款号
- ✅ 精确匹配优先：`doc_article` 类型排在 rerank 之前
- ✅ 检索阈值优化：相似度 0.2 + Rerank 0.3

**配置与文档：**
- ✅ `.gitignore` 优化：排除 `.chainlit/translations/`（自动生成）
- ✅ README 更新：整合 Chainlit 架构，精简常见问题
- ✅ 删除冗余文档：保留核心 README + Chainlit 欢迎页

### v3.0.0 (2025-12-15) - Multi-Collection & Code Quality
**核心功能：**
- ✅ 双集合架构：`rag-qa-knowledge`（QA 知识库）
- ✅ 45+ 配置项统一管理（`config.py`）
- ✅ Excel 优化：10 行/块，16 个关键字段
- ✅ Markdown 支持：章节标题提取，HTML 清理
- ✅ 动态召回：fetch_k = k × 100，提升检索覆盖

**代码质量：**
- ✅ 删除冗余代码 ~50 行（retrieve_with_mmr、双重判断）
- ✅ 性能提升 ~35ms/请求
- ✅ Clean Architecture 重构

### v2.0.0 (2025-12-03) - RAG Quality & Architecture Optimization
**架构优化：**
- ✅ Clean Architecture 重构（领域驱动设计）
- ✅ LangChain v1.0+ 最佳实践（`with_structured_output`）
- ✅ 依赖注入模式（FastAPI `Depends()`）
- ✅ Pydantic Settings 配置管理

**RAG 质量提升：**
- ✅ 两阶段检索策略（Similarity Search + Rerank）
- ✅ 相关性过滤（相似度 0.65 + Rerank 0.3）
- ✅ 源文档溯源（`SourceReference` 模型）
- ✅ Token 预算优化（输入 900 + 输出 4096）

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
