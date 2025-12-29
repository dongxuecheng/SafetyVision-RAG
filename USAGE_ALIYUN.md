# 阿里云API版本 - 使用指南

## 快速开始

### 1. 获取API Key

访问阿里云百炼控制台：
- 北京地域: https://bailian.console.aliyun.com/
- API Key管理: https://help.aliyun.com/zh/model-studio/get-api-key

**注意**：北京地域和新加坡地域的API Key是不同的

### 2. 配置环境

```bash
# 切换到阿里云API分支
cd /home/xcd/SafetyVision-RAG
git checkout feature/aliyun-api

# 复制配置模板
cp .env.aliyun.example .env

# 编辑配置文件，填入API Key
nano .env
# 修改 DASHSCOPE_API_KEY=sk-your-actual-key
```

### 3. 启动服务

```bash
# 使用快速启动脚本（推荐）
./start_aliyun.sh

# 或手动启动
docker compose -f docker-compose.aliyun.yaml up -d
```

### 4. 验证服务

```bash
# 检查服务状态
docker compose -f docker-compose.aliyun.yaml ps

# 查看日志
docker compose -f docker-compose.aliyun.yaml logs -f safetyvision-api
```

## API测试

### 测试图像分析（使用阿里云qwen3-vl-plus）

```bash
curl -X POST "http://localhost:8080/api/analysis/image" \
  -F "file=@test_image.jpg"
```

预期响应：
```json
{
  "violations": [
    {
      "hazard_id": 1,
      "hazard_description": "作业人员未佩戴安全帽",
      "hazard_category": "安全防护",
      "hazard_level": "重大隐患",
      "recommendations": "1. 立即停止作业\n2. 要求所有人员佩戴安全帽",
      "rule_reference": "《建筑施工安全检查标准》...",
      "source_documents": [...]
    }
  ]
}
```

### 测试RAG问答（使用阿里云qwen3-max-preview）

访问Chainlit UI：http://localhost:25810

或通过API：
```python
import requests

response = requests.post(
    "http://localhost:8080/api/qa/query",
    json={"query": "脚手架搭设规范有哪些要求？"}
)
print(response.json())
```

## 架构对比

### 原版（自托管vllm）
```
┌─────────────────┐
│  vllm-qwen-vl   │  GPU: ~8GB
│   (多模态)      │
└─────────────────┘
        ↓
┌─────────────────┐
│  vllm-bge-m3    │  GPU: ~2GB
│   (embedding)   │
└─────────────────┘
        ↓
┌─────────────────┐
│vllm-bge-reranker│  GPU: ~2GB
│   (reranker)    │
└─────────────────┘

总GPU需求: ~12GB
```

### 阿里云API版（本分支）
```
┌─────────────────┐
│  阿里云API      │  按调用付费
│  qwen3-vl-plus  │  无需GPU
│  qwen3-max      │
└─────────────────┘
        ↓
┌─────────────────┐
│  vllm-bge-m3    │  GPU: ~2GB
│   (embedding)   │  自托管
└─────────────────┘
        ↓
┌─────────────────┐
│vllm-bge-reranker│  GPU: ~2GB
│   (reranker)    │  自托管
└─────────────────┘

总GPU需求: ~4GB
节省: 8GB GPU
```

## 成本分析

### GPU成本对比

**自托管vllm版本**：
- GPU需求: 12GB VRAM（RTX 3090/4090或A4000）
- 云服务器成本: ¥2-4/小时（按量付费）
- 包年包月: ¥1500-3000/月

**阿里云API版本**：
- GPU需求: 4GB VRAM（GTX 1660 Ti或更低）
- 云服务器成本: ¥0.5-1/小时
- 包年包月: ¥400-800/月
- **节省: 50-70% GPU成本**

### API调用成本

**qwen3-vl-plus** (图像分析):
- 输入: ¥0.004/1K tokens
- 输出: ¥0.012/1K tokens
- 图片处理: 约1000-2000 tokens（根据分辨率）
- 单次调用: ¥0.01-0.05

**qwen3-max-preview** (RAG问答):
- 输入: ¥0.02/1K tokens
- 输出: ¥0.06/1K tokens
- 单次调用: ¥0.05-0.2（含检索上下文）

