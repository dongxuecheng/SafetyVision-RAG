# 迁移指南：从自托管vLLM到阿里云API

## 🎯 迁移概览

本指南帮助你从自托管vLLM版本（main分支）迁移到阿里云API版本（feature/aliyun-api分支）。

## 📋 迁移前准备

### 1. 评估是否适合迁移

**适合使用阿里云API的场景**：
- ✅ 每日图像分析 < 50次
- ✅ 每日RAG问答 < 200次
- ✅ GPU资源不足（<12GB VRAM）
- ✅ 希望简化运维
- ✅ 对延迟不敏感（+1-2秒可接受）

**继续使用自托管的场景**：
- ❌ 高频调用（>500次/天）
- ❌ 对数据隐私有严格要求
- ❌ 网络环境不稳定
- ❌ 要求极低延迟（<2秒）

### 2. 获取阿里云API Key

访问：https://bailian.console.aliyun.com/
1. 注册/登录阿里云账号
2. 开通百炼服务
3. 创建API Key
4. 保存密钥（格式：sk-xxxxxxxxxx）

## 🚀 迁移步骤

### Step 1: 备份当前数据

```bash
cd /home/xcd/SafetyVision-RAG

# 备份向量数据库
tar -czf backup_qdrant_$(date +%Y%m%d).tar.gz data/qdrant/

# 备份上传文件
tar -czf backup_files_$(date +%Y%m%d).tar.gz file/

# 备份配置
cp .env .env.backup
```

### Step 2: 切换到阿里云API分支

```bash
# 停止当前服务
docker compose down

# 切换分支
git checkout feature/aliyun-api

# 查看变更
git log --oneline -3
```

### Step 3: 配置阿里云API

```bash
# 复制配置模板
cp .env.aliyun.example .env

# 编辑配置（必须填入API Key）
nano .env
```

配置示例：
```bash
DASHSCOPE_API_KEY=sk-your-actual-api-key-here
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
VLM_MODEL_NAME=qwen3-vl-plus
LLM_MODEL_NAME=qwen3-max-preview
```

### Step 4: 测试API连接

```bash
# 安装依赖（如果需要）
pip install openai python-dotenv

# 运行测试脚本
python test_aliyun_config.py
```

预期输出：
```
✅ 文本模型响应: 我是通义千问...
✅ 多模态模型响应: 你好！...
✅ 所有测试通过！阿里云API配置正确
```

### Step 5: 启动新服务

```bash
# 使用快速启动脚本（推荐）
./start_aliyun.sh

# 或手动启动
docker compose -f docker-compose.aliyun.yaml up -d

# 查看服务状态
docker compose -f docker-compose.aliyun.yaml ps
```

### Step 6: 验证功能

```bash
# 1. 检查API健康状态
curl http://localhost:8080/health

# 2. 测试图像分析
curl -X POST http://localhost:8080/api/analysis/image \
  -F "file=@test_image.jpg"

# 3. 访问Chainlit UI
# 浏览器打开: http://localhost:25810
```

## 📊 迁移对比

### 服务变化

| 组件 | 自托管版本 | 阿里云API版本 | 状态 |
|------|-----------|---------------|------|
| Qwen-VL | vllm容器 | 阿里云API | ✅ 已替换 |
| Qwen-LLM | vllm容器 | 阿里云API | ✅ 已替换 |
| BGE-M3 | vllm容器 | vllm容器 | ✅ 保持 |
| Reranker | vllm容器 | vllm容器 | ✅ 保持 |
| Qdrant | 本地容器 | 本地容器 | ✅ 保持 |

### 端口映射

| 服务 | 自托管版本 | 阿里云API版本 |
|------|-----------|---------------|
| API服务 | 8080 | 8080（不变）|
| Chainlit UI | 25810 | 25810（不变）|
| Qdrant | 6333 | 6333（不变）|
| VLM | 28000 | -（已移除）|
| Embedding | 28001 | 28001（不变）|
| Reranker | 28002 | 28002（不变）|

### 数据兼容性

