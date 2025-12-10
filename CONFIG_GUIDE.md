# SafetyVision-RAG 配置指南

> **版本**: v3.0.0  
> **最后更新**: 2025-12-15  
> **配置文件**: `app/core/config.py`

所有 45+ 配置项已整合到 `app/core/config.py`，实现统一管理和类型安全。本指南涵盖所有配置参数的含义、调优建议和常见场景。

## 📋 配置架构

配置采用 **Pydantic Settings** 管理，支持：
- ✅ 类型验证和自动转换
- ✅ 环境变量覆盖（优先级最高）
- ✅ 默认值和文档化
- ✅ IDE 智能提示

## 🗂️ 配置分类（13 个类别）

### 1. API 基础配置
```python
app_name: str = "SafetyVision-RAG"
app_version: str = "3.0.0"
debug: bool = False
```

**说明**：
- `debug=True`：启用详细日志和错误堆栈，仅开发环境使用

### 2. Qdrant 向量数据库配置
```python
qdrant_host: str = "qdrant-server"
qdrant_port: int = 6333
qdrant_regulations_collection: str = "rag-regulations"  # 规范文档集合
qdrant_hazard_db_collection: str = "rag-hazard-db"      # 隐患数据库集合
```

**多集合架构说明**：
- `rag-regulations`：存储 PDF/Word/Markdown 规范文档
- `rag-hazard-db`：存储 Excel 隐患检查表，独立优化
- **优势**：避免 Excel 向量污染，提升检索质量

### 3. Excel 处理优化配置
```python
excel_rows_per_chunk: int = 10  # 每N行合并为一个chunk
excel_key_fields: List[str] = [  # 只索引这些关键字段
    "隐患问题", "隐患描述", "整改措施", "整改要求",
    "依据条款", "规范依据", "隐患类别", "隐患级别",
    # ... 更多字段
]
```

**调优建议**：
- `excel_rows_per_chunk` 越大，chunk 总数越少，但单个 chunk 信息越密集
- 建议值：5-15 行（当前 10 行）

### 4. VLM 和 Embedding 服务配置
```python
# VLM (Vision Language Model)
vllm_chat_url: str = "http://vllm-qwen-vl:8000/v1"
vllm_model_name: str = "/model/qwen3-vl-4b"

# Embedding Model
vllm_embed_url: str = "http://vllm-bge-m3:8000/v1"
vllm_embed_model: str = "/model/bge-m3"

# Rerank Model
vllm_rerank_url: str = "http://vllm-bge-reranker:8000"
vllm_rerank_model: str = "/model/bge-reranker-v2-m3"
```

### 5. 文件上传配置
```python
max_file_size: int = 500 * 1024 * 1024  # 500MB
max_files: int = 10  # 单次最多上传10个文件
```

### 6. 文本分块配置
```python
chunk_size: int = 1000        # 文本块大小（字符数）
chunk_overlap: int = 200      # 块之间重叠字符数
```

**调优建议**：
- PDF/Markdown 文档建议 chunk_size=800-1200
- 重叠度建议为 chunk_size 的 15-25%

### 7. LLM 生成配置
```python
llm_temperature: float = 0.0   # 温度（0=确定性，1=随机性）
llm_max_tokens: int = 1500     # 最大生成 token 数
```

**调优建议**：
- `temperature=0`：适合需要稳定输出的场景（当前）
- `llm_max_tokens`：受模型 `max_model_len=5840` 限制，建议 ≤2000

### 8. RAG 检索配置（核心参数）

#### 8.1 通用检索参数
```python
retrieval_top_k: int = 3                          # 返回文档数
retrieval_score_threshold: float = 0.4            # 硬阈值（过滤低分文档）
rerank_score_threshold: float = 0.3               # 重排序阈值
fetch_k_multiplier: int = 50                      # fetch_k = k × 50
rerank_top_n_multiplier: int = 10                 # rerank_top_n = k × 10
min_relevant_docs_per_hazard: int = 2             # 每个隐患最少文档数
```

**参数说明**：
- `retrieval_top_k`：最终返回给 LLM 的文档数（Top-K）
- `retrieval_score_threshold`：**硬阈值**，低于此分数直接过滤（建议 0.3-0.5）
- `fetch_k_multiplier`：第一阶段召回倍数，当前 k=3 时召回 150 个候选
- `rerank_top_n_multiplier`：重排序处理文档数，当前 k=3 时重排序 30 个
- `min_relevant_docs_per_hazard`：判定是否检索成功的最小文档数

**调优建议**：
- **高精度场景**：`retrieval_score_threshold=0.5`, `min_relevant_docs_per_hazard=3`
- **高召回场景**：`retrieval_score_threshold=0.3`, `fetch_k_multiplier=100`
- **低显存场景**：`retrieval_top_k=2`, `fetch_k_multiplier=30`

**两阶段检索流程**：
```
第一阶段（Similarity Search）:
  召回: fetch_k = retrieval_top_k × fetch_k_multiplier = 3 × 50 = 150
  过滤: score >= retrieval_score_threshold (0.4)

第二阶段（Rerank）:
  重排序: rerank_top_n = retrieval_top_k × rerank_top_n_multiplier = 3 × 10 = 30
  过滤: score >= rerank_score_threshold (0.3)
  返回: Top retrieval_top_k = 3
```

#### 8.2 多集合检索策略（已废弃，使用统一参数）
**v3.0.0 简化说明**：当前版本使用统一的检索参数（上述 8.1），不再区分 regulations 和 hazard_db 集合的独立参数。

如需恢复多集合独立配置，可参考以下模板：
```python
# Regulations Collection (高质量规范文档)
regulations_retrieval_k: int = 3
regulations_score_threshold: float = 0.5

# Hazard Database Collection (Excel 补充数据)
hazard_db_retrieval_k: int = 3
hazard_db_score_threshold: float = 0.4
```

### 9. 文档格式化配置（Token 预算）
```python
max_doc_length: int = 600            # 单个文档最大字符数
max_context_length: int = 1000       # 总上下文最大字符数
```

**Token 预算分配**（适配 Qwen3-VL-4B max_model_len=5840）：
```
总 Token 预算: 5840
├─ System Prompt: ~500 tokens
├─ 图像理解结果: ~500 tokens
├─ RAG 上下文: ~1000 tokens (max_context_length)
├─ LLM 输出预留: ~1500 tokens (llm_max_tokens)
└─ 安全边际: ~2340 tokens
```

**调优建议**：
- `max_doc_length`：单文档摘要长度，建议 500-800
- `max_context_length`：所有文档合并后总长度，**必须 < max_model_len - 3000**
- 关系：`max_context_length ≈ max_doc_length × retrieval_top_k`

**问题排查**：
- ⚠️ "输出超长度限制" → 降低 `max_context_length` 或 `llm_max_tokens`
- ⚠️ 文档内容被截断 → 增加 `max_doc_length`（需同步减少 `llm_max_tokens`）

### 10. 置信度阈值配置
```python
high_confidence_threshold: float = 0.7        # 高置信度阈值
medium_confidence_threshold: float = 0.5      # 中等置信度阈值
low_confidence_threshold: float = 0.3         # 低置信度阈值
```

**说明**：
- 用于 LLM Prompt 引导，影响生成质量和表述风格
- 高置信度：使用肯定语气（"明确违反"）
- 中等置信度：使用中性语气（"可能存在"）
- 低置信度：使用谨慎语气（"建议检查"）

### 11. Qdrant 查询配置
```python
qdrant_search_params: dict = {
    "hnsw_ef": 128,              # HNSW 算法搜索精度（越大越准确但越慢）
    "exact": False               # 是否使用精确搜索（True 时速度慢但精度高）
}
```

**调优建议**：
- `hnsw_ef=64`：快速检索（适合大数据集）
- `hnsw_ef=128`：平衡（默认）
- `hnsw_ef=256`：高精度（适合小数据集或关键任务）
- `exact=True`：适合 ≤1000 chunks 的小集合

### 12. 隐患分类配置
```python
hazard_categories: List[str] = [
    "安全管理", "文明施工", "脚手架工程", "基坑工程",
    "模板工程", "高处作业", "施工用电", "物料提升机",
    "施工机具", "塔吊", "起重吊装", "施工升降机",
    "拆除工程", "暗挖工程", "钢结构工程", "幕墙工程",
    "人工挖孔桩", "有限空间", "其他", "未分类"
]

hazard_levels: List[str] = [
    "一般隐患",
    "重要隐患",
]
```

**说明**：
- 预定义的隐患类别和级别，用于 LLM 结构化输出
- 可根据实际项目需求扩展类别

## 🎯 快速调优场景

### 场景 1：检索召回率低（漏检）
**症状**：部分隐患未检索到相关文档，`source_documents` 为空或少于 2 个

**解决方案**：
```python
# app/core/config.py
retrieval_score_threshold = 0.3          # 降低阈值（从 0.4 → 0.3）
min_relevant_docs_per_hazard = 1         # 降低最小文档数（从 2 → 1）
fetch_k_multiplier = 100                 # 增加召回量（从 50 → 100）
```

