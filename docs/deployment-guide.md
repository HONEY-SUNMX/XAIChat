# 部署指南

> XAIChat 生产环境部署完整指南，包含 Docker、Nginx、系统服务配置

## 目录

- [部署架构](#部署架构)
- [环境准备](#环境准备)
- [部署方式](#部署方式)
  - [方式一：直接部署](#方式一直接部署)
  - [方式二：Docker 部署](#方式二docker-部署)
  - [方式三：Systemd 服务](#方式三systemd-服务)
- [Nginx 反向代理](#nginx-反向代理)
- [性能优化](#性能优化)
- [安全加固](#安全加固)
- [监控和日志](#监控和日志)

---

## 部署架构

### 推荐架构

```
┌─────────────┐
│   用户请求   │
└──────┬──────┘
       │
┌──────▼──────────┐
│  Nginx (80/443) │ ← SSL 终端 + 负载均衡
└──────┬──────────┘
       │
┌──────▼──────────┐
│  XAIChat API    │ ← FastAPI (8000)
│   (Uvicorn)     │
└──────┬──────────┘
       │
┌──────▼──────────┐
│  Static Files   │ ← 静态文件服务
│  (outputs/)     │
└─────────────────┘
```

### 最小配置要求

| 组件 | CPU | 内存 | 存储 | 说明 |
|------|-----|------|------|------|
| **最小配置** | 4 核 | 8GB | 20GB | 仅 Chat 模型 |
| **推荐配置** | 8 核 | 16GB | 50GB | 全功能运行 |
| **高性能配置** | 16 核 | 32GB | 100GB | 支持并发 |

---

## 环境准备

### 1. 系统要求

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.10 python3-pip git nginx supervisor

# CentOS/RHEL
sudo yum install -y python3 python3-pip git nginx supervisor
```

### 2. Python 环境

```bash
# 安装 Python 3.10+
python3 --version  # 确保 >= 3.10

# 安装虚拟环境
pip3 install virtualenv

# 创建虚拟环境
cd /opt
git clone https://github.com/yourname/XAIChat.git
cd XAIChat
virtualenv venv --python=python3.10
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 模型准备

```bash
# 下载 Chat 模型（必需）
mkdir -p models
cd models

# 方式 1：使用 HuggingFace CLI（推荐）
export HF_ENDPOINT=https://hf-mirror.com  # 国内镜像
huggingface-cli download unsloth/Qwen3-1.7B-GGUF \
    Qwen3-1.7B-Q4_K_M.gguf \
    --local-dir .

# 方式 2：wget 直接下载
wget https://hf-mirror.com/unsloth/Qwen3-1.7B-GGUF/resolve/main/Qwen3-1.7B-Q4_K_M.gguf

cd ..
```

### 4. 配置文件

```bash
# 复制配置模板
cp .env.template .env

# 编辑配置
vim .env
```

**生产环境配置示例** (`.env`):

```bash
# 应用配置
QWEN_DEBUG=false
QWEN_HOST=0.0.0.0
QWEN_PORT=8000

# 模型配置
QWEN_CHAT_MODEL_DIR=./models
QWEN_CHAT_MODEL_FILENAME=Qwen3-1.7B-Q4_K_M.gguf
QWEN_CHAT_CONTEXT_LENGTH=8192
QWEN_CHAT_N_THREADS=8  # 根据 CPU 核心数调整
QWEN_CHAT_N_GPU_LAYERS=0  # CPU only

# 性能优化
QWEN_STREAM_BATCH_SIZE=10
QWEN_LOG_PROGRESS_INTERVAL=50

# 超时设置（秒）
QWEN_CHAT_TIMEOUT=300
QWEN_VISION_TIMEOUT=300
QWEN_IMAGE_TIMEOUT=300

# HuggingFace 镜像（国内推荐）
QWEN_HF_ENDPOINT=https://hf-mirror.com

# 日志控制
QWEN_UVICORN_ACCESS_LOG=false
QWEN_DIFFUSERS_VERBOSITY=error
QWEN_TRANSFORMERS_VERBOSITY=error
```

---

## 部署方式

### 方式一：直接部署

#### 1. 使用 Uvicorn 直接运行

```bash
# 开发环境
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload

# 生产环境（单进程）
uvicorn server.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --log-level info \
    --access-log
```

> ⚠️ **注意**: 由于模型加载在内存中，不建议使用多 worker 模式

#### 2. 使用 Gunicorn + Uvicorn Worker

```bash
# 安装 gunicorn
pip install gunicorn

# 运行（单 worker）
gunicorn server.main:app \
    --workers 1 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 300 \
    --graceful-timeout 30 \
    --keep-alive 5 \
    --access-logfile /var/log/xaichat/access.log \
    --error-logfile /var/log/xaichat/error.log
```

---

### 方式二：Docker 部署

#### 1. 创建 Dockerfile

```dockerfile
# Dockerfile
FROM python:3.10-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建必要的目录
RUN mkdir -p models outputs uploads

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV CUDA_VISIBLE_DEVICES=""

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 2. 创建 docker-compose.yml

```yaml
version: '3.8'

services:
  xaichat:
    build: .
    container_name: xaichat-api
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - ./models:/app/models:ro  # 只读挂载模型
      - ./outputs:/app/outputs
      - ./uploads:/app/uploads
      - ./.env:/app/.env:ro
    environment:
      - QWEN_DEBUG=false
      - QWEN_HOST=0.0.0.0
      - QWEN_PORT=8000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    deploy:
      resources:
        limits:
          cpus: '8'
          memory: 16G
        reservations:
          cpus: '4'
          memory: 8G
```

#### 3. 构建和运行

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

---

### 方式三：Systemd 服务

#### 1. 创建服务文件

```bash
sudo vim /etc/systemd/system/xaichat.service
```

```ini
[Unit]
Description=XAIChat API Service
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/XAIChat
Environment="PATH=/opt/XAIChat/venv/bin"
Environment="CUDA_VISIBLE_DEVICES="

ExecStart=/opt/XAIChat/venv/bin/uvicorn server.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --log-level info

Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# 资源限制
LimitNOFILE=65536
MemoryLimit=16G
CPUQuota=800%

[Install]
WantedBy=multi-user.target
```

#### 2. 启动服务

```bash
# 重载配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start xaichat

# 设置开机自启
sudo systemctl enable xaichat

# 查看状态
sudo systemctl status xaichat

# 查看日志
sudo journalctl -u xaichat -f
```

---

## Nginx 反向代理

### 1. 基础配置

```nginx
# /etc/nginx/sites-available/xaichat
upstream xaichat_backend {
    server 127.0.0.1:8000;
    keepalive 64;
}

server {
    listen 80;
    server_name api.yourdomain.com;

    # 日志
    access_log /var/log/nginx/xaichat_access.log;
    error_log /var/log/nginx/xaichat_error.log;

    # 客户端请求体大小限制（图片上传）
    client_max_body_size 20M;

    # API 代理
    location /api/ {
        proxy_pass http://xaichat_backend;
        proxy_http_version 1.1;

        # 请求头
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时设置
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;

        # 连接复用
        proxy_set_header Connection "";
    }

    # SSE 流式响应特殊配置
    location /api/chat {
        proxy_pass http://xaichat_backend;
        proxy_http_version 1.1;

        # SSE 必需配置
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding on;

        # 超时设置
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;

        # 请求头
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # 静态文件服务（生成的图片）
    location /outputs/ {
        alias /opt/XAIChat/outputs/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    # 健康检查
    location /health {
        proxy_pass http://xaichat_backend;
        access_log off;
    }

    # API 文档
    location /docs {
        proxy_pass http://xaichat_backend;
    }
}
```

### 2. HTTPS 配置（Let's Encrypt）

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d api.yourdomain.com

# 自动续期
sudo certbot renew --dry-run
```

**HTTPS 配置示例**:

```nginx
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    # SSL 证书
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    # SSL 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # ... 其他配置同上
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

### 3. 启用配置

```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/xaichat /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重载 Nginx
sudo systemctl reload nginx
```

---

## 性能优化

### 1. 系统级优化

```bash
# 增加文件描述符限制
sudo vim /etc/security/limits.conf
```

```
* soft nofile 65536
* hard nofile 65536
```

```bash
# 优化 TCP 参数
sudo vim /etc/sysctl.conf
```

```
# 增加 TCP 连接队列
net.core.somaxconn = 1024
net.ipv4.tcp_max_syn_backlog = 2048

# 启用 TCP Fast Open
net.ipv4.tcp_fastopen = 3

# 调整 keepalive
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_probes = 3
net.ipv4.tcp_keepalive_intvl = 15
```

```bash
# 应用配置
sudo sysctl -p
```

### 2. CPU 亲和性

```bash
# 使用 taskset 绑定 CPU
taskset -c 0-7 python -m server.main
```

### 3. 内存优化

```python
# 在 core/config.py 中调整
chat_context_length: int = 4096  # 减小上下文长度
chat_n_threads: int = 4  # 限制线程数
```

---

## 安全加固

### 1. 防火墙配置

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable

# 限制内部端口
sudo ufw deny 8000/tcp  # 仅通过 Nginx 访问
```

### 2. 添加 API 认证

创建 `server/middleware/auth.py`:

```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

API_KEY = "your-secret-api-key"
api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key
```

在路由中使用:

```python
from server.middleware.auth import verify_api_key

@router.post("/chat")
async def chat(
    request: ChatRequest,
    api_key: str = Depends(verify_api_key)
):
    # ... 处理逻辑
```

### 3. 速率限制

```bash
# 安装 slowapi
pip install slowapi
```

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@router.post("/chat")
@limiter.limit("10/minute")  # 每分钟 10 次
async def chat(request: Request, ...):
    # ...
```

---

## 监控和日志

### 1. 日志配置

```python
# 在 server/main.py 中配置
import logging
from logging.handlers import RotatingFileHandler

# 创建日志目录
os.makedirs('/var/log/xaichat', exist_ok=True)

# 配置日志
handler = RotatingFileHandler(
    '/var/log/xaichat/app.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logging.getLogger().addHandler(handler)
```

### 2. 健康检查脚本

```bash
#!/bin/bash
# health_check.sh

API_URL="http://localhost:8000/health"
TIMEOUT=10

response=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT $API_URL)

if [ "$response" == "200" ]; then
    echo "✅ Service is healthy"
    exit 0
else
    echo "❌ Service is unhealthy (HTTP $response)"
    exit 1
fi
```

### 3. 添加到 Cron

```bash
# 每分钟检查一次
crontab -e
```

```
* * * * * /opt/XAIChat/scripts/health_check.sh >> /var/log/xaichat/health.log 2>&1
```

### 4. 系统监控

```bash
# 安装监控工具
sudo apt install htop iotop nethogs

# 实时监控
htop           # CPU/内存
iotop          # 磁盘 I/O
nethogs        # 网络流量
```

---

## 常见问题

### 1. 服务无法启动

```bash
# 检查端口占用
sudo lsof -i :8000

# 检查日志
sudo journalctl -u xaichat -n 50

# 检查权限
ls -la /opt/XAIChat
```

### 2. 模型加载失败

```bash
# 检查模型文件
ls -lh /opt/XAIChat/models/

# 检查内存
free -h

# 增加 swap（临时方案）
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 3. 性能问题

```bash
# 检查 CPU 使用
top -bn1 | grep "Cpu(s)"

# 检查内存
free -h

# 检查磁盘
df -h
iostat -x 1
```

---

Generated with ❤️ by Harei-chan (￣▽￣)ノ
