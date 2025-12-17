# RAG 知识问答系统使用指南

## 📋 功能说明

SafetyVision-RAG 项目已集成 **RAG 知识问答系统**，提供两种使用方式：
1. **Chainlit UI** - 友好的对话界面
2. **REST API** - 可编程接口

## 🏗️ 架构说明

### 三层架构复用

```
┌──────────────────────────────────────────────────────┐
│                     顶层逻辑                          │
├────────────────────┬─────────────────────────────────┤
│  SafetyVision-RAG  │  RAG-QA System                 │
│  (图像安全分析)      │  (知识问答)                     │
│  - VLM 隐患识别    │  - 文本问答                      │
│  - 规范检索        │  - 文档检索                      │
│  - 违规报告        │  - 答案生成                      │
└────────────────────┴─────────────────────────────────┘
           │                        │
           ▼                        ▼
┌──────────────────────────────────────────────────────┐
│                   中层架构（复用）                      │
│  - 文档管理接口 (DocumentService)                     │
│  - 文档上传、列表、删除                                │
└──────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────┐
│                   底层架构（复用）                      │
│  - vLLM 模型接口: Qwen-VL, BGE-M3, BGE-Reranker      │
│  - Qdrant 向量库: 不同 Collections                    │
│    • rag-regulations (安全规范)                       │
│    • rag-hazard-db (危险库)                          │
│    • rag-qa-knowledge (QA知识库) ← 新增              │
│  - SafetyRetriever (检索器)                          │
│  - LLM 配置和依赖注入                                  │
└──────────────────────────────────────────────────────┘
```

### 复用的组件

1. **SafetyRetriever** - 两阶段检索（Similarity + Rerank）
2. **LLM (Qwen-VL)** - 答案生成
3. **Embeddings (BGE-M3)** - 文本向量化
4. **Reranker (BGE-Reranker-v2-M3)** - 文档重排序
5. **DocumentService** - 文档管理（上传、删除、列表）
6. **Qdrant** - 向量数据库（独立 collection）

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

新增依赖：
- `chainlit>=1.0.0` - 对话界面框架

### 2. 启动服务

#### 方式一：启动 Chainlit UI（推荐）

```bash
# 在项目根目录下
chainlit run chainlit_app.py -w

# 默认访问地址: http://localhost:8000
```

参数说明：
- `-w` - 启用热重载（开发模式）
- `--port 8001` - 指定端口（可选）
- `--host 0.0.0.0` - 允许外部访问（可选）

#### 方式二：使用 REST API

```bash
# 启动 FastAPI 服务（如果还未启动）
docker compose restart safetyvision-api

# API 文档: http://localhost:8080/docs
```

### 3. 上传知识库文档

使用现有的文档上传接口（复用）：

```bash
# 方式一：通过 API 上传
curl -X POST "http://localhost:8080/api/documents/upload?collection=qa" \
  -F "files=@your-document.pdf"

# 方式二：通过脚本上传
# 编辑 upload_documents.sh，设置 COLLECTION=qa
bash upload_documents.sh
```

支持的文档格式：
- PDF
- Word (.docx, .doc)
- Excel (.xlsx, .xls)
- Markdown (.md)
- 文本 (.txt)

## 💡 使用示例

### Chainlit UI 使用

1. 访问 http://localhost:8000
2. 在对话框中输入问题
3. 系统自动检索相关文档并生成答案
4. 点击侧边栏查看引用来源

示例对话：
```
用户: 什么是高处作业？
助手: 根据文档，高处作业是指...

📚 参考来源：
1. 建筑施工安全规范.pdf (相似度: 0.85)
2. 安全技术规范.xlsx (相似度: 0.76)
```

### REST API 使用

#### 请求示例

```bash
curl -X POST "http://localhost:8080/api/qa/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "什么是高处作业？"
  }'
```

#### 响应示例

```json
{
  "answer": "根据《建筑施工安全规范》，高处作业是指...",
  "sources": [
    {
      "content": "高处作业是指凡在坠落高度基准面2m以上...",
      "filename": "建筑施工安全规范.pdf",
      "location": "页码: 15",
      "score": 0.85
    }
  ],
  "has_relevant_sources": true
}
```