**每日使用估算**：
- 图像分析: 100次/天 × ¥0.03 = ¥3
- RAG问答: 500次/天 × ¥0.1 = ¥50
- **每月总计: ¥1590**

**结论**：
- 低频使用（<30次/天）: 阿里云API更划算
- 中频使用（30-200次/天）: 持平或略贵
- 高频使用（>200次/天）: 自托管更划算

## 性能对比

### 模型能力

| 维度 | 自托管qwen3-vl-4b | 阿里云qwen3-vl-plus |
|------|------------------|-------------------|
| 参数量 | 4B | ~32B (估计) |
| 图像理解 | ★★★☆☆ | ★★★★★ |
| 中文能力 | ★★★★☆ | ★★★★★ |
| 指令遵循 | ★★★☆☆ | ★★★★★ |
| 推理速度 | 快 | 中等 |

### 响应延迟

| 操作 | 自托管 | 阿里云API |
|------|-------|-----------|
| 图像分析 | 2-5秒 | 3-8秒 |
| RAG问答 | 1-3秒 | 2-5秒 |
| Embedding | 0.1秒 | 0.1秒 |

**网络影响**：国内网络访问阿里云API延迟+50-200ms

## 故障排查

### 1. API Key错误

```bash
# 错误信息
ValueError: DashScope API Key not found

# 解决方案
# 检查.env文件
cat .env | grep DASHSCOPE_API_KEY

# 测试API Key
curl -X POST "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-turbo","messages":[{"role":"user","content":"test"}]}'
```

### 2. 网络连接问题

```bash
# 测试阿里云连接
curl -v https://dashscope.aliyuncs.com

# 如果使用代理
export HTTP_PROXY=http://your-proxy:port
export HTTPS_PROXY=http://your-proxy:port
```

### 3. 图片base64编码问题

```python
# 检查图片编码是否正确
import base64

with open("test.jpg", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()
    print(f"Base64 length: {len(b64)}")
    print(f"Data URL: data:image/jpeg;base64,{b64[:50]}...")
```

### 4. 模型限流

```
错误: Rate limit exceeded

原因: API调用频率过高
解决: 
1. 降低并发请求数
2. 添加请求间隔（time.sleep）
3. 联系阿里云提升配额
```

## 回退到自托管版本

```bash
# 切换回主分支
git checkout main

# 启动原有服务
docker compose up -d
```

## 技术细节

### Base64图片编码流程

```python
# app/services/analysis_service.py
async def analyze_image(self, file: UploadFile) -> SafetyReport:
    # 读取图片
    image_bytes = await file.read()
    
    # Base64编码
    image_b64 = base64.b64encode(image_bytes).decode()
    
    # 调用阿里云API
    messages = [
        HumanMessage(content=[
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_b64}"
                }
            },
            {"type": "text", "text": "请分析图片中的安全隐患"}
        ])
    ]
    
    result = await self.vlm.ainvoke(messages)
```

### OpenAI兼容性

阿里云DashScope提供OpenAI兼容接口，因此可以直接使用`langchain_openai.ChatOpenAI`：

```python
from langchain_openai import ChatOpenAI

vlm = ChatOpenAI(
    model_name="qwen3-vl-plus",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)
```

## 常见问题

**Q: 为什么不把Embedding和Reranker也换成API？**
A: Embedding和Reranker调用频率极高（每次检索都需要），使用API成本会急剧上升。自托管这两个模型只需要4GB GPU，成本可控。

**Q: 支持新加坡地域吗？**
A: 支持。修改`.env`中的`DASHSCOPE_BASE_URL`为：
```
DASHSCOPE_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
```

**Q: 可以使用其他模型吗？**
A: 可以。修改`.env`中的模型名称：
```
VLM_MODEL_NAME=qwen3-vl-flash  # 更快速的模型
LLM_MODEL_NAME=qwen3-max       # 标准版本
```

**Q: 图片大小有限制吗？**
A: 阿里云API建议图片<5MB，分辨率<4096px。代码中已设置50MB限制，但实际应控制在合理范围。

## 支持

- GitHub Issues: https://github.com/your-repo/issues
- 阿里云文档: https://help.aliyun.com/zh/model-studio/
- 技术讨论: [添加讨论群链接]
