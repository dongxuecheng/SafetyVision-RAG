# SafetyVision-RAG

**基于视觉-语言模型和检索增强生成的AI安全隐患检测系统**

[![FastAPI](https://img.shields.io/badge/FastAPI-2.0.0-009688.svg)](https://fastapi.tiangolo.com)
[![LangChain](https://img.shields.io/badge/LangChain-1.0+-1C3C3C.svg)](https://python.langchain.com)
[![Qdrant](https://img.shields.io/badge/Qdrant-1.15+-DC382D.svg)](https://qdrant.tech)
[![vLLM](https://img.shields.io/badge/vLLM-latest-4B8BBE.svg)](https://github.com/vllm-project/vllm)

## ✨ 核心特性

- 💬 **智能问答**：流式对话 + LaTeX 公式 + 中文化（Chainlit UI）
- 🎯 **图像分析**：多模态VLM识别安全隐患，支持用户自定义隐患融合
- 🔄 **双模式部署**：阿里云API（生产）/ 本地vLLM（离线）灵活切换
- 📝 **统一日志**：loguru集中管理，文件输出 + 日志轮转
- 📚 **混合检索**：向量搜索 + 关键词匹配 + BGE-Reranker重排
- 📋 **结构化输出**：自动提取隐患、建议、规范引用及源文档溯源

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


#### 🌩️ 阿里云API模式（推荐）

**优势**：GPU要求低（~8GB），使用高性能云端模型

```bash
# 1. 配置
cp .env.aliyun.example .env
vim .env  # 填写 DASHSCOPE_API_KEY

# 2. 启动
docker compose -f docker-compose.aliyun.yaml up -d

# 3. 访问
# Chainlit UI: http://localhost:8000
# API文档: http://localhost:8080/docs
```

**配置**：VLM/LLM使用阿里云API，Embedding/Reranker本地部署

#### 💻 本地vLLM模式

**优势**：完全离线，数据不出本地

```bash
# 1. 配置
cp .env.local.example .env

# 2. 启动（需要16GB+ GPU显存）
docker compose -f docker-compose.local.yaml up -d

# 3. 等待模型加载（3-5分钟）
docker compose logs -f vllm-qwen-vl
```

**配置**：所有模型本地部署（Qwen3-VL-4B + BGE-M3 + BGE-Reranker）

### 验证服务

```bash
# 查看日志
docker compose logs -f safetyvision-api

# 访问服务
curl http://localhost:8000           # Chainlit UI
curl http://localhost:8080/docs      # API 文档
curl http://localhost:6333/dashboard # Qdrant 管理界面
```

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

### 4. 测试图像分析（可选）

```bash
# 基本用法：仅使用VLM识别隐患
curl -X POST "http://localhost:8080/api/analysis/image" \
  -F "file=@construction_site.jpg" \
  | jq .

# 高级用法：结合用户自定义隐患
curl -X POST "http://localhost:8080/api/analysis/image" \
  -F "file=@construction_site.jpg" \
  -F "user_hazards=作业人员未佩戴反光背心" \
  -F "user_hazards=施工区域无围挡" \
  | jq .
## 📚 使用指南

### API端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/analysis/image` | POST | 图像安全分析（支持用户自定义隐患） |
| `/api/documents/upload` | POST | 上传文档（PDF/Word/Excel/Markdown） |
| `/api/documents` | GET | 文档列表 |
| `/api/documents` | DELETE | 删除文档 |

### 图像分析示例

```bash
# 基础分析
curl -X POST "http://localhost:8080/api/analysis/image" \
  -F "file=@image.jpg"

# 传入用户自定义隐患（可选）
curl -X POST "http://localhost:8080/api/analysis/image" \
  -F "file=@image.jpg" \
  -F "user_hazards=未佩戴安全帽" 
```

### 文档管理示例

```bash
# 上传文档
curl -X POST "http://localhost:8080/api/documents/upload" \
  -F "files=@document.pdf"

# 查看文档列表
curl -X GET "http://localhost:8080/api/documents"

# 删除文档
curl -X DELETE "http://localhost:8080/api/documents?filenames=document.pdf"
```

**支持格式**：PDF、Word、Excel、Markdown
curl -X DELETE "http://localhost:8080/api/documents" \
  -H "Content-Type: application/json" \
  -d '{"document_names": ["document.pdf"]}'

# 批量删除
curl -X DELETE "http://localhost:8080/api/documents" \
  -H "Content-Type: application/json" \
  -d '{"document_names": ["doc1.pdf", "doc2.xlsx", "doc3.docx"]}'
```

## ⚙️ 配置说明

### 环境变量配置

#### 阿里云API模式（.env.aliyun.example）

```bash
# 部署模式
DEPLOYMENT_MODE=aliyun

# 阿里云API配置
DASHSCOPE_API_KEY=sk-xxx                        # 必填：阿里云API密钥

# 本地模型服务
VLLM_EMBED_URL=http://vllm-bge-m3:8000/v1
VLLM_EMBED_MODEL=/model/bge-m3
VLLM_RERANK_URL=http://vllm-bge-reranker:8000
VLLM_RERANK_MODEL=/model/bge-reranker-v2-m3

# 日志配置
LOG_LEVEL=INFO
LOG_FILE_PATH=logs/app.log
LOG_ROTATION=100 MB
LOG_RETENTION=30 days
```

#### 本地vLLM模式（.env.local.example）

```bash
# 部署模式
DEPLOYMENT_MODE=local

# 本地vLLM服务配置
VLLM_LLM_URL=http://vllm-qwen-vl:8000/v1
VLLM_LLM_MODEL=/model/qwen3-vl-4b               # 注意：小写路径
VLLM_EMBED_URL=http://vllm-bge-m3:8000/v1
VLLM_EMBED_MODEL=/model/bge-m3
VLLM_RERANK_URL=http://vllm-bge-reranker:8000
VLLM_RERANK_MODEL=/model/bge-reranker-v2-m3

# 日志配置
LOG_LEVEL=INFO
LOG_FILE_PATH=logs/app.log
LOG_ROTATION=100 MB
LOG_RETENTION=30 days
```

### 核心参数（app/core/config.py）

详细配置请参考 [CONFIG_GUIDE.md](CONFIG_GUIDE.md)。以下是关键参数：## ⚙️ 配置说明

### 核心配置项

```python
# 部署模式
deployment_mode: "aliyun" | "local"    # 阿里云API或本地vLLM

# 日志配置（loguru）
log_level: "INFO"                       # 日志级别
log_file_path: "logs/app.log"          # 日志文件
log_rotation: "100 MB"                  # 日志轮转
log_retention: "30 days"                # 保留时间

# RAG检索
retrieval_score_threshold: 0.2          # 向量相似度阈值
rerank_score_threshold: 0.3             # 重排序阈值
regulations_retrieval_k: 5              # 规范文档检索数量
hazard_db_retrieval_k: 5                # 隐患数据库检索数量

# 文本处理
chunk_size: 1000                        # 文本块大小
excel_rows_per_chunk: 10                # Excel合并行数
max_doc_length: 1500                    # 单文档最大字符
max_context_length: 3000                # 总上下文限制
```

### 环境变量

**阿里云模式** (`.env.aliyun.example`):
```bash
DEPLOYMENT_MODE=aliyun
DASHSCOPE_API_KEY=sk-xxx              # 必填
```

**本地模式** (`.env.local.example`):
```bash
DEPLOYMENT_MODE=local
VLLM_LLM_URL=http://vllm-qwen-vl:8000/v1
VLLM_LLM_MODEL=/model/qwen3-vl-4b
```

详细配置说明见 [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)

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

## 🔧 常见问题

### 服务相关

**Q: 如何切换部署模式？**
```bash
# 停止当前服务
docker compose -f docker-compose.{aliyun/local}.yaml down

# 修改.env中的DEPLOYMENT_MODE
vim .env

# 启动新模式
docker compose -f docker-compose.{aliyun/local}.yaml up -d
```

**Q: 如何查看日志？**
```bash
# 实时日志
docker compose logs -f safetyvision-api

# 日志文件（持久化）
tail -f logs/app.log

# 查看特定服务
docker logs vllm-qwen-vl
```

**Q: 服务启动失败？**
```bash
# 1. 检查GPU
nvidia-smi

# 2. 检查端口占用
netstat -tulpn | grep -E "8000|8080|6333"

# 3. 重启服务
docker compose restart

# 4. 完全重建
docker compose down && docker compose up -d --build
```

### 配置相关

**Q: 如何调整检索精度？**

编辑 `app/core/config.py` 或通过环境变量：
```python
# 精度优先
retrieval_score_threshold: 0.3
rerank_score_threshold: 0.4

# 召回优先  
retrieval_score_threshold: 0.1
rerank_score_threshold: 0.2
```

**Q: 本地模式GPU不足？**

调整 `docker-compose.local.yaml` 中的显存分配：
```yaml
# 降低Qwen-VL显存占用
--gpu-memory-utilization 0.5    # 从0.7降至0.5
```

更多问题参考 [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)

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