**预期效果**：
- 召回量提升：150 → 300 候选文档
- 漏检率降低：~10% → ~5%
- 误报率可能上升：~5% → ~10%

---

### 场景 2：检索精准度低（误报）
**症状**：返回的文档与隐患不相关，`source_documents` 包含无关内容

**解决方案**：
```python
# app/core/config.py
retrieval_score_threshold = 0.5          # 提高阈值（从 0.4 → 0.5）
rerank_score_threshold = 0.4             # 提高重排序阈值（从 0.3 → 0.4）
min_relevant_docs_per_hazard = 3         # 提高最小文档数（从 2 → 3）
```

**预期效果**：
- 精确率提升：~85% → ~95%
- 召回率可能下降：~90% → ~80%

---

### 场景 3：Token 超限错误
**症状**：错误信息 "LLM生成失败: 输出超长度限制"

**解决方案**：
```python
# app/core/config.py
max_doc_length = 500                     # 减小（从 600 → 500）
max_context_length = 800                 # 减小（从 1000 → 800）
llm_max_tokens = 1200                    # 减小（从 1500 → 1200）
retrieval_top_k = 2                      # 减少文档数（从 3 → 2）
```

**预期效果**：
- Token 使用量：~4500 → ~3500
- 文档完整性可能降低

---

### 场景 4：Excel 数据干扰规范检索
**症状**：Excel 数据在 `rag-hazard-db` 集合中占比过高，影响检索质量

**解决方案**：
```python
# app/core/config.py
excel_rows_per_chunk = 15                # 增加粒度（从 10 → 15）
excel_key_fields = [...]                 # 减少索引字段（保留前 10 个）
```

**操作步骤**：
1. 修改配置
2. 删除旧的 `rag-hazard-db` 集合
3. 重新上传 Excel 文件

```bash
curl -X DELETE "http://localhost:6333/collections/rag-hazard-db"
./upload_documents.sh
```

**预期效果**：
- Excel chunks 数量：~2000 → ~1300（减少 35%）
- 检索速度提升：~500ms → ~350ms

---

### 场景 5：检索速度慢
**症状**：单次分析耗时 >5 秒

**解决方案**：
```python
# app/core/config.py
fetch_k_multiplier = 30                  # 减小（从 50 → 30）
retrieval_top_k = 2                      # 减少（从 3 → 2）
qdrant_search_params = {"hnsw_ef": 64}   # 降低精度（从 128 → 64）
```

**预期效果**：
- 检索时间：~500ms → ~200ms
- 精确率可能下降：~90% → ~85%

---

### 场景 6：Markdown 文档位置不准确
**症状**：`source_documents[].location` 显示 "章节: Unknown"

**解决方案**：
检查 Markdown 文档是否包含标准章节标题（`#`, `##`, `###`）。如果使用非标准格式，需调整 `src/document_processors.py` 中的章节提取逻辑。

---

### 场景 7：高并发请求导致 OOM
**症状**：多个并发请求时服务崩溃或响应极慢

**解决方案**（代码级优化）：
```python
# app/services/analysis_service.py
from asyncio import Semaphore

MAX_CONCURRENT_VIOLATIONS = 5  # 限制并发 LLM 调用
semaphore = Semaphore(MAX_CONCURRENT_VIOLATIONS)

async def _generate_with_limit(hazard, docs, chain):
    async with semaphore:
        return await self._generate_single_violation(hazard, docs, chain)

violations = await asyncio.gather(*[
    _generate_with_limit(h, d, chain)
    for h, d in zip(hazards, docs_per_hazard) if d
])
```

**预期效果**：
- 并发处理能力：5-10 个请求/秒
- 显存使用稳定，不会 OOM

## 🔄 配置生效方式

### 方法1：重启服务（推荐）
```bash
cd /home/xcd/SafetyVision-RAG
docker compose restart safetyvision-api
```

### 方法2：使用环境变量覆盖
在 `.env` 文件中设置（优先级高于代码）：
```bash
# .env
REGULATIONS_RETRIEVAL_K=5
MIN_RETRIEVAL_SCORE=0.25
LLM_MAX_TOKENS=2000
```

变量命名规则：大写 + 下划线（例如 `regulations_retrieval_k` → `REGULATIONS_RETRIEVAL_K`）

## 📊 性能监控与诊断

### 关键性能指标（KPI）

