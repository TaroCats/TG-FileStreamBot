# 多阶段构建
FROM rust:1.75-alpine AS builder

# 安装构建依赖
RUN apk add --no-cache musl-dev openssl-dev pkgconfig

WORKDIR /app

# 复制依赖文件
COPY Cargo.toml Cargo.lock ./

# 创建虚拟项目以缓存依赖
RUN mkdir src && echo "fn main() {}" > src/main.rs
RUN cargo build --release && rm -rf src

# 复制源代码
COPY src ./src

# 构建应用
RUN cargo build --release

# 运行时镜像
FROM alpine:3.19

# 安装运行时依赖
RUN apk add --no-cache ca-certificates openssl

WORKDIR /app

# 复制二进制文件
COPY --from=builder /app/target/release/tg_filestreambot /app/

# 复制配置文件
COPY config.toml ./

# 创建非root用户
RUN addgroup -g 1000 appuser && adduser -u 1000 -G appuser -s /bin/sh -D appuser

# 设置权限
RUN chown -R appuser:appuser /app

USER appuser

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8080/api/status || exit 1

# 启动命令
CMD ["./tg_filestreambot"]