# 文档管理接口使用指南

## 📚 系统架构

SafetyVision-RAG 系统支持两大功能模块，每个模块使用独立的向量数据库集合：

### 1. **RAG 知识问答系统** (`purpose=qa`)
- **用途**：通用知识问答，基于文档库回答用户问题
- **集合**：`rag-qa-knowledge`
- **支持格式**：PDF, Word, Markdown（**不支持 Excel**）

### 2. **隐患识别系统** (`purpose=safety`)
- **用途**：施工现场图片隐患检测与规范引用
- **集合**：
  - `rag-regulations`：法规文档（PDF, Word, Markdown）
  - `rag-hazard-db`：隐患数据库（Excel）
- **自动路由**：Excel → hazard_db，其他 → regulations

## 🔧 API 接口

### 1. 上传文档

**接口**：`POST /api/documents/upload`

**参数**：
- `purpose`: 文档用途（必选）
  - `qa`：RAG 知识问答
  - `safety`：隐患识别（默认）
- `files`: 文件列表
- `skip_existing`: 跳过已存在文件（默认 true）

**示例**：

```bash
# 上传文档到 RAG 知识问答系统
curl -X POST "http://localhost:8080/api/documents/upload?purpose=qa" \
  -F "files=@施工安全手册.pdf" \
  -F "files=@常见问题解答.md"

# 上传文档到隐患识别系统（自动路由）
curl -X POST "http://localhost:8080/api/documents/upload?purpose=safety" \
  -F "files=@JGJ80-2016建筑施工高处作业安全技术规范.pdf" \
  -F "files=@隐患案例库.xlsx"
```

**路由规则**：

| Purpose | 文件类型 | 目标集合 | 说明 |
|---------|---------|---------|------|
| `qa` | PDF/Word/Markdown | `rag-qa-knowledge` | QA 知识库 |
| `qa` | Excel | ❌ 拒绝 | QA 不支持 Excel |
| `safety` | Excel | `rag-hazard-db` | 隐患数据库 |
| `safety` | PDF/Word/Markdown | `rag-regulations` | 法规文档 |

### 2. 列表文档

**接口**：`GET /api/documents`

**参数**：
- `purpose`: 文档用途（必选）
  - `qa`：列出 QA 系统的文档
  - `safety`：列出隐患识别系统的文档（默认）

**示例**：

```bash
# 查看 QA 系统的文档
curl "http://localhost:8080/api/documents?purpose=qa"

# 查看隐患识别系统的文档（regulations + hazard_db）
curl "http://localhost:8080/api/documents?purpose=safety"
```

### 3. 删除文档

**接口**：`DELETE /api/documents`

**参数**：
- `filenames`: 要删除的文件名列表（必选）
- `purpose`: 文档用途（必选）
  - `qa`：从 QA 系统删除
  - `safety`：从隐患识别系统删除（默认）

**示例**：

```bash
# 从 QA 系统删除文档
curl -X DELETE "http://localhost:8080/api/documents?purpose=qa&filenames=test.md"

# 从隐患识别系统删除文档（自动从 regulations 和 hazard_db 中查找）
curl -X DELETE "http://localhost:8080/api/documents?purpose=safety&filenames=old_doc.pdf"
```

## 🎯 完整使用场景

### 场景 1: 构建 RAG 知识问答系统

```bash
# 1. 上传知识库文档
curl -X POST "http://localhost:8080/api/documents/upload?purpose=qa" \
  -F "files=@施工安全手册.pdf" \
  -F "files=@常见问题解答.md" \
  -F "files=@技术规范汇编.docx"

# 2. 验证上传成功
curl "http://localhost:8080/api/documents?purpose=qa"

# 3. 通过 API 测试问答
curl -X POST "http://localhost:8080/api/qa/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "什么是高处作业？有哪些等级？"}'

# 4. 使用 Chainlit Web UI（推荐）
# 浏览器访问: http://localhost:8001
```

