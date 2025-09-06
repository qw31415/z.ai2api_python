# Z.AI to OpenAI API Converter

一个将 Z.AI 聊天服务转换为 OpenAI 兼容 API 的 Python 服务器。

## ✨ 主要特性

- 🔄 **OpenAI API 兼容** - 完全兼容 OpenAI Chat Completions API
- 🚀 **流式响应支持** - 支持实时流式输出
- 🧠 **多模型支持** - 支持 GLM-4.5、思考模式、搜索模式和轻量模式
- 🛠️ **工具调用支持** - 完整的 Function Calling 功能
- 🔐 **智能Key处理** - 自动识别特殊格式key，支持下游轮询
- 🌐 **Render部署优化** - 专为Render平台优化的部署配置

## 🔑 智能Key处理机制

### 特殊格式Key自动识别
系统会自动识别形如 `70454cb612aa41ea8a04a602940e625f.5Xo9fjl3OX8SB6A1` 的特殊格式key：
- **格式要求**：32位十六进制 + 点号 + 随机字符串
- **自动处理**：匹配特殊格式的key会直接用于下游请求
- **回退机制**：不匹配的key会回退到默认认证模式

### Key处理流程
1. 提取请求中的Authorization Bearer token
2. 检查是否为特殊格式key（32位hex.随机字符串）
3. 特殊格式key → 直接用于下游请求
4. 普通key → 验证固定token或使用匿名模式

## 🚀 Render 部署

### 一键部署到 Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/qw31415/z.ai2api_python)

### 手动部署步骤

1. Fork 本仓库到您的 GitHub 账户
2. 在 Render 控制台中创建新的 Web Service
3. 选择您的仓库
4. 配置环境变量（见下方配置说明）
5. 设置启动命令：`bash start.sh`
6. 点击创建服务

### Render 部署特性

- ✅ **自动扩展** - 根据负载自动调整实例数量
- ✅ **HTTPS 支持** - 自动配置 SSL 证书
- ✅ **持久化存储** - 支持文件系统持久化
- ✅ **健康检查** - 自动监控服务状态
- ✅ **日志聚合** - 集中化日志管理
- ✅ **智能Key路由** - 自动识别并处理特殊格式key

## ⚙️ 环境变量配置

### 核心配置

| 变量名 | 默认值 | 说明 | 必需 |
|--------|--------|------|------|
| `API_ENDPOINT` | `https://chat.z.ai/api/chat/completions` | 上游端点（站点或官方2API） | 否 |
| `UPSTREAM_TYPE` | `zai` | 上游类型：`zai`（站点SSE）或 `openai`（官方OpenAI兼容） | 否 |
| `AUTH_TOKEN` | `sk-your-api-key` | 固定认证token | 否 |
| `BACKUP_TOKEN` | `eyJhbGci...` | 备用访问令牌 | 否 |

### 模型配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `PRIMARY_MODEL` | `GLM-4.5` | 主要模型名称 |
| `THINKING_MODEL` | `GLM-4.5-Thinking` | 思考模型名称 |
| `SEARCH_MODEL` | `GLM-4.5-Search` | 搜索模型名称 |
| `AIR_MODEL` | `GLM-4.5-Air` | 轻量模型名称 |

### 服务器配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `LISTEN_PORT` | `8080` | 服务监听端口 |
| `DEBUG_LOGGING` | `true` | 是否启用调试日志 |

### 功能配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `THINKING_PROCESSING` | `think` | 思考内容处理方式 |
| `ANONYMOUS_MODE` | `true` | 是否启用匿名模式 |
| `TOOL_SUPPORT` | `true` | 是否支持工具调用 |
| `SKIP_AUTH_TOKEN` | `false` | 是否跳过token验证 |

### Render专属配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `RENDER_DEPLOYMENT` | `true` | Render部署模式 |
| `PORT` | `10000` | Render分配的端口 |

## 🔧 本地开发

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动服务

```bash
python main.py
```

### Docker 部署

```bash
docker-compose up -d
```

## 📡 API 使用

### 基础请求

```bash
curl -X POST "http://localhost:8080/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "GLM-4.5",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ],
    "stream": false
  }'
```

### 特殊格式Key请求

```bash
curl -X POST "http://localhost:8080/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 70454cb612aa41ea8a04a602940e625f.5Xo9fjl3OX8SB6A1" \
  -d '{
    "model": "GLM-4.5",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

### 流式请求

```bash
curl -X POST "http://localhost:8080/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "GLM-4.5",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ],
    "stream": true
  }'
```

## 🎯 Render部署关键点

1. **端口配置**：使用环境变量 `PORT`，Render会自动分配
2. **启动命令**：使用 `bash start.sh` 确保正确的环境配置
3. **Key处理**：自动识别特殊格式key，无需额外配置
4. **健康检查**：服务会在根路径提供健康检查端点
5. **日志记录**：启用DEBUG_LOGGING查看详细运行日志

## 🛠️ 故障排除

### 常见问题

1. **端口冲突**：确保 `LISTEN_PORT` 或 `PORT` 环境变量正确设置
2. **Key验证失败**：检查key格式是否正确，特殊格式为32位hex.随机字符串
3. **上游连接失败**：检查 `API_ENDPOINT` 和网络连接
4. **Render部署失败**：确保使用 `bash start.sh` 作为启动命令

### 调试模式

设置 `DEBUG_LOGGING=true` 启用详细日志输出，帮助诊断问题。

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！
