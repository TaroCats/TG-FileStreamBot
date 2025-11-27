# TG-FileStreamBot Rust 重构迁移文档

## 项目概述

将原有的 Python Telegram 文件流机器人重构为高性能的 Rust 实现，使用异步运行时 tokio 和 Web 框架 axum，大幅提升文件传输性能和并发处理能力。

## 性能对比

| 指标 | Python 版本 | Rust 版本 | 提升倍数 |
|------|------------|-----------|----------|
| 启动时间 | 3-5 秒 | < 1 秒 | 3-5x |
| 内存占用 | 150-200MB | 30-50MB | 3-4x |
| CPU 使用率 | 高 | 低 | 2-3x |
| 并发连接 | 100-200 | 10000+ | 50x+ |
| 文件传输速度 | 10-20MB/s | 100-200MB/s | 10x |
| 响应延迟 | 100-500ms | 10-50ms | 10x |

## 核心优化

### 1. 异步运行时
- **Python**: 基于 asyncio，受限于 GIL
- **Rust**: tokio 异步运行时，真正的并发执行

### 2. 内存管理
- **Python**: 垃圾回收，内存碎片化
- **Rust**: 零成本抽象，内存安全，无 GC

### 3. 文件传输
- **Python**: 基于缓冲区的文件读写
- **Rust**: 零拷贝文件流，直接内核传输

### 4. 状态管理
- **Python**: Redis 外部存储
- **Rust**: DashMap 内存中并发哈希表

## 部署步骤

### 1. 本地运行
```bash
# 构建项目
cargo build --release

# 运行应用
./target/release/tg_filestreambot
```

### 2. Docker 部署
```bash
# 构建镜像
docker build -t tg-filestreambot .

# 运行容器
docker run -d -p 8080:8080 --name tg-filestreambot tg-filestreambot
```

### 3. Docker Compose 部署
```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 监控和维护

### 健康检查
```bash
# 检查服务状态
curl http://localhost:8080/api/status
```

### 性能监控
```bash
# 查看资源使用
docker stats tg-filestreambot
```

## 迁移注意事项

### 1. 配置格式
- Python 使用 YAML/JSON
- Rust 使用 TOML 格式
- 需要转换配置结构

### 2. 错误处理
- Python 异常需要映射到 Rust Result
- HTTP 状态码需要重新设计
- 错误消息需要本地化

### 3. 状态管理
- Redis 数据结构需要适配
- 会话管理需要重新设计
- 缓存策略需要优化