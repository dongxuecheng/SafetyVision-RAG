# 文档列表分页 API 使用示例

## API 端点
```
GET /documents
```

## 查询参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| purpose | string | 否 | "safety" | 文档用途：`qa` 或 `safety` |
| page | int | 否 | 1 | 页码（从1开始） |
| page_size | int | 否 | 20 | 每页数量（最小1，最大100） |

---

## 使用示例

### 1. 基础查询（使用默认值）
```bash
# 请求第1页，每页20条（默认）
curl "http://localhost:8080/documents?purpose=safety"
```

**响应示例**：
```json
{
  "total": 1234,
  "page": 1,
  "page_size": 20,
  "total_pages": 62,
  "items": [
    {
      "filename": "中华人民共和国安全生产法.pdf",
      "chunks_count": 23
    },
    {
      "filename": "建筑施工安全规范.docx",
      "chunks_count": 15
    }
    // ... 18 more items
  ]
}
```

---

### 2. 指定页码
```bash
# 请求第3页
curl "http://localhost:8080/documents?purpose=safety&page=3"
```

---

### 3. 自定义每页数量
```bash
# 每页显示50条
curl "http://localhost:8080/documents?purpose=safety&page=1&page_size=50"
```

---

### 4. QA 知识库文档
```bash
# 查询 QA 系统的文档
curl "http://localhost:8080/documents?purpose=qa&page=1&page_size=20"
```

---

### 5. 完整参数示例
```bash
# 获取第5页，每页10条
curl "http://localhost:8080/documents?purpose=safety&page=5&page_size=10"
```

---

## 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| total | int | 总文档数 |
| page | int | 当前页码 |
| page_size | int | 每页数量 |
| total_pages | int | 总页数（向上取整） |
| items | array | 当前页的文档列表 |

### items 数组元素

| 字段 | 类型 | 说明 |
|------|------|------|
| filename | string | 文档文件名 |
| chunks_count | int | 文档被切分的块数 |

---

## 错误处理

### 1. 页码非法（小于1）
```bash
curl "http://localhost:8080/documents?page=0"
```
**响应**：422 Validation Error

### 2. page_size 超过限制
```bash
curl "http://localhost:8080/documents?page_size=200"
```
**响应**：422 Validation Error（最大值为100）

### 3. purpose 参数非法
```bash
curl "http://localhost:8080/documents?purpose=invalid"
```
**响应**：422 Validation Error

---

## 前端集成示例

### JavaScript/Fetch
```javascript
async function fetchDocuments(page = 1, pageSize = 20) {
  const response = await fetch(
    `/documents?purpose=safety&page=${page}&page_size=${pageSize}`
  );
  const data = await response.json();
  
  console.log(`总共 ${data.total} 个文档`);
  console.log(`当前第 ${data.page}/${data.total_pages} 页`);
  
  return data;
}

// 使用示例
const result = await fetchDocuments(1, 20);
```

### Python/Requests
```python
import requests

def fetch_documents(page=1, page_size=20, purpose="safety"):
    url = "http://localhost:8080/documents"
    params = {
        "purpose": purpose,
        "page": page,
        "page_size": page_size
    }
    response = requests.get(url, params=params)
    return response.json()

# 使用示例
data = fetch_documents(page=1, page_size=20)
print(f"总文档数: {data['total']}")
print(f"当前页: {data['page']}/{data['total_pages']}")
```

---

## 配置说明

可以在 `app/core/config.py` 中修改默认配置：

```python
class Settings:
    # Document List Pagination Settings
    documents_default_page_size: int = 20  # 默认每页数量
    documents_max_page_size: int = 100     # 最大每页数量
    documents_min_page_size: int = 1       # 最小每页数量
```

---

## 性能优化建议

1. **前端缓存**：已加载的页面可以缓存，避免重复请求
2. **预加载**：在用户浏览时预加载下一页数据
3. **虚拟滚动**：对于大量数据，结合虚拟滚动组件提升体验
4. **搜索功能**：建议后续添加文档名搜索，减少数据量

---

## 测试命令

```bash
# 测试默认分页
curl "http://localhost:8080/documents?purpose=safety" | jq

# 测试第2页
curl "http://localhost:8080/documents?purpose=safety&page=2" | jq

# 测试大页面
curl "http://localhost:8080/documents?purpose=safety&page_size=50" | jq

# 测试 QA 文档
curl "http://localhost:8080/documents?purpose=qa" | jq
```

---

## 后续优化方向

1. **搜索功能**：添加 `search` 参数过滤文档名
2. **排序功能**：添加 `sort_by` 参数（文件名、块数、上传时间）
3. **集合过滤**：添加 `collection` 参数过滤特定集合
4. **游标分页**：对于超大数据集，考虑实现游标分页
