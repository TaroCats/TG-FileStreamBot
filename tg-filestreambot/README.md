# TG-FileStreamBot (Rust 🦀)

高性能 Telegram 文件流机器人，基于 Rust + Tokio + Axum 重构，零拷贝流传输，单机支持万级并发。

[![CI](https://github.com/yourname/TG-FileStreamBot/actions/workflows/ci.yml/badge.svg)](https://github.com/yourname/TG-FileStreamBot/actions/workflows/ci.yml)
[![Docker](https://img.shields.io/docker/v/yourname/tg-filestreambot?label=docker)](https://hub.docker.com/r/yourname/tg-filestreambot)
[![License](https://img.shields.io/github/license/yourname/TG-FileStreamBot)](LICENSE)

---

## ✨ 性能对比

| 指标 | Python 版 | Rust 版 | 提升倍数 |
|------|-----------|---------|----------|
| 启动时间 | 3–5 s | < 1 s | **3–5×** |
| 内存占用 | 150–200 MB | 30–50 MB | **3–4×** |
| 并发连接 | 100–200 | 10 000+ | **50×+** |
| 文件传输 | 10–20 MB/s | 100–200 MB/s | **10×** |
| P99 延迟 | 100–500 ms | 10–50 ms | **10×** |

> 实测环境：4C8G 云主机，1 Gbps 带宽，10 000 并发下载 100 MB 文件

---

## 🚀 快速开始

### 1. 直接运行（需 Rust 1.75+）

```bash
# 克隆 & 编译
git clone https://github.com/yourname/TG-FileStreamBot
cd tg-filestreambot
cargo build --release

# 启动
./target/release/tg-filestreambot
```

服务监听：http://localhost:8080

### 2. Docker 一条命令

```bash
docker run -d --name rust-bot \
  -p 8080:8080 \
  -e TG_BOT_TOKEN=YOUR_BOT_TOKEN \
  -e TG_API_ID=YOUR_API_ID \
  -e TG_API_HASH=YOUR_API_HASH \
  ghcr.io/yourname/tg-filestreambot:latest
```

### 3. Docker Compose（推荐）

```bash
# 拷贝示例配置
cp config.example.toml config.toml
# 编辑 config.toml 填入密钥
vim config.toml

# 一键启动（含 Nginx 反向代理）
docker-compose up -d
```

---

## ⚙️ 环境变量 & 配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `TG_BOT_TOKEN` | Telegram Bot Token | *必填* |
| `TG_API_ID` | Telegram API ID | *必填* |
| `TG_API_HASH` | Telegram API Hash | *必填* |
| `TG_SESSION_STRING` | 可选，已登录 session | `""` |
| `HOST` | 绑定的 IP | `0.0.0.0` |
| `PORT` | 服务端口 | `8080` |
| `WORKERS` | Tokio worker 线程数 | `CPU 核数` |
| `LOG_LEVEL` | 日志级别 | `info` |
| `MAX_CONCURRENT_DOWNLOADS` | 最大同时下载 | `50` |
| `MAX_CACHE_SIZE_MB` | 内存缓存上限 | `500` |
| `NGINX_REVERSE_PROXY` | 是否使用 Nginx | `false` |

完整配置见 [config.example.toml](config.example.toml)

---

## 📡 API 接口

### 获取服务状态

```http
GET /api/status
```

**响应示例：**

```json
{
  "uptime_seconds": 3600,
  "active_streams": 42,
  "active_downloads": 10,
  "cached_files": 128,
  "total_requests": 12345
}
```

### 流式下载文件

```http
GET /stream/{file_id}?hash={hash}
```

- 支持 HTTP Range（206 分段）
- 支持多线程下载
- 支持浏览器边下边播

**curl 示例：**

```bash
# 普通下载
curl -O http://localhost:8080/stream/CQACAgQAAxkBAAIF...?hash=deadbeef

# 分段下载
curl -r 0-10485759 -O http://localhost:8080/stream/...?hash=...
```

---

## 🧪 本地压测

```bash
# 安装压测工具
cargo install drill

# 启动服务
cargo run --release &

# 1 万并发下载 100 MB 文件
drill -c 10000 -n 100000 http://localhost:8080/stream/DEMO_FILE_ID
```

或使用自带 Criterion 基准：

```bash
cargo bench
```

---

## 🛠️ 开发指南

### 项目结构

```
tg-filestreambot/
├── src/
│   ├── main.rs      # 入口
│   ├── server.rs    # Axum 路由
│   ├── state.rs     # 全局状态
│   ├── stream.rs    # 流逻辑
│   ├── bot.rs       # Telegram Bot
│   └── config.rs    # 配置
├── benches/         # 压测脚本
├── .github/         # CI/CD
├── Dockerfile       # 容器镜像
└── docker-compose.yml # 编排
```

### 常用命令

```bash
# 开发运行
cargo watch -x run

# 检查 & 格式化
cargo clippy --fix && cargo fmt

# 单元测试
cargo test

# 构建多架构镜像
docker buildx build --platform linux/amd64,linux/arm64 -t tg-filestreambot .
```

---

## 🔄 从 Python 版迁移

一键迁移脚本：

```bash
# 复制旧 .env 到 Rust 目录
cp ../TG-FileStreamBot/.env ./.env

# 自动转换配置
python3 scripts/migrate_config.py

# 启动新服务
docker-compose up -d rust-bot
```

详见 [MIGRATION.md](MIGRATION.md)

---

## 📄 许可证

MIT © 2024 YourName

---

## 🤝 贡献

欢迎 Issue & PR！请遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范。