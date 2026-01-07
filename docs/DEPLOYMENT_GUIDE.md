# 双模式部署指南

SafetyVision-RAG 支持两种部署模式，可根据实际需求灵活切换。

## 🎯 部署模式对比

| 特性 | 本地完整部署 (Local) | 阿里云API混合部署 (Aliyun) |
|------|---------------------|---------------------------|
| **LLM/VLM** | 本地 vLLM (Qwen3-VL-4B) | 阿里云 DashScope API |
| **Embedding** | 本地 vLLM (BGE-M3) | 本地 vLLM (BGE-M3) |
| **Reranker** | 本地 vLLM (BGE-Reranker-v2-M3) | 本地 vLLM (BGE-Reranker-v2-M3) |
| **GPU需求** | ~105% (需要多卡或分批部署) | ~80% (单卡可能满足) |
| **成本** | 一次性硬件投资 | 按调用量付费 |
| **适用场景** | 数据敏感、高频调用 | 小规模测试、低频使用 |

## 📦 方式1: 本地完整部署

### 特点
- 所有模型本地部署，数据不出服务器
- 需要较多GPU资源 (~70% + 20% + 15%)
- 无API调用成本

### 部署步骤

1. **准备模型文件**
```bash
# 确保以下模型已下载到 /home/xcd/vllm/model/
# - Qwen3-VL-4B (多模态，同时提供图像和文本能力)
# - bge-m3 (嵌入模型)
# - bge-reranker-v2-m3 (重排序模型)
```

2. **配置环境变量**
```bash
cd /home/xcd/SafetyVision-RAG
cp .env.local.example .env

# 编辑 .env 确认配置（通常无需修改）
vim .env
```

3. **启动服务**
```bash
# 使用本地部署配置启动
docker compose -f docker-compose.local.yaml up -d

# 查看日志
docker compose -f docker-compose.local.yaml logs -f safetyvision-api
```

4. **验证服务**
```bash
# 检查所有服务健康状态
docker compose -f docker-compose.local.yaml ps

# 访问API文档
curl http://localhost:8080/docs
```

## ☁️ 方式2: 阿里云API混合部署

### 特点
- LLM/VLM使用阿里云API，按调用量付费
- Embedding和Reranker仍本地部署（保证检索性能）
- GPU需求较低 (~40% + 40%)

### 部署步骤

1. **获取阿里云API Key**
- 访问: https://dashscope.console.aliyun.com/apiKey
- 创建API Key并保存

2. **配置环境变量**
```bash
cd /home/xcd/SafetyVision-RAG
cp .env.aliyun.example .env

# 编辑 .env 填写API Key
vim .env
```

必填配置:
```bash
DEPLOYMENT_MODE=aliyun
DASHSCOPE_API_KEY=sk-your-actual-api-key-here  # 必填！
VLM_MODEL_NAME=qwen3-vl-plus
LLM_MODEL_NAME=qwen3-max-preview
```

3. **启动服务**
```bash
# 使用阿里云API配置启动
docker compose -f docker-compose.aliyun.yaml up -d

# 查看日志
docker compose -f docker-compose.aliyun.yaml logs -f safetyvision-api
```

4. **验证服务**
```bash
# 检查服务状态
docker compose -f docker-compose.aliyun.yaml ps

# 测试API调用
curl -X POST "http://localhost:8080/api/analysis/image" \
  -F "file=@test.jpg"
```

## 🔄 模式切换

### 从阿里云切换到本地
```bash
# 1. 停止阿里云模式
docker compose -f docker-compose.aliyun.yaml down

# 2. 更新.env配置
cp .env.local.example .env

# 3. 启动本地模式
docker compose -f docker-compose.local.yaml up -d
```

### 从本地切换到阿里云
```bash
# 1. 停止本地模式
docker compose -f docker-compose.local.yaml down

# 2. 更新.env配置
cp .env.aliyun.example .env
vim .env  # 填写DASHSCOPE_API_KEY

# 3. 启动阿里云模式
docker compose -f docker-compose.aliyun.yaml up -d
```

## 📝 日志管理

### 日志配置
两种模式都支持统一的日志管理，通过环境变量配置:

```bash
LOG_LEVEL=INFO              # 日志级别: DEBUG/INFO/WARNING/ERROR
LOG_FILE_PATH=logs/app.log  # 日志文件路径
LOG_ROTATION=100 MB         # 日志轮转大小
LOG_RETENTION=30 days       # 日志保留时间
```

### 查看日志

**容器日志**:
```bash
# 实时查看
docker logs -f safetyvision-api

# 查看最近100行
docker logs --tail 100 safetyvision-api
```

**文件日志**:
```bash
# 查看应用日志
tail -f logs/app.log

# 查看最近的错误
grep ERROR logs/app.log | tail -20
```

## 🛠️ 常见问题

### Q1: 本地模式GPU显存不足
**A**: 调整GPU内存分配比例
```yaml
# 编辑 docker-compose.local.yaml
command:
  - --gpu-memory-utilization
  - "0.5"  # 从0.7降低到0.5
```

### Q2: 阿里云API调用失败
**A**: 检查API Key和网络
```bash
# 1. 验证API Key
docker exec safetyvision-api env | grep DASHSCOPE

# 2. 测试网络连接
docker exec safetyvision-api curl -I https://dashscope.aliyuncs.com

# 3. 查看详细日志
docker logs safetyvision-api 2>&1 | grep -i error
```

### Q3: 日志文件过大
**A**: 调整轮转策略
```bash
# 在.env中修改
LOG_ROTATION=50 MB    # 减小轮转大小
LOG_RETENTION=7 days  # 缩短保留时间
```

### Q4: 如何查看当前部署模式
```bash
# 查看环境变量
docker exec safetyvision-api env | grep DEPLOYMENT_MODE

# 查看日志中的初始化信息
docker logs safetyvision-api 2>&1 | grep "Deployment mode"
```

## 📊 性能对比

| 指标 | 本地部署 | 阿里云API |
|------|---------|----------|
| 图像分析延迟 | ~2-3s | ~3-5s |
| 文本QA延迟 | ~1-2s | ~2-4s |
| 并发能力 | 受GPU限制 | 几乎无限 |
| 成本 (1000次调用) | ¥0 (已投资) | ~¥10-20 |

## 🚀 推荐配置

| 使用场景 | 推荐模式 |
|---------|---------|
| 开发测试 | 阿里云API (快速验证) |
| 小规模生产 (<100次/天) | 阿里云API (成本低) |
| 大规模生产 (>1000次/天) | 本地部署 (成本优势) |
| 数据安全要求高 | 本地部署 (数据不出服务器) |
| GPU资源有限 | 阿里云API (节省GPU) |

## 📚 更多文档

- [阿里云DashScope文档](https://help.aliyun.com/zh/model-studio/)
- [vLLM部署指南](https://docs.vllm.ai/)
- [项目README](./README.md)
