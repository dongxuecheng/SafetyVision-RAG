# 阿里云API版本 - 配置说明

本分支使用阿里云百炼DashScope API替代自托管的vLLM模型，降低部署成本和维护复杂度。

## 架构变更

### 使用阿里云API的模型
- **图像隐患识别（多模态）**: `qwen3-vl-plus` - 阿里云百炼多模态大模型
- **知识问答RAG（文本）**: `qwen3-max-preview` - 阿里云百炼文本大模型

### 仍然自托管的模型
- **Embedding模型**: BGE-M3 (通过vLLM部署)
- **Reranker模型**: BGE-Reranker-v2-M3 (通过vLLM部署)

## 配置步骤

### 1. 获取API Key

访问阿里云百炼控制台获取API Key：
https://help.aliyun.com/zh/model-studio/get-api-key

**注意**：北京地域和新加坡地域的API Key不同

### 2. 配置环境变量

复制示例配置文件：
```bash
cp .env.aliyun.example .env
```

编辑 `.env` 文件，填入你的API Key：
```bash
DASHSCOPE_API_KEY=sk-your-actual-api-key-here
```

### 3. 启动服务

只需启动Embedding、Reranker和Qdrant服务（无需启动聊天模型容器）：

```bash
# 启动必要的服务
docker compose up -d qdrant-server vllm-bge-m3 vllm-bge-reranker safetyvision-api
```

## API调用示例

### 图像隐患识别 (Base64编码)

当前实现会自动将上传的图片转换为base64格式传递给阿里云API：

```python
import base64
from openai import OpenAI

# 读取图片并编码
with open("construction_site.jpg", "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode()

# 调用API
client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

response = client.chat.completions.create(
    model="qwen3-vl-plus",
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}
            },
            {"type": "text", "text": "请分析图片中的安全隐患"}
        ]
    }]
)
```

### 知识问答RAG

```python
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

response = client.chat.completions.create(
    model="qwen3-max-preview",
    messages=[
        {"role": "system", "content": "你是安全专家"},
        {"role": "user", "content": "脚手架搭设规范有哪些要求？"}
    ]
)
```

## 成本估算

阿里云百炼按Token计费：

- **qwen3-vl-plus** (多模态):
  - 输入: ¥0.004/1K tokens
  - 输出: ¥0.012/1K tokens
  - 图片: 按分辨率计算额外tokens

- **qwen3-max-preview** (文本):
  - 输入: ¥0.02/1K tokens
  - 输出: ¥0.06/1K tokens

每次图像分析约消耗 3000-5000 tokens (¥0.02-0.05)
每次RAG问答约消耗 2000-4000 tokens (¥0.08-0.24)

## 优势

1. **降低部署成本**: 无需GPU服务器部署大模型
2. **简化运维**: 不需要管理模型文件和vLLM容器
3. **性能更强**: 阿里云最新版本模型能力更强
4. **按需付费**: 低频使用场景更经济

## 注意事项

1. **网络依赖**: 需要稳定的外网访问阿里云API
2. **API限流**: 注意并发请求限制
3. **数据隐私**: 图片会上传到阿里云服务器处理
4. **地域选择**: 
   - 国内用户使用北京地域: `https://dashscope.aliyuncs.com/compatible-mode/v1`
   - 海外用户使用新加坡地域: `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`

## 回退到自托管版本

如需切换回自托管vLLM版本：
```bash
git checkout main
```
