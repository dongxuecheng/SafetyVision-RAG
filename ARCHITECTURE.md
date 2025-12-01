# SafetyVision-RAG Architecture

## 架构概览

本项目采用 **Clean Architecture**（清洁架构）设计，遵循 FastAPI 最佳实践，实现代码的高内聚、低耦合，便于测试和维护。

## 目录结构

```
SafetyVision-RAG/
├── app/                          # 应用程序主目录
│   ├── __init__.py
│   ├── main.py                   # 应用入口（Application Factory）
│   │
│   ├── api/                      # API 路由层（Presentation Layer）
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── documents.py      # 文档管理 API
│   │       └── analysis.py       # 图像分析 API
│   │
│   ├── core/                     # 核心模块（Infrastructure）
│   │   ├── __init__.py
│   │   ├── config.py             # Pydantic Settings 配置
│   │   └── deps.py               # 依赖注入函数
│   │
│   ├── schemas/                  # 数据模型（DTO/Request/Response）
│   │   ├── __init__.py
│   │   └── safety.py             # API 请求/响应模型
│   │
│   ├── services/                 # 业务逻辑层（Business Logic Layer）
│   │   ├── __init__.py
│   │   ├── document_service.py   # 文档处理服务
│   │   └── analysis_service.py   # 安全分析服务
│   │
│   └── models/                   # 数据库模型（未使用）
│       └── __init__.py
│
├── src/                          # 工具模块
│   ├── __init__.py
│   └── document_processors.py    # 文档处理器工厂
│
└── file/                         # 上传文件存储
```

## 分层架构

### 1. API 路由层 (`app/api/routes/`)

**职责**: 处理 HTTP 请求，验证输入，返回响应

- `documents.py`: 文档上传、列表、删除
- `analysis.py`: 图像安全分析

**特点**:
- 使用 FastAPI 路由装饰器
- 依赖注入（Depends）获取服务实例
- 最小业务逻辑，委托给服务层

### 2. 服务层 (`app/services/`)

**职责**: 实现核心业务逻辑

- `DocumentService`: 文档上传、存储、向量化、查询、删除
- `AnalysisService`: 图像分析、RAG 链构建、安全检测

**特点**:
- 单一职责原则
- 独立于框架，易于测试
- 封装复杂逻辑（LangChain 集成）

### 3. 核心模块 (`app/core/`)

**职责**: 提供配置和依赖注入

- `config.py`: 
  - Pydantic Settings 管理环境变量
  - 类型安全的配置
  - 支持 `.env` 文件
  
- `deps.py`:
  - 提供共享资源（Qdrant、LLM、Embeddings）
  - 使用 `lru_cache` 实现单例模式
  - 自动资源清理（lifespan）

### 4. 数据模型 (`app/schemas/`)

**职责**: 定义 API 输入/输出结构

- `SafetyViolation`: 安全违规项
- `SafetyReport`: 安全分析报告
- `DocumentDetail`: 文档详情
- `DocumentUploadResponse`: 上传响应

**特点**:
- Pydantic 自动验证
- 自动生成 OpenAPI 文档
- 类型安全

## 核心设计模式

### 1. 依赖注入（Dependency Injection）

```python
# app/core/deps.py
@lru_cache
def get_qdrant_client() -> QdrantClient:
    settings = get_settings()
    return QdrantClient(url=settings.QDRANT_URL)

# app/api/routes/documents.py
@router.post("/upload")
async def upload_documents(
    files: List[UploadFile],
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
    embeddings: OpenAIEmbeddings = Depends(get_embeddings)
):
    service = DocumentService(qdrant_client, embeddings)
    # ...
```

### 2. 应用工厂模式（Application Factory）

```python
# app/main.py
def create_app() -> FastAPI:
    app = FastAPI(
        title="SafetyVision-RAG",
        lifespan=lifespan
    )
    app.include_router(documents_router, prefix="/api/documents")
    app.include_router(analysis_router, prefix="/api/analysis")
    return app

app = create_app()
```

### 3. 服务层模式（Service Layer）

```python
# app/services/document_service.py
class DocumentService:
    def __init__(self, qdrant_client, embeddings):
        self.qdrant_client = qdrant_client
        self.embeddings = embeddings
    
    async def upload_documents(self, files, skip_existing):
        # 业务逻辑实现
        ...
```

## 关键改进

### 相比旧架构（单文件 main.py）

| 方面 | 旧架构 | 新架构 |
|------|--------|--------|
| **代码组织** | 单文件 457 行 | 分层目录，每个文件 < 200 行 |
| **职责分离** | 混杂在一起 | API/Service/Core 清晰分离 |
| **可测试性** | 难以测试 | 服务层可独立测试 |
| **配置管理** | 环境变量 + 硬编码 | Pydantic Settings 统一管理 |
| **依赖管理** | 全局变量 | 依赖注入 + 单例缓存 |
| **可维护性** | 难以扩展 | 遵循 SOLID 原则 |

### 具体优化

1. **删除冗余端点**
   - `/health`: 不需要的健康检查
   - `/root`: 简单的欢迎消息

2. **多格式文档支持**
   - PDF: 传统 Chunking
   - DOCX/DOC: 段落提取
   - XLSX/XLS: Row-to-Text 行级语义搜索

3. **增强 RAG 响应**
   - `rule_reference` 字段包含源文件名
   - 用户可追溯答案来源

4. **统一错误处理**
   - 使用 HTTPException
   - 返回一致的错误格式

## 技术栈

- **Web 框架**: FastAPI 0.115+
- **配置管理**: Pydantic Settings
- **LLM 框架**: LangChain
- **向量数据库**: Qdrant
- **文档处理**: pypdf, python-docx, openpyxl, xlrd, antiword
- **容器化**: Docker + Docker Compose

## 最佳实践

1. ✅ **类型注解**: 所有函数都有完整类型注解
2. ✅ **依赖注入**: 避免全局状态，提高可测试性
3. ✅ **异步优先**: 使用 `async/await` 提升性能
4. ✅ **配置外部化**: 使用环境变量和 Pydantic Settings
5. ✅ **单一职责**: 每个模块职责清晰
6. ✅ **开闭原则**: 易于扩展，无需修改现有代码
7. ✅ **接口隔离**: 服务层与框架解耦

## 测试策略

### 单元测试（推荐）

```python
# tests/test_document_service.py
def test_upload_documents():
    mock_qdrant = MagicMock()
    mock_embeddings = MagicMock()
    service = DocumentService(mock_qdrant, mock_embeddings)
    # 测试业务逻辑
```

### 集成测试

```python
# tests/test_api.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_upload_endpoint():
    response = client.post("/api/documents/upload", files=...)
    assert response.status_code == 200
```

## 部署

### Docker 部署

```bash
docker-compose up -d
```

### 健康检查

所有服务都有健康检查：
- Qdrant: `http://qdrant-server:6333/`
- VLM: `http://vllm-qwen-vl:8000/health`
- BGE-m3: `http://vllm-bge-m3:8000/health`

## 扩展指南

### 添加新端点

1. 在 `app/schemas/` 定义请求/响应模型
2. 在 `app/services/` 实现业务逻辑
3. 在 `app/api/routes/` 添加路由
4. 在 `app/main.py` 注册路由

### 添加新服务

1. 创建 `app/services/new_service.py`
2. 定义服务类和方法
3. 在 `app/core/deps.py` 添加依赖注入函数
4. 在路由中使用 `Depends(get_new_service)`

## 参考资料

- [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices)
- [FastAPI Project Structure](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [LangChain Documentation](https://python.langchain.com/docs/get_started/introduction)