✅ **完全兼容** - 向量数据库格式相同，无需重新索引

```bash
# 数据目录保持不变
data/qdrant/  # 向量数据库
file/         # 上传文件
```

## ⚠️ 常见问题

### Q1: 迁移后API请求失败

**症状**：
```
HTTPException: DashScope API Key not found
```

**解决**：
```bash
# 检查环境变量
docker exec safetyvision-api env | grep DASHSCOPE

# 重新加载配置
docker compose -f docker-compose.aliyun.yaml restart safetyvision-api
```

### Q2: 图像分析返回错误

**症状**：
```json
{"detail": "VLM 隐患提取失败: ..."}
```

**排查**：
```bash
# 1. 检查图片格式
file test_image.jpg

# 2. 检查图片大小（建议<5MB）
ls -lh test_image.jpg

# 3. 查看详细日志
docker logs safetyvision-api -f
```

### Q3: 响应速度变慢

**原因**：阿里云API有网络延迟

**优化**：
1. 使用离你更近的地域（北京/新加坡）
2. 考虑使用flash版本模型（更快但能力稍弱）
```bash
VLM_MODEL_NAME=qwen3-vl-flash
LLM_MODEL_NAME=qwen3-turbo
```

### Q4: 成本超出预期

**监控API使用**：
```bash
# 阿里云控制台 → 百炼 → 用量统计
# 查看每日调用次数和消耗金额
```

**成本控制**：
1. 设置阿里云预算告警
2. 限制单个用户请求频率
3. 考虑切换回自托管版本

## 🔄 回滚步骤

如果迁移后遇到问题，可随时回滚：

```bash
# 1. 停止阿里云API版本
docker compose -f docker-compose.aliyun.yaml down

# 2. 切换回主分支
git checkout main

# 3. 恢复配置
cp .env.backup .env

# 4. 启动自托管版本
docker compose up -d

# 5. 验证服务
curl http://localhost:8080/health
```

数据不会丢失，因为向量数据库和上传文件都在本地。

## 📈 性能监控

### 监控指标

```bash
# 1. API响应时间
docker logs safetyvision-api 2>&1 | grep "took"

# 2. 容器资源使用
docker stats vllm-bge-m3 vllm-bge-reranker

# 3. 阿里云API调用统计
# 访问: https://bailian.console.aliyun.com/#/console/usage
```

### 性能基准

| 操作 | 自托管 | 阿里云API | 差异 |
|------|--------|-----------|------|
| 图像分析 | 2-5秒 | 3-8秒 | +1-3秒 |
| RAG问答 | 1-3秒 | 2-5秒 | +1-2秒 |
| 向量检索 | 0.1秒 | 0.1秒 | 无变化 |

## 💰 成本估算

### 月度成本对比（中等使用量）

**自托管版本**：
- GPU服务器: ¥2000/月（RTX 3090）
- 电费: ¥200/月
- 总计: **¥2200/月**

**阿里云API版本**：
- GPU服务器: ¥600/月（GTX 1660 Ti，仅embedding和reranker）
- 电费: ¥60/月
- API调用: ¥800/月（每天100次图像+500次问答）
- 总计: **¥1460/月**

**节省**: ¥740/月（34%）

## 📝 迁移检查清单

- [ ] 备份向量数据库
- [ ] 备份上传文件
- [ ] 获取阿里云API Key
- [ ] 切换到feature/aliyun-api分支
- [ ] 配置.env文件
- [ ] 运行测试脚本验证API
- [ ] 启动Docker服务
- [ ] 测试图像分析功能
- [ ] 测试RAG问答功能
- [ ] 监控API调用量
- [ ] 设置成本告警

## 📞 获取帮助

- 查看详细文档: `USAGE_ALIYUN.md`
- 实现细节: `IMPLEMENTATION_SUMMARY.md`
- 测试API配置: `python test_aliyun_config.py`
- 快速启动: `./start_aliyun.sh`

---

**迁移时间**: 约15-30分钟
**难度级别**: ⭐⭐☆☆☆（简单）
**风险评估**: 低（可随时回滚）