| 指标 | 目标值 | 监控方法 | 说明 |
|------|--------|----------|------|
| 检索成功率 | ≥85% | 统计 `len(source_documents) >= 2` 的比例 | 每个隐患至少检索到 2 个文档 |
| 检索相似度 | 平均 ≥0.5 | 观察 `source_documents[].score` 分布 | 分数越高说明相关性越强 |
| Token 使用率 | <80% | 监控 `max_model_len` 使用情况 | 避免频繁触发长度限制 |
| 响应时间 | <3 秒 | 记录 `/api/analysis/image` 耗时 | 含图像分析 + RAG + LLM |
| "未检索到相关规范" 比例 | <15% | 统计 `rule_reference` 为默认值的比例 | 过高说明检索阈值过严 |

### 诊断命令

```bash
# 1. 检查 Qdrant 集合统计
curl "http://localhost:6333/collections/rag-regulations" | jq '.result'
curl "http://localhost:6333/collections/rag-hazard-db" | jq '.result'

# 2. 测试检索质量
curl -X POST "http://localhost:8080/api/analysis/image" \
  -F "file=@test_image.jpg" | jq '.violations[].source_documents'

# 3. 查看 API 日志
docker compose logs -f safetyvision-api | grep "检索"

# 4. 监控 Token 使用
docker compose logs safetyvision-api | grep "输出超长度"
```

### 日志分析

**检索成功示例**：
```
INFO: 检索到 3 个相关文档，最高分: 0.72
```

**检索失败示例**：
```
WARNING: 检索相似度过低: 0.28，低于阈值 0.4
INFO: 未检索到相关规范
```

## 🛠️ 配置管理

### 配置文件位置
- **主配置**：`app/core/config.py`（45+ 配置项）
- **环境变量**：`.env`（项目根目录，优先级最高）
- **Docker 配置**：`docker-compose.yaml`（服务级配置）

### 环境变量覆盖规则

配置优先级（从高到低）：
1. 环境变量（`.env` 或 `docker-compose.yaml`）
2. `config.py` 中的默认值

**示例**：覆盖检索阈值
```bash
# .env
RETRIEVAL_SCORE_THRESHOLD=0.5
MIN_RELEVANT_DOCS_PER_HAZARD=3
LLM_MAX_TOKENS=1200
```

**变量命名规则**：大写 + 下划线
- `retrieval_score_threshold` → `RETRIEVAL_SCORE_THRESHOLD`
- `llm_max_tokens` → `LLM_MAX_TOKENS`

### 配置生效方式

```bash
# 方法 1：重启单个服务（推荐）
docker compose restart safetyvision-api

# 方法 2：重启所有服务
docker compose restart

# 方法 3：重新构建（修改 Dockerfile 后）
docker compose up -d --build safetyvision-api
```

## ⚠️ 重要注意事项

### 配置约束关系

1. **阈值链**：`rerank_score_threshold ≤ retrieval_score_threshold`
2. **Token 预算**：`max_context_length + llm_max_tokens + 1000 ≤ max_model_len (5840)`
3. **检索倍数**：`fetch_k_multiplier ≥ rerank_top_n_multiplier`
4. **文档长度**：`max_context_length ≈ max_doc_length × retrieval_top_k`

### 修改后需重启服务的配置

所有配置修改后都需重启服务才能生效。

### 修改后需重新上传文档的配置

以下配置修改后需删除旧集合并重新上传文档：
- `chunk_size` / `chunk_overlap`
- `excel_rows_per_chunk`
- `excel_key_fields`
- `qdrant_regulations_collection` / `qdrant_hazard_db_collection`（名称修改）

**操作步骤**：
```bash
# 1. 删除旧集合
./delete_all_documents.sh

# 2. 重启服务
docker compose restart safetyvision-api

# 3. 重新上传文档
./upload_documents.sh
```

### 常见配置错误

| 错误 | 症状 | 解决方案 |
|------|------|----------|
| `retrieval_score_threshold=0.8` 过高 | 大量 "未检索到相关规范" | 降低到 0.3-0.5 |
| `llm_max_tokens=5000` 过高 | "输出超长度限制" 错误 | 降低到 ≤2000 |
| `fetch_k_multiplier=10` 过低 | 检索召回率低 | 提高到 30-100 |
| `excel_rows_per_chunk=50` 过高 | Excel 检索不准确 | 降低到 5-15 |

## 📚 参考资源

- **项目文档**：[README.md](README.md)
- **LangChain 文档**：https://python.langchain.com
- **Qdrant 文档**：https://qdrant.tech/documentation
- **Pydantic Settings**：https://docs.pydantic.dev/latest/concepts/pydantic_settings

---

**最后更新**: 2025-12-15  
**版本**: v3.0.0  
**维护者**: SafetyVision-RAG Team