## 🔧 配置说明

### Qdrant Collection

QA 系统使用独立的 collection：`rag-qa-knowledge`

```python
# 在 app/core/config.py
qdrant_collection_qa: str = "rag-qa-knowledge"
```

### 检索参数（可调优）

```python
# 使用与 SafetyVision 相同的检索参数
regulations_retrieval_k: int = 5  # 返回文档数
retrieval_score_threshold: float = 0.4  # 相似度阈值
min_retrieval_score: float = 0.3  # 最低分数
```

## 📊 API 端点

### QA 相关接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/qa/ask` | POST | 提问并获取答案 |
| `/api/qa/health` | GET | 健康检查 |

### 文档管理接口（复用）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/documents/upload?collection=qa` | POST | 上传文档到 QA 知识库 |
| `/api/documents?collection=qa` | GET | 列出 QA 知识库文档 |
| `/api/documents/delete?collection=qa` | POST | 删除 QA 知识库文档 |

## 🎯 与 SafetyVision-RAG 的对比

| 特性 | SafetyVision-RAG | RAG-QA System |
|------|------------------|---------------|
| **输入** | 图像 | 文本问题 |
| **输出** | 安全违规报告 | 文本答案 + 来源 |
| **检索策略** | Per-Hazard 检索 | 单次检索 |
| **Collection** | regulations + hazard_db | qa-knowledge |
| **UI** | REST API | Chainlit 对话界面 |
| **LLM 任务** | 结构化输出 | 自由文本生成 |

## 🔍 常见问题

### Q1: 如何提高答案质量？

1. **上传高质量文档** - 文档内容准确、结构清晰
2. **调整检索参数** - 增加 `regulations_retrieval_k` 获取更多上下文
3. **优化问题表达** - 问题具体明确，包含关键词

### Q2: 如何查看检索到的文档？

- **Chainlit UI**: 点击侧边栏的来源引用
- **API**: 查看 `sources` 字段

### Q3: 为什么没有找到相关文档？

可能原因：
1. 知识库中没有相关内容 → 上传更多文档
2. 问题表达不清晰 → 重新表述问题
3. 相似度阈值过高 → 降低 `retrieval_score_threshold`

### Q4: 如何同时运行两个系统？

两个系统共享底层服务（vLLM、Qdrant），可以同时运行：

```bash
# Terminal 1: 启动 FastAPI (SafetyVision-RAG)
docker compose up -d

# Terminal 2: 启动 Chainlit (QA System)
chainlit run chainlit_app.py -w --port 8001
```

### Q5: 如何切换知识库？

通过 `collection` 参数指定：
- `collection=qa` - QA 知识库
- `collection=regulations` - 安全规范库
- `collection=hazard_db` - 危险案例库

## 🛠️ 开发与扩展

### 添加新功能

QA 系统代码结构清晰，易于扩展：

```
app/
├── api/qa.py              # API 路由
├── services/qa_service.py # 业务逻辑
├── schemas/qa.py          # 数据模型
└── core/
    ├── config.py          # 配置（已添加 QA collection）
    └── deps.py            # 依赖注入（已支持 QA）

chainlit_app.py            # Chainlit UI
```

### 自定义提示词

编辑 `app/services/qa_service.py` 中的 `_generate_answer` 方法：

```python
SystemMessage(
    content="""你是一个专业的知识问答助手...
    
    自定义要求：
    1. ...
    2. ...
    """
)
```

## 📝 总结

✅ **已实现功能**：
- RAG 知识问答服务
- Chainlit 对话界面
- REST API 接口
- 文档管理（复用）
- 两阶段检索（复用）

✅ **代码复用**：
- SafetyRetriever
- LLM 和 Embeddings
- DocumentService
- Qdrant 配置

✅ **架构优势**：
- 清晰的三层架构
- 组件高度复用
- 独立的 Collection
- 易于维护和扩展

开始使用吧！🚀