### 场景 2: 构建隐患识别系统

```bash
# 1. 上传法规文档（PDF/Word/Markdown → regulations）
curl -X POST "http://localhost:8080/api/documents/upload?purpose=safety" \
  -F "files=@JGJ80-2016建筑施工高处作业安全技术规范.pdf" \
  -F "files=@GB50720-2011建设工程施工现场消防安全技术规范.pdf"

# 2. 上传隐患数据库（Excel → hazard_db）
curl -X POST "http://localhost:8080/api/documents/upload?purpose=safety" \
  -F "files=@隐患案例库.xlsx" \
  -F "files=@整改措施汇总.xls"

# 3. 验证上传成功
curl "http://localhost:8080/api/documents?purpose=safety"

# 4. 测试图片隐患识别
curl -X POST "http://localhost:8080/api/analysis/image" \
  -F "image=@施工现场照片.jpg"
```

### 场景 3: 文档管理操作

```bash
# 查看各系统的文档统计
curl "http://localhost:8080/api/documents?purpose=qa" | jq 'length'
curl "http://localhost:8080/api/documents?purpose=safety" | jq 'length'

# 删除过时文档
curl -X DELETE "http://localhost:8080/api/documents?purpose=qa&filenames=旧版手册.pdf"
curl -X DELETE "http://localhost:8080/api/documents?purpose=safety&filenames=过期规范.pdf"

# 重新上传更新后的文档
curl -X POST "http://localhost:8080/api/documents/upload?purpose=qa" \
  -F "files=@新版手册.pdf"
```

## ⚠️ 重要注意事项

### 1. **文件格式限制**

| 用途 | 支持格式 | 不支持格式 |
|------|---------|-----------|
| **QA 系统** (`qa`) | PDF, Word, Markdown | ❌ Excel |
| **隐患识别** (`safety`) | PDF, Word, Markdown, Excel | - |

**QA 系统不支持 Excel 的原因**：
- QA 系统需要连续的文本内容
- Excel 的结构化数据不适合自然语言问答

### 2. **文档路由规则**

```
purpose=qa:
  ├─ PDF/Word/Markdown → rag-qa-knowledge ✓
  └─ Excel → 拒绝上传 ✗

purpose=safety:
  ├─ PDF/Word/Markdown → rag-regulations ✓
  └─ Excel → rag-hazard-db ✓
```

### 3. **知识库隔离**

两个系统的知识库**完全独立**：
- QA 系统查询 `rag-qa-knowledge` 集合
- 隐患识别查询 `rag-regulations` + `rag-hazard-db` 集合
- 互不干扰，避免混淆

### 4. **默认参数**

所有接口的 `purpose` 参数默认值为 `safety`（隐患识别），保持向后兼容。

## 📊 系统架构

```
┌─────────────────────────────────────────────────┐
│              SafetyVision-RAG                   │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────┐         ┌──────────────┐    │
│  │隐患识别系统   │         │知识问答系统   │    │
│  └──────┬───────┘         └──────┬───────┘    │
│         │                        │             │
│         ├─── regulations         └─── qa       │
│         └─── hazard_db                         │
│                                                 │
│  ┌─────────────────────────────────────────┐  │
│  │          Qdrant Vector Store            │  │
│  ├─────────────────────────────────────────┤  │
│  │ • rag-regulations (法规)                │  │
│  │ • rag-hazard-db (隐患库)                │  │
│  │ • rag-qa-knowledge (QA知识)             │  │
│  └─────────────────────────────────────────┘  │
│                                                 │
└─────────────────────────────────────────────────┘
```

## 🔗 相关文档

- [QA_SYSTEM_GUIDE.md](QA_SYSTEM_GUIDE.md) - 知识问答系统完整指南
- [QUICKSTART_QA.md](QUICKSTART_QA.md) - QA 系统快速开始
- [RAG-README.md](RAG-README.md) - 项目整体说明
