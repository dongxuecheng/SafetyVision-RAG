# Collection 参数使用指南

## 📚 三个 Qdrant Collections

SafetyVision-RAG 系统现在支持三个独立的向量数据库集合：

| Collection | 用途 | 文件类型 | API 参数值 |
|-----------|------|---------|-----------|
| `rag-regulations` | **隐患识别** - 法规文档 | PDF, Word, Markdown | `regulations` |
| `rag-hazard-db` | **隐患识别** - 隐患数据库 | Excel | `hazard_db` |
| `rag-qa-knowledge` | **知识问答** - QA 知识库 | PDF, Word, Markdown | `qa` |

## 🔧 API 接口

### 1. 上传文档

```bash
# 自动识别（默认）：Excel -> hazard_db, 其他 -> regulations
POST /api/documents/upload?collection=auto

# 上传到法规库（用于隐患识别）
POST /api/documents/upload?collection=regulations

# 上传到隐患数据库（用于隐患识别）
POST /api/documents/upload?collection=hazard_db

# 上传到知识问答库（用于 QA 系统）
POST /api/documents/upload?collection=qa
```

**示例**：
```bash
# 上传知识文档到 QA 系统
curl -X POST "http://localhost:8080/api/documents/upload?collection=qa" \
  -F "files=@知识库文档.pdf"

# 自动识别（Excel -> hazard_db, PDF -> regulations）
curl -X POST "http://localhost:8080/api/documents/upload?collection=auto" \
  -F "files=@隐患清单.xlsx" \
  -F "files=@安全规范.pdf"
```

### 2. 列表文档

```bash
# 列出所有集合的文档
GET /api/documents?collection=all

# 仅列出法规库文档
GET /api/documents?collection=regulations

# 仅列出隐患数据库文档
GET /api/documents?collection=hazard_db

# 仅列出知识问答库文档
GET /api/documents?collection=qa
```

**示例**：
```bash
# 查看 QA 系统的知识库
curl "http://localhost:8080/api/documents?collection=qa"

# 查看隐患识别系统的所有文档（regulations + hazard_db）
curl "http://localhost:8080/api/documents?collection=regulations"
curl "http://localhost:8080/api/documents?collection=hazard_db"
```

### 3. 删除文档

```bash
# 从所有集合删除
DELETE /api/documents?collection=all&filenames=文件名.pdf

# 仅从法规库删除
DELETE /api/documents?collection=regulations&filenames=文件名.pdf

# 仅从知识问答库删除
DELETE /api/documents?collection=qa&filenames=文件名.md
```

**示例**：
```bash
# 从 QA 知识库删除特定文档
curl -X DELETE "http://localhost:8080/api/documents?collection=qa&filenames=test.md"

# 从所有集合删除
curl -X DELETE "http://localhost:8080/api/documents?collection=all&filenames=old_doc.pdf"
```

## 🎯 使用场景

### 场景 1: 构建知识问答系统

```bash
# 1. 上传知识库文档到 qa 集合
curl -X POST "http://localhost:8080/api/documents/upload?collection=qa" \
  -F "files=@施工安全手册.pdf" \
  -F "files=@常见问题解答.md"

# 2. 验证上传
curl "http://localhost:8080/api/documents?collection=qa"

# 3. 测试问答
curl -X POST "http://localhost:8080/api/qa/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "什么是高处作业？"}'

# 4. 使用 Chainlit UI
# 浏览器访问 http://localhost:8001
```

### 场景 2: 构建隐患识别系统

```bash
# 1. 上传法规文档（自动识别）
curl -X POST "http://localhost:8080/api/documents/upload?collection=auto" \
  -F "files=@JGJ80-2016建筑施工高处作业安全技术规范.pdf"

# 2. 上传隐患数据库（自动识别）
curl -X POST "http://localhost:8080/api/documents/upload?collection=auto" \
  -F "files=@隐患案例库.xlsx"

# 3. 验证上传
curl "http://localhost:8080/api/documents?collection=all"

# 4. 测试隐患识别
curl -X POST "http://localhost:8080/api/analysis/image" \
  -F "image=@施工现场.jpg"
```

## ⚠️ 注意事项

1. **Collection 参数验证**：
   - 上传: `auto`, `regulations`, `hazard_db`, `qa`
   - 列表/删除: `all`, `regulations`, `hazard_db`, `qa`
   - 无效值会返回 400 错误

2. **自动识别规则** (`collection=auto`):
   - `.xlsx`, `.xls` → `hazard_db`
   - `.pdf`, `.docx`, `.md` → `regulations`

3. **隔离性**：
   - 隐患识别系统使用 `regulations` + `hazard_db`
   - QA 系统使用 `qa`
   - 两个系统的知识库完全独立

4. **向后兼容**：
   - 默认 `collection=auto`，保持原有行为
   - 现有 API 调用无需修改

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
