# 故障排查手册

> XAIChat 常见问题诊断和解决方案完整手册

## 目录

- [快速诊断](#快速诊断)
- [安装问题](#安装问题)
- [模型问题](#模型问题)
- [运行时问题](#运行时问题)
- [性能问题](#性能问题)
- [API 问题](#api-问题)
- [网络问题](#网络问题)
- [已知警告](#已知警告)

---

## 快速诊断

### 问题自检清单

```bash
# 1. 检查 Python 版本
python3 --version  # 应该 >= 3.10

# 2. 检查依赖安装
pip list | grep -E "llama-cpp-python|transformers|diffusers|fastapi"

# 3. 检查模型文件
ls -lh models/*.gguf

# 4. 检查端口占用
lsof -i :8000

# 5. 检查系统资源
free -h  # 内存
df -h    # 磁盘
top      # CPU

# 6. 检查服务状态
curl http://localhost:8000/health
```

### 日志位置

| 组件 | 日志位置 |
|------|---------|
| API 服务 | `journalctl -u xaichat -f` |
| Nginx | `/var/log/nginx/xaichat_*.log` |
| Docker | `docker-compose logs -f` |
| 应用日志 | `/var/log/xaichat/app.log` |

---

## 安装问题

### 问题 1: llama-cpp-python 安装失败

**症状**:
```
error: command 'gcc' failed with exit status 1
```

**原因**: 缺少编译工具链

**解决方案**:

```bash
# Ubuntu/Debian
sudo apt install build-essential cmake

# CentOS/RHEL
sudo yum groupinstall "Development Tools"
sudo yum install cmake

# 或使用预编译版本
pip install llama-cpp-python --prefer-binary

# 或使用 CPU 专用版本
pip install llama-cpp-python \
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
```

---

### 问题 2: transformers/torch 安装超时

**症状**:
```
ReadTimeoutError: HTTPSConnectionPool(host='pypi.org', port=443)
```

**原因**: 网络问题或包太大

**解决方案**:

```bash
# 使用国内镜像
pip install -r requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 增加超时时间
pip install transformers torch --timeout 300

# 分步安装大包
pip install torch --no-deps
pip install transformers --no-deps
pip install -r requirements.txt
```

---

### 问题 3: 依赖版本冲突

**症状**:
```
ERROR: pip's dependency resolver does not currently take into account...
```

**解决方案**:

```bash
# 清理缓存
pip cache purge

# 使用虚拟环境重新安装
python -m venv venv_clean
source venv_clean/bin/activate
pip install -r requirements.txt

# 如果仍然失败，手动调整版本
pip install transformers==4.40.0  # 替换为兼容版本
```

---

## 模型问题

### 问题 4: 模型下载失败（404 错误）

**症状**:
```
RuntimeError: Failed to download chat model: 404 Client Error
```

**原因**: 模型 ID 错误或文件不存在

**解决方案**:

```bash
# 1. 检查模型 ID
# 推荐使用 unsloth/Qwen3-1.7B-GGUF

# 2. 使用国内镜像
export HF_ENDPOINT=https://hf-mirror.com

# 3. 手动下载模型
huggingface-cli download unsloth/Qwen3-1.7B-GGUF \
    Qwen3-1.7B-Q4_K_M.gguf \
    --local-dir ./models

# 4. 或使用 wget
wget https://hf-mirror.com/unsloth/Qwen3-1.7B-GGUF/resolve/main/Qwen3-1.7B-Q4_K_M.gguf \
    -O models/Qwen3-1.7B-Q4_K_M.gguf
```

---

### 问题 5: 模型加载失败

**症状**:
```
Failed to load model: unable to load model
OSError: [Errno 12] Cannot allocate memory
```

**原因**: 内存不足或模型文件损坏

**诊断步骤**:

```bash
# 1. 检查模型文件完整性
ls -lh models/Qwen3-1.7B-Q4_K_M.gguf
# 应该约 1.0-1.1GB

# 2. 检查文件是否损坏
file models/Qwen3-1.7B-Q4_K_M.gguf
# 应该显示: data

# 3. 检查可用内存
free -h
# 至少需要 4GB 可用内存
```

**解决方案**:

```bash
# 方案 1: 增加 swap（临时）
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 方案 2: 使用更小的模型
# 下载 Q2_K 或 Q3_K_M 版本

# 方案 3: 减小上下文长度
# 编辑 .env
QWEN_CHAT_CONTEXT_LENGTH=2048

# 方案 4: 重新下载模型（可能损坏）
rm models/Qwen3-1.7B-Q4_K_M.gguf
huggingface-cli download ... # 重新下载
```

---

### 问题 6: 模型格式错误

**症状**:
```
ValueError: Invalid magic number in GGUF file
```

**原因**: 下载的不是 GGUF 格式

**解决方案**:

```bash
# 确保下载 GGUF 格式
# 文件名应该以 .gguf 结尾

# 检查文件类型
file models/your-model.gguf

# 如果是 safetensors 或其他格式，需要转换
# 参考 docs/gguf-quantization-guide.md
```

---

## 运行时问题

### 问题 7: 端口被占用

**症状**:
```
OSError: [Errno 98] Address already in use
```

**诊断**:

```bash
# 查找占用端口的进程
lsof -i :8000
netstat -tlnp | grep 8000
```

**解决方案**:

```bash
# 方案 1: 杀死占用进程
kill -9 <PID>

# 方案 2: 使用其他端口
# 编辑 .env
QWEN_PORT=8001

# 方案 3: 停止已有服务
sudo systemctl stop xaichat
# 或
docker-compose down
```

---

### 问题 8: 服务启动后立即退出

**诊断步骤**:

```bash
# 1. 查看详细错误
python -m server.main

# 2. 检查配置文件
cat .env

# 3. 检查权限
ls -la models/
ls -la uploads/
ls -la outputs/

# 4. 查看系统日志
journalctl -u xaichat -n 50
```

**常见原因和解决方案**:

```bash
# 原因 1: 配置文件缺失或格式错误
cp .env.template .env
vim .env  # 检查格式

# 原因 2: 模型文件路径错误
ls models/  # 确认文件存在
# 修改 .env 中的路径

# 原因 3: 目录权限问题
chmod 755 models outputs uploads
chown -R $USER:$USER .

# 原因 4: 依赖缺失
pip install -r requirements.txt
```

---

### 问题 9: 请求超时

**症状**:
```
504 Gateway Timeout
TimeoutError: Request timeout
```

**原因**: 推理时间过长

**解决方案**:

```bash
# 1. 增加超时设置
# 在 .env 中
QWEN_CHAT_TIMEOUT=600  # 10 分钟
QWEN_VISION_TIMEOUT=600
QWEN_IMAGE_TIMEOUT=600

# 2. 在 Nginx 中增加超时
# /etc/nginx/sites-available/xaichat
proxy_read_timeout 600s;
proxy_send_timeout 600s;

# 3. 客户端增加超时
response = requests.post(url, json=data, timeout=600)
```

---

## 性能问题

### 问题 10: 响应速度慢

**诊断**:

```bash
# 1. 检查 CPU 使用
top -bn1 | grep "Cpu(s)"

# 2. 检查内存使用
free -h

# 3. 检查磁盘 I/O
iostat -x 1

# 4. 检查进程资源
ps aux | grep python
```

**优化方案**:

```bash
# 1. 增加线程数（不超过 CPU 核心数）
# .env
QWEN_CHAT_N_THREADS=8

# 2. 减小上下文长度
QWEN_CHAT_CONTEXT_LENGTH=4096

# 3. 减小 max_tokens
QWEN_CHAT_MAX_TOKENS=2048

# 4. 使用更小的模型
# Q4_K_M -> Q3_K_M

# 5. 关闭思考模式
# API 请求中设置
{"enable_thinking": false}
```

---

### 问题 11: 内存占用过高

**症状**:
```
MemoryError: Cannot allocate memory
```

**诊断**:

```bash
# 监控内存使用
watch -n 1 free -h

# 检查进程内存
ps aux --sort=-%mem | head
```

**解决方案**:

```bash
# 1. 减小上下文长度
QWEN_CHAT_CONTEXT_LENGTH=2048

# 2. 使用更小的量化模型
# Q4_K_M (1.0GB) -> Q3_K_M (0.7GB) -> Q2_K (0.5GB)

# 3. 不同时加载多个模型
# 禁用不需要的功能
# 在启动时使用 --no-vision 或 --no-image

# 4. 增加 swap
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

### 问题 12: CPU 使用率 100%

**原因**: 线程数设置过高

**解决方案**:

```bash
# 调整线程数为 CPU 核心数的 80-90%
# 例如 8 核 CPU
QWEN_CHAT_N_THREADS=6

# 限制进程 CPU 使用
# 在 systemd 服务中
CPUQuota=600%  # 6 个核心

# 或使用 taskset
taskset -c 0-5 python -m server.main
```

---

## API 问题

### 问题 13: CORS 错误

**症状**:
```
Access to fetch at 'http://localhost:8000/api/chat' from origin 'http://localhost:5173' has been blocked by CORS policy
```

**解决方案**:

```python
# 在 .env 中添加前端地址
QWEN_CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000", "https://yourdomain.com"]

# 或编辑 core/config.py
cors_origins: List[str] = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://yourdomain.com",
]
```

---

### 问题 14: 文件上传失败

**症状**:
```
413 Request Entity Too Large
422 Unprocessable Entity
```

**解决方案**:

```bash
# 1. 检查文件大小限制
# .env
QWEN_MAX_UPLOAD_SIZE=10485760  # 10MB

# 2. 在 Nginx 中增加限制
client_max_body_size 20M;

# 3. 检查文件格式
# 只支持: jpg, jpeg, png, gif, bmp, webp
```

---

### 问题 15: 流式响应中断

**症状**: SSE 连接突然断开

**解决方案**:

```nginx
# Nginx 配置
location /api/chat {
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 3600s;
    chunked_transfer_encoding on;
}
```

---

## 网络问题

### 问题 16: HuggingFace 连接失败

**症状**:
```
requests.exceptions.ConnectionError: Cannot connect to huggingface.co
```

**解决方案**:

```bash
# 使用国内镜像
export HF_ENDPOINT=https://hf-mirror.com

# 或在 .env 中设置
QWEN_HF_ENDPOINT=https://hf-mirror.com

# 测试连接
curl -I https://hf-mirror.com
```

---

### 问题 17: 无法访问 API

**诊断步骤**:

```bash
# 1. 检查服务是否运行
systemctl status xaichat
# 或
docker ps

# 2. 检查端口监听
netstat -tlnp | grep 8000

# 3. 检查防火墙
sudo ufw status
sudo iptables -L

# 4. 测试本地连接
curl http://localhost:8000/health

# 5. 测试外网连接
curl http://your-server-ip:8000/health
```

**解决方案**:

```bash
# 1. 启动服务
systemctl start xaichat

# 2. 开放端口
sudo ufw allow 8000/tcp

# 3. 检查绑定地址
# .env
QWEN_HOST=0.0.0.0  # 不要用 127.0.0.1
```

---

## 已知警告

### 警告 1: Qwen2VLRotaryEmbedding ⚠️

```
`Qwen2VLRotaryEmbedding` can now be fully parameterized by passing the model config
through the `config` argument. All other arguments will be removed in v4.46
```

**说明**:
- 这是 `transformers` 库内部的 API 变更提示
- **不是本项目的问题**
- **完全不影响功能**

**处理方式**:
- ✅ 暂时忽略，不影响使用
- 🔄 等 transformers v4.46+ 发布后升级

---

### 警告 2: NVML 初始化 ✅ (已解决)

```
Can't initialize NVML
```

**说明**:
- 本项目已通过设置 `CUDA_VISIBLE_DEVICES=""` 环境变量解决
- 所有模型强制使用 CPU 模式

**如果仍然出现**:
- 确保使用最新代码
- 检查是否有其他地方导入了 torch

---

### 警告 3: Safety Checker ⚠️

```
You have disabled the safety checker for <LatentConsistencyModelPipeline> by passing `safety_checker=None`.
```

**说明**:
- 这是有意的**性能优化**
- 禁用 Safety Checker 可提升 30-40% 生成速度

**使用建议**:
- ✅ 个人/内部使用：保持禁用
- ⚠️ 公开服务：建议启用（修改 `core/text2img.py:133`）

---

## 诊断工具脚本

### 一键诊断脚本

```bash
#!/bin/bash
# diagnose.sh

echo "====== XAIChat 系统诊断 ======"
echo

echo "1. Python 版本:"
python3 --version
echo

echo "2. 关键依赖:"
pip list | grep -E "llama-cpp-python|transformers|diffusers|fastapi"
echo

echo "3. 模型文件:"
ls -lh models/*.gguf 2>/dev/null || echo "未找到模型文件"
echo

echo "4. 系统资源:"
echo "内存:"
free -h
echo "磁盘:"
df -h /
echo

echo "5. 端口状态:"
netstat -tlnp 2>/dev/null | grep 8000 || lsof -i :8000
echo

echo "6. 服务状态:"
systemctl status xaichat 2>/dev/null || echo "服务未安装"
echo

echo "7. API 健康检查:"
curl -s http://localhost:8000/health || echo "API 未响应"
echo

echo "====== 诊断完成 ======"
```

运行:
```bash
chmod +x diagnose.sh
./diagnose.sh
```

---

## 获取帮助

如果以上方法都无法解决问题：

1. **查看日志**: 收集完整的错误日志
2. **GitHub Issues**: https://github.com/yourname/XAIChat/issues
3. **讨论区**: https://github.com/yourname/XAIChat/discussions
4. **提供信息**:
   - 操作系统和版本
   - Python 版本
   - 完整错误信息
   - 配置文件内容（隐藏敏感信息）

---

Generated with ❤️ by Harei-chan (￣▽￣)ノ
