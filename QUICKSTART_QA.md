# 🚀 RAG 知识问答系统 - 快速启动

## 📦 一键部署

### 1. 安装依赖
```bash
pip install chainlit>=1.0.0
# 或更新所有依赖
pip install -r requirements.txt
```

### 2. 启动服务

#### 选项 A: 启动 Chainlit UI（推荐）
```bash
chainlit run chainlit_app.py -w
# 访问: http://localhost:8000
```

#### 选项 B: 仅使用 API
```bash
# FastAPI 已通过 docker compose 运行
# API 文档: http://localhost:8080/docs
# 测试: python test_qa_system.py
```

### 3. 上传知识文档
```bash
# 方法 1: 通过 API 上传
curl -X POST "http://localhost:8080/api/documents/upload?collection=qa" \
  -F "files=@your-document.pdf"

# 方法 2: 通过 Swagger UI
# 访问 http://localhost:8080/docs
# 找到 POST /api/documents/upload
# 设置 collection=qa
# 上传文件
```

## ✅ 验证

### 测试 Chainlit UI
1. 访问 http://localhost:8000
2. 输入问题: "你好，请介绍一下自己"
3. 查看回复

### 测试 REST API
```bash
# 健康检查
curl http://localhost:8080/api/qa/health

# 提问
curl -X POST "http://localhost:8080/api/qa/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "什么是安全施工？"}'

# 或运行测试脚本
python test_qa_system.py
```

## 🎯 示例对话

**用户**: 什么是高处作业？

**助手**: 根据《建筑施工安全规范》，高处作业是指凡在坠落高度基准面2m以上（含2m）有可能坠落的高处进行的作业...

📚 **参考来源**:
1. 建筑施工安全规范.pdf (相似度: 0.85)
2. 安全技术规范.xlsx (相似度: 0.76)

## 🔧 配置调优

### 提高检索质量
编辑 `app/core/config.py`:
```python
regulations_retrieval_k: int = 7  # 增加返回文档数
retrieval_score_threshold: float = 0.3  # 降低阈值（召回更多）
```

### 自定义 Chainlit 配置
编辑 `.chainlit`:
```toml
[UI]
name = "我的知识库"
description = "专业领域问答助手"
```

## 📊 性能指标

- **检索延迟**: ~200-500ms
- **生成延迟**: ~1-3s
- **总响应时间**: ~2-4s
- **并发支持**: 10+ 用户

## 🐛 故障排查

### 问题 1: Chainlit 启动失败
```bash
# 检查依赖
pip list | grep chainlit

# 重新安装
pip install --upgrade chainlit
```

### 问题 2: 没有返回答案
- ✅ 检查是否上传了文档
- ✅ 查看日志: `docker compose logs -f safetyvision-api`
- ✅ 降低 `retrieval_score_threshold`

### 问题 3: API 连接失败
```bash
# 检查服务状态
docker compose ps

# 重启服务
docker compose restart safetyvision-api
```

## 📚 更多信息

详细文档: [QA_SYSTEM_GUIDE.md](./QA_SYSTEM_GUIDE.md)

项目架构:
```
SafetyVision-RAG/
├── chainlit_app.py          # Chainlit UI 入口
├── test_qa_system.py        # API 测试脚本
├── app/
│   ├── api/qa.py            # QA REST API
│   ├── services/qa_service.py  # QA 业务逻辑
│   └── schemas/qa.py        # QA 数据模型
└── .chainlit                # Chainlit 配置
```

开始使用吧！🎉
