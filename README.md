

### 🔧 Render专属环境变量

| 变量名 | 默认值 | 说明 | 必需 |
|--------|--------|------|------|
| `RENDER_DEPLOYMENT` | `true` | 是否为Render部署环境 | 可选 |
| `USE_DOWNSTREAM_KEYS` | `true` | 是否使用下游密钥 | 可选 |
| `DOWNSTREAM_KEYS` | `""` | 下游密钥列表（逗号分隔） | 可选 |

### 📋 完整环境变量清单（包括原有配置）

#### API基础配置
- `API_ENDPOINT` - 上游API地址
- `AUTH_TOKEN` - 客户端认证密钥
- `BACKUP_TOKEN` - Z.ai备用访问令牌

#### 模型配置
- `PRIMARY_MODEL` - 主要模型（默认：GLM-4.5）
- `THINKING_MODEL` - 思考模型（默认：GLM-4.5-Thinking）
- `SEARCH_MODEL` - 搜索模型（默认：GLM-4.5-Search）
- `AIR_MODEL` - 轻量模型（默认：GLM-4.5-Air）

#### 服务器配置
- `LISTEN_PORT` - 监听端口（默认：8080）
- `DEBUG_LOGGING` - 调试日志（默认：true）

#### 功能配置
- `THINKING_PROCESSING` - 思考处理策略（默认：think）
- `ANONYMOUS_MODE` - 匿名模式（默认：true）
- `TOOL_SUPPORT` - 工具支持（默认：true）
- `SCAN_LIMIT` - 扫描限制（默认：200000）
- `SKIP_AUTH_TOKEN` - 跳过认证（默认：false）


### 1. 新增Render部署章节

## 🚀 Render 部署

### 一键部署到 Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/qw31415/z.ai2api_python)

### 手动部署步骤

1. Fork 本仓库到您的 GitHub 账户
2. 在 Render 控制台中创建新的 Web Service
3. 选择您的仓库
4. 配置环境变量（见下方配置说明）
5. 点击创建服务

### Render 环境变量配置

除了基础配置外，Render部署需要以下特殊配置：

| 变量名 | 建议值 | 说明 |
|--------|--------|------|
| `RENDER_DEPLOYMENT` | `true` | 启用Render部署模式 |
| `USE_DOWNSTREAM_KEYS` | `true` | 启用下游密钥支持 |
| `DOWNSTREAM_KEYS` | `key1,key2,key3` | 多个下游密钥，用逗号分隔 |
| `LISTEN_PORT` | `10000` | Render推荐的端口 |
```

### 2. 更新环境变量表格
在现有的环境变量配置表格中添加新的Render相关变量。

### 3. 添加Render特性说明
```markdown
### Render 部署特性

- ✅ **自动扩展** - 根据负载自动调整实例数量
- ✅ **HTTPS 支持** - 自动配置 SSL 证书
- ✅ **持久化存储** - 支持文件系统持久化
- ✅ **健康检查** - 自动监控服务状态
- ✅ **日志聚合** - 集中化日志管理
```

## 🎯 Render部署关键点

1. **端口配置**：Render建议使用`10000`端口
2. **下游密钥**：支持多个密钥轮换，提高可用性
3. **自动扩展**：利用Render的自动扩展功能应对高并发
4. **HTTPS**：自动配置，无需额外设置
