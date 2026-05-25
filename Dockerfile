FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt ./

# 使用 slim 镜像自带 glibc，可以直接下载预编译的 wheel 包（如 TgCrypto, aiohttp）
# 无需像 Alpine 那样安装庞大的 build-base 编译工具链
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python3", "-m", "WebStreamer"]
