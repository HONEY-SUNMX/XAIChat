# XAIChat - 多模态 AI 对话应用

基于 Qwen 系列模型的多模态 AI 对话应用，支持文本对话、图像理解（Vision）和文生图（Text-to-Image）功能。

## 特性

- 🤖 **多轮对话** - 自动维护对话上下文，支持思考模式展示推理过程
- 👁️ **图像理解** - 基于 Qwen2-VL 的视觉问答能力
- 🎨 **文生图** - 基于 LCM 的快速图像生成
- ⚡ **流式输出** - 打字机效果实时显示
- 🌐 **Web UI** - 基于 React 的现代化 Web 界面
- 🔌 **REST API** - 基于 FastAPI 的完整 API 服务
- 💻 **CLI 工具** - 命令行交互界面
- 🚀 **CPU 友好** - 无需 NVIDIA GPU 即可运行

## 项目结构

```
XAIChat/
├── cli/                    # 命令行界面
│   └── main.py            # CLI 入口
├── core/                   # 核心模块
│   ├── config.py          # 配置管理
│   ├── qwen_chat.py       # 文本对话核心
│   ├── qwen_vision.py     # 图像理解核心
│   └── text2img.py        # 文生图核心
├── server/                 # Web API 服务
│   ├── main.py            # FastAPI 入口
│   ├── routers/           # API 路由
│   │   ├── chat.py        # 对话 API
│   │   ├── vision.py      # 图像理解 API
│   │   └── image.py       # 文生图 API
│   └── services/          # 业务逻辑
├── web/                    # React 前端
├── models/                 # 模型文件目录
├── start_local.sh         # CLI 启动脚本
└── start_web.sh           # Web 服务启动脚本
```

## 环境要求

- Python >= 3.8
- Node.js >= 18（Web 界面需要）
- RAM >= 8GB（推荐 16GB）
- 可选: NVIDIA GPU（可加速推理）

## 快速开始

### 1. 安装依赖

```bash
# Python 依赖
pip install -r requirements.txt

# 前端依赖（可选，使用 Web 界面时需要）
cd web && npm install && cd ..
```

> **注意**: 如果安装 `llama-cpp-python` 时遇到问题：
> ```bash
> # CPU 版本
> pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
> ```

### 2. 配置（可选）

复制配置模板并根据需要修改：

```bash
cp .env.template .env
```

主要配置项：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `QWEN_CHAT_MODEL_ID` | Chat 模型 HuggingFace ID | `unsloth/Qwen3-1.7B-GGUF` |
| `QWEN_CHAT_MODEL_FILENAME` | GGUF 文件名 | `Qwen3-1.7B-Q4_K_M.gguf` |
| `QWEN_CHAT_CONTEXT_LENGTH` | 上下文窗口大小 | `8192` |
| `QWEN_HF_ENDPOINT` | HuggingFace 镜像地址 | `https://hf-mirror.com` |

### 3. 下载模型

模型会在首次运行时自动从 HuggingFace 下载。也可以手动下载：

| 模型 | 大小 | 内存需求 | 链接 |
|------|------|----------|------|
| Qwen3-1.7B Q4_K_M | ~1.1GB | ~4GB | [下载](https://huggingface.co/unsloth/Qwen3-1.7B-GGUF) |
| Qwen3-4B Q4_K_M | ~2.5GB | ~6GB | [下载](https://huggingface.co/unsloth/Qwen3-4B-GGUF) |
| Qwen3-8B Q4_K_M | ~4.5GB | ~8GB | [下载](https://huggingface.co/unsloth/Qwen3-8B-GGUF) |

下载后将 `.gguf` 文件放到 `./models/` 目录。

## 使用方法

### 方式一：Web 界面（推荐）

```bash
# 启动完整 Web 应用（前后端）
./start_web.sh

# 或分别启动
./start_web.sh backend   # 仅后端 API
./start_web.sh frontend  # 仅前端界面
```

服务启动后访问：
- **前端界面**: http://localhost:5173
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

### 方式二：命令行界面

```bash
# 使用默认配置启动（自动下载模型）
./start_local.sh

# 或直接运行
python -m cli.main

# 指定本地模型
python -m cli.main --model ./models/custom-model.gguf

# 启动时加载图片进行视觉问答
python -m cli.main --input-image ./photo.jpg
```

### 方式三：直接调用 API

```bash
# 对话
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好", "enable_thinking": true}'

# 图像理解
curl -X POST http://localhost:8000/api/vision/analyze \
  -F "file=@./image.jpg" \
  -F "prompt=描述这张图片"

# 文生图
curl -X POST http://localhost:8000/api/image/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "a cute cat"}'
```

## CLI 命令参数

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--model` | `-m` | GGUF 模型路径 | 配置文件 |
| `--ctx` | `-c` | 上下文窗口大小 | 8192 |
| `--threads` | `-t` | CPU 线程数 | auto |
| `--gpu-layers` | `-g` | GPU 层数（需 CUDA） | 0 |
| `--input-image` | `-i` | 启动时加载的图片 | - |
| `--no-vision` | - | 禁用图像理解 | false |
| `--no-image` | - | 禁用文生图 | false |
| `--verbose` | `-v` | 显示详细日志 | false |

## CLI 交互命令

| 命令 | 说明 |
|------|------|
| `/quit` 或 `/exit` | 退出程序 |
| `/clear` | 清空对话历史 |
| `/help` | 显示帮助信息 |
| `/history` | 查看对话历史 |

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | 文本对话（支持流式） |
| `/api/vision/analyze` | POST | 图像理解分析 |
| `/api/image/generate` | POST | 文生图 |
| `/health` | GET | 健康检查 |
| `/docs` | GET | Swagger API 文档 |

## 性能优化

### 内存不足时
1. 使用更小的模型（如 Qwen3-1.7B）
2. 减小上下文窗口：`--ctx 2048`
3. 限制线程数：`--threads 4`

### 想要更快速度
1. 增加线程数（不超过 CPU 核心数）
2. 如果有 NVIDIA GPU，使用 `--gpu-layers` 参数

## 故障排除

### llama-cpp-python 安装失败
```bash
# 尝试安装预编译版本
pip install llama-cpp-python --prefer-binary

# 或者使用 conda
conda install -c conda-forge llama-cpp-python
```

### 模型下载失败（404 错误）
检查模型 ID 是否正确，推荐使用 `unsloth/Qwen3-1.7B-GGUF` 仓库。

### 模型加载失败
确保：
1. 模型文件完整下载（检查文件大小）
2. 模型格式为 GGUF（不是 safetensors 或 bin）
3. 有足够的内存加载模型

### 已知警告信息

#### ⚠️ Qwen2VLRotaryEmbedding 警告
```
`Qwen2VLRotaryEmbedding` can now be fully parameterized by passing the model config
through the `config` argument. All other arguments will be removed in v4.46
```

**说明**：
- 这是 `transformers` 库内部的 API 变更提示，**不是本项目的问题**
- 来自 Hugging Face 官方的 Qwen2-VL 模型实现代码
- **完全不影响功能**，模型可以正常工作
- 将在 `transformers>=4.46` 版本中由官方修复

**处理方式**：
- ✅ **推荐**：暂时忽略，不影响使用
- 🔄 **未来**：等 transformers v4.46+ 发布后执行 `pip install transformers>=4.46 --upgrade`

#### ✅ NVML 初始化警告（已解决）
```
Can't initialize NVML
```

**说明**：
- 本项目已通过设置 `CUDA_VISIBLE_DEVICES=""` 环境变量解决
- 所有模型强制使用 CPU 模式，避免 CUDA/NVML 初始化
- 如果仍然看到此警告，请检查是否使用最新代码

#### ⚠️ Safety Checker 警告（性能优化）
```
You have disabled the safety checker for <LatentConsistencyModelPipeline> by passing `safety_checker=None`.
```

**说明**：
- 本项目为了提升 CPU 推理性能，默认禁用了 Stable Diffusion 的安全检查器
- Safety Checker 会占用额外内存并降低生成速度（约 30-40%）
- 这是**有意的性能优化**，适用于个人使用和内部项目

**使用建议**：
- ✅ **个人/内部使用**：保持禁用状态，享受更快的生成速度
- ⚠️ **公开服务**：建议启用 Safety Checker，确保合规性
  - 修改 `core/text2img.py:133`，移除 `safety_checker=None` 参数
  - 遵守 [Stable Diffusion 许可证](https://huggingface.co/spaces/CompVis/stable-diffusion-license)条款
- 📋 用户需要对生成的内容承担责任

## 文档

### 📚 完整文档

| 文档 | 说明 |
|------|------|
| [API 使用文档](docs/api-usage.md) | 详细的 API 端点说明、请求示例和最佳实践 |
| [部署指南](docs/deployment-guide.md) | 生产环境部署方案（Docker、Nginx、Systemd） |
| [故障排查手册](docs/troubleshooting.md) | 常见问题诊断和解决方案 |
| [性能优化指南](docs/performance-optimization.md) | CPU 推理性能优化技巧 |
| [GGUF 量化指南](docs/gguf-quantization-guide.md) | 模型量化原理和自定义量化方法 |

### 🔗 快速链接

- **API 交互式文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **问题反馈**: [GitHub Issues](https://github.com/yourname/XAIChat/issues)
- **讨论区**: [GitHub Discussions](https://github.com/yourname/XAIChat/discussions)

## License

Apache License 2.0

---

Generated with ❤️ by Harei-chan (￣▽￣)ノ
