# 更新日志

## 2025-11-28 - 多格式文档支持

### 新增功能

#### 支持的文档格式
- ✅ **PDF** (`.pdf`) - 使用 PyPDFLoader，传统 Chunking 策略
- ✅ **Word 新版** (`.docx`) - 使用 python-docx，传统 Chunking 策略  
- ✅ **Word 旧版** (`.doc`) - 使用 antiword 工具，传统 Chunking 策略
- ✅ **Excel 新版** (`.xlsx`) - 使用 openpyxl，Row-to-Text 策略
- ✅ **Excel 旧版** (`.xls`) - 使用 xlrd，Row-to-Text 策略

#### Excel Row-to-Text 策略详解

**核心思想**：将 Excel 表格每一行数据结合表头，转换为具有完整语义的自然语言文本。

**示例**：
```
原始数据：
| 姓名 | 职位 | 部门     |
|------|------|----------|
| 张三 | 经理 | 技术部   |
| 李四 | 工程师 | 研发部 |

转换后：
第2行数据：姓名为张三，职位为经理，部门为技术部。
第3行数据：姓名为李四，职位为工程师，部门为研发部。
```

**优势**：
- ✅ 支持自然语言查询："经理是谁" → 找到"张三"
- ✅ 保留结构信息："技术部有谁" → 找到相关人员
- ✅ 语义完整，便于向量检索

### 技术实现

#### 依赖更新
```
openpyxl       # Excel 2007+ (.xlsx)
python-docx    # Word 2007+ (.docx)
xlrd          # Excel 97-2003 (.xls)
antiword      # Word 97-2003 (.doc) - 系统工具
```

#### 架构设计
- 工厂模式：`DocumentProcessorFactory` 统一入口
- 独立处理器：每种格式对应一个处理器类
- 清晰职责：PDF/Word 传统分块，Excel 行转文本

### 配置更新
- 文件大小限制：10MB → **50MB**
- 支持格式：`.pdf`, `.docx`, `.doc`, `.xlsx`, `.xls`

### 使用示例

#### 上传文档
```bash
curl -X POST "http://localhost:8000/api/documents/upload" \
  -F "files=@document.doc" \
  -F "files=@data.xls"
```

#### 响应示例
```json
{
  "success": true,
  "message": "Processed 2 files, 2 succeeded",
  "details": [
    {
      "filename": "document.doc",
      "status": "success",
      "chunks": 15,
      "message": "Uploaded successfully"
    },
    {
      "filename": "data.xls",
      "status": "success",
      "chunks": 127,
      "message": "Uploaded successfully"
    }
  ]
}
```

### 技术说明

#### .doc 文件处理
使用 `antiword` 命令行工具提取文本：
- 支持 Word 97-2003 格式
- 纯文本提取，保留基本格式
- 系统级工具，稳定可靠

#### .xls 文件处理  
使用 `xlrd` 库读取二进制格式：
- 支持 Excel 97-2003 格式
- 读取所有 sheet
- 自动处理日期类型

### 错误处理
- 文件格式不支持：返回友好提示
- 文件过大：50MB 限制提示
- 提取失败：详细错误信息

### 性能优化
- 流式处理大文件
- 只读模式打开 Excel
- 高效的文本分块算法
