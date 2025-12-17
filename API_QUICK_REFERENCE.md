# 📘 API 快速参考

## 文档管理接口

### 🔹 参数说明

**purpose** - 文档用途（2 选 1）：
- `qa` - RAG 知识问答系统
- `safety` - 隐患识别系统（默认）

---

### 📤 上传文档

```bash
POST /api/documents/upload?purpose=<qa|safety>
```

**示例**：
```bash
# QA 系统
curl -X POST "http://localhost:8080/api/documents/upload?purpose=qa" \
  -F "files=@文档.pdf"

# 隐患识别
curl -X POST "http://localhost:8080/api/documents/upload?purpose=safety" \
  -F "files=@规范.pdf" \
  -F "files=@隐患库.xlsx"
```

**路由规则**：
- `qa` + PDF/Word/Markdown → `rag-qa-knowledge`
- `qa` + Excel → ❌ 拒绝
- `safety` + Excel → `rag-hazard-db`
- `safety` + PDF/Word/Markdown → `rag-regulations`

---

### 📋 列表文档

```bash
GET /api/documents?purpose=<qa|safety>
```

**示例**：
```bash
# 查看 QA 系统文档
curl "http://localhost:8080/api/documents?purpose=qa"

# 查看隐患识别文档
curl "http://localhost:8080/api/documents?purpose=safety"
```

---

### 🗑️ 删除文档

```bash
DELETE /api/documents?purpose=<qa|safety>&filenames=<文件名>
```

**示例**：
```bash
# 从 QA 系统删除
curl -X DELETE "http://localhost:8080/api/documents?purpose=qa&filenames=old.pdf"

# 从隐患识别删除
curl -X DELETE "http://localhost:8080/api/documents?purpose=safety&filenames=doc.pdf"
```

---

## 知识问答接口

### 💬 问答查询

```bash
POST /api/qa/ask
Content-Type: application/json
```

**示例**：
```bash
curl -X POST "http://localhost:8080/api/qa/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "什么是高处作业？"}'
```

**Chainlit Web UI**：http://localhost:8001

---

## 隐患识别接口

### �� 图片分析

```bash
POST /api/analysis/image
```

**示例**：
```bash
curl -X POST "http://localhost:8080/api/analysis/image" \
  -F "image=@现场照片.jpg"
```

---

## 🎯 常用场景

### 场景 1: 搭建 QA 知识库

```bash
# 1. 上传知识文档
curl -X POST "http://localhost:8080/api/documents/upload?purpose=qa" \
  -F "files=@handbook.pdf"

# 2. 验证
curl "http://localhost:8080/api/documents?purpose=qa"

# 3. 测试问答
curl -X POST "http://localhost:8080/api/qa/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "问题"}'
```

### 场景 2: 搭建隐患识别系统

```bash
# 1. 上传法规和隐患库
curl -X POST "http://localhost:8080/api/documents/upload?purpose=safety" \
  -F "files=@规范.pdf" \
  -F "files=@隐患.xlsx"

# 2. 识别图片隐患
curl -X POST "http://localhost:8080/api/analysis/image" \
  -F "image=@photo.jpg"
```

---

## 💡 提示

1. **QA 系统不支持 Excel**：只接受 PDF/Word/Markdown
2. **默认 purpose=safety**：可省略参数
3. **批量上传**：可同时上传多个文件
4. **自动路由**：系统根据 purpose 和文件类型自动选择集合

---

## 📚 详细文档

- [COLLECTION_USAGE.md](COLLECTION_USAGE.md) - 完整使用指南
- [QA_SYSTEM_GUIDE.md](QA_SYSTEM_GUIDE.md) - QA 系统详解
- [IMAGE_RECOGNITION_TROUBLESHOOTING.md](IMAGE_RECOGNITION_TROUBLESHOOTING.md) - 图片识别故障排查
