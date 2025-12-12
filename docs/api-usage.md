# API 使用文档

> XAIChat 完整 API 参考文档，包含详细示例和最佳实践

## 目录

- [快速开始](#快速开始)
- [认证](#认证)
- [文本对话 API](#文本对话-api)
- [图像理解 API](#图像理解-api)
- [文生图 API](#文生图-api)
- [错误处理](#错误处理)
- [最佳实践](#最佳实践)

---

## 快速开始

### 启动 API 服务

```bash
# 使用默认配置启动
python -m server.main

# 或使用启动脚本
./start_web.sh backend
```

默认服务地址：
- **API 基础地址**: http://localhost:8000
- **交互式文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

### 基础请求示例

```bash
# 健康检查
curl http://localhost:8000/health

# 查看 API 信息
curl http://localhost:8000/
```

---

## 认证

当前版本 **不需要认证**，所有端点都是公开的。

> ⚠️ **生产环境建议**：如果要部署到公网，请添加认证机制（JWT、API Key 等）。

---

## 文本对话 API

### POST /api/chat

与 AI 进行文本对话，支持思考模式和流式输出。

#### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `message` | string | ✅ | - | 用户输入的消息 |
| `enable_thinking` | boolean | ❌ | `true` | 是否启用思考模式 |
| `stream` | boolean | ❌ | `true` | 是否启用流式输出 |

#### 请求示例

**非流式请求**：
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "介绍一下量子计算",
    "enable_thinking": true,
    "stream": false
  }'
```

**流式请求**（SSE）：
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "message": "写一个快速排序算法",
    "enable_thinking": true,
    "stream": true
  }'
```

#### 响应格式

**非流式响应**：
```json
{
  "response": "量子计算是一种利用量子力学原理进行信息处理的计算方式...",
  "thinking": "用户询问量子计算，我需要解释基本概念..."
}
```

**流式响应（SSE）**：
```
data: {"type": "thinking", "content": "用户询问快速排序..."}

data: {"type": "thinking", "content": "我需要给出清晰的实现..."}

data: {"type": "response", "content": "快速"}

data: {"type": "response", "content": "排序"}

data: {"type": "done"}
```

#### Python 客户端示例

```python
import requests
import json

# 非流式调用
def chat_sync(message: str):
    response = requests.post(
        "http://localhost:8000/api/chat",
        json={
            "message": message,
            "enable_thinking": True,
            "stream": False
        }
    )
    return response.json()

# 流式调用
def chat_stream(message: str):
    response = requests.post(
        "http://localhost:8000/api/chat",
        json={
            "message": message,
            "enable_thinking": True,
            "stream": True
        },
        stream=True,
        headers={"Accept": "text/event-stream"}
    )

    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data = json.loads(line[6:])
                if data['type'] == 'thinking':
                    print(f"[思考] {data['content']}", end='', flush=True)
                elif data['type'] == 'response':
                    print(data['content'], end='', flush=True)
                elif data['type'] == 'done':
                    print("\n[完成]")
                    break

# 使用示例
result = chat_sync("你好")
print(result['response'])

# 流式输出
chat_stream("写一个冒泡排序")
```

#### JavaScript 客户端示例

```javascript
// 非流式调用
async function chatSync(message) {
  const response = await fetch('http://localhost:8000/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: message,
      enable_thinking: true,
      stream: false
    })
  });
  return await response.json();
}

// 流式调用（使用 EventSource）
function chatStream(message, onThinking, onResponse, onDone) {
  const eventSource = new EventSource(
    'http://localhost:8000/api/chat?' +
    new URLSearchParams({
      message: message,
      enable_thinking: 'true',
      stream: 'true'
    })
  );

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'thinking') {
      onThinking(data.content);
    } else if (data.type === 'response') {
      onResponse(data.content);
    } else if (data.type === 'done') {
      onDone();
      eventSource.close();
    }
  };

  eventSource.onerror = (error) => {
    console.error('SSE Error:', error);
    eventSource.close();
  };
}

// 使用示例
chatSync("你好").then(result => {
  console.log(result.response);
});

chatStream(
  "解释一下递归",
  (thinking) => console.log('[思考]', thinking),
  (chunk) => process.stdout.write(chunk),
  () => console.log('\n[完成]')
);
```

---

## 图像理解 API

### POST /api/vision/analyze

上传图片并提问，获取 AI 对图像的理解和分析。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | File | ✅ | 图片文件（支持 jpg/png/gif/webp） |
| `prompt` | string | ❌ | 对图片的提问（默认："描述这张图片"） |

#### 请求示例

```bash
# 使用 curl 上传图片
curl -X POST http://localhost:8000/api/vision/analyze \
  -F "file=@./photo.jpg" \
  -F "prompt=这张图片里有什么?"
```

#### 响应格式

```json
{
  "response": "图片中显示了一只橘色的猫咪坐在窗台上，背景是蓝天白云...",
  "image_size": [1920, 1080],
  "processing_time": 12.5
}
```

#### Python 客户端示例

```python
import requests

def analyze_image(image_path: str, prompt: str = "描述这张图片"):
    with open(image_path, 'rb') as f:
        files = {'file': f}
        data = {'prompt': prompt}
        response = requests.post(
            'http://localhost:8000/api/vision/analyze',
            files=files,
            data=data
        )
    return response.json()

# 使用示例
result = analyze_image('./photo.jpg', '图片中有几个人?')
print(result['response'])
```

#### JavaScript 客户端示例

```javascript
async function analyzeImage(file, prompt = "描述这张图片") {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('prompt', prompt);

  const response = await fetch('http://localhost:8000/api/vision/analyze', {
    method: 'POST',
    body: formData
  });

  return await response.json();
}

// 使用示例（浏览器环境）
const fileInput = document.querySelector('input[type="file"]');
fileInput.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  const result = await analyzeImage(file, '这是什么?');
  console.log(result.response);
});
```

---

## 文生图 API

### POST /api/image/generate

根据文本描述生成图片，支持流式进度更新。

#### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `prompt` | string | ✅ | - | 图片描述（英文效果更好） |
| `negative_prompt` | string | ❌ | `""` | 负面提示（要避免的内容） |
| `width` | integer | ❌ | `512` | 图片宽度（8 的倍数） |
| `height` | integer | ❌ | `512` | 图片高度（8 的倍数） |
| `num_steps` | integer | ❌ | `6` | 推理步数（4-8 推荐） |
| `seed` | integer | ❌ | `null` | 随机种子（用于复现） |
| `stream` | boolean | ❌ | `true` | 是否返回进度 |

#### 请求示例

**非流式请求**：
```bash
curl -X POST http://localhost:8000/api/image/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a cute cat sitting on a windowsill",
    "negative_prompt": "blurry, low quality",
    "width": 512,
    "height": 512,
    "stream": false
  }'
```

**流式请求（获取进度）**：
```bash
curl -X POST http://localhost:8000/api/image/generate \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "prompt": "beautiful sunset over mountains",
    "stream": true
  }'
```

#### 响应格式

**非流式响应**：
```json
{
  "image_url": "/outputs/gen_20231215_143022_12345.png",
  "filename": "gen_20231215_143022_12345.png",
  "seed": 12345
}
```

**流式响应（SSE）**：
```
data: {"type": "progress", "step": 1, "total": 6}

data: {"type": "progress", "step": 2, "total": 6}

...

data: {"type": "done", "image_url": "/outputs/gen_xxx.png", "filename": "gen_xxx.png", "seed": 12345}
```

#### Python 客户端示例

```python
import requests
import json
from PIL import Image
from io import BytesIO

# 非流式生成
def generate_image(prompt: str, **kwargs):
    response = requests.post(
        'http://localhost:8000/api/image/generate',
        json={
            'prompt': prompt,
            'stream': False,
            **kwargs
        }
    )
    result = response.json()

    # 下载生成的图片
    img_url = f"http://localhost:8000{result['image_url']}"
    img_response = requests.get(img_url)
    img = Image.open(BytesIO(img_response.content))

    return img, result['seed']

# 流式生成（带进度条）
def generate_image_with_progress(prompt: str, **kwargs):
    response = requests.post(
        'http://localhost:8000/api/image/generate',
        json={
            'prompt': prompt,
            'stream': True,
            **kwargs
        },
        stream=True,
        headers={'Accept': 'text/event-stream'}
    )

    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data = json.loads(line[6:])
                if data['type'] == 'progress':
                    progress = data['step'] / data['total'] * 100
                    print(f"进度: {progress:.0f}%", end='\r', flush=True)
                elif data['type'] == 'done':
                    print(f"\n生成完成！种子: {data['seed']}")
                    return data['image_url'], data['seed']

# 使用示例
img, seed = generate_image(
    "a peaceful lake with mountains",
    negative_prompt="people, cars",
    width=512,
    height=512
)
img.save(f'output_{seed}.png')
print(f'图片已保存，种子: {seed}')

# 带进度的生成
img_url, seed = generate_image_with_progress(
    "cyberpunk city at night"
)
```

---

## 错误处理

### 错误响应格式

所有错误都返回统一的 JSON 格式：

```json
{
  "error": "错误类型",
  "detail": "详细错误信息"
}
```

### 常见错误码

| HTTP 状态码 | 错误类型 | 说明 | 解决方案 |
|------------|---------|------|---------|
| 400 | Bad Request | 请求参数错误 | 检查参数格式和必填项 |
| 413 | Payload Too Large | 上传文件过大 | 压缩图片或降低分辨率 |
| 415 | Unsupported Media Type | 不支持的文件格式 | 使用支持的图片格式 |
| 500 | Internal Server Error | 服务器内部错误 | 查看服务器日志 |
| 503 | Service Unavailable | 模型未加载 | 等待模型加载完成 |

### 错误处理示例

```python
import requests

def safe_api_call(url, **kwargs):
    try:
        response = requests.post(url, **kwargs)
        response.raise_for_status()  # 抛出 HTTP 错误
        return response.json()
    except requests.exceptions.HTTPError as e:
        error_data = e.response.json()
        print(f"API 错误: {error_data['error']}")
        print(f"详情: {error_data.get('detail', '无')}")
        return None
    except requests.exceptions.ConnectionError:
        print("连接错误: 无法连接到服务器")
        return None
    except requests.exceptions.Timeout:
        print("超时错误: 请求超时")
        return None

# 使用示例
result = safe_api_call(
    'http://localhost:8000/api/chat',
    json={'message': '你好'},
    timeout=30
)
```

---

## 最佳实践

### 1. 超时设置

不同 API 的推荐超时时间：

```python
TIMEOUTS = {
    'chat': 120,      # 对话: 2 分钟
    'vision': 180,    # 图像理解: 3 分钟
    'image': 300,     # 文生图: 5 分钟
}

response = requests.post(
    url,
    json=data,
    timeout=TIMEOUTS['chat']
)
```

### 2. 重试策略

```python
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def create_session_with_retries():
    session = requests.Session()

    retry_strategy = Retry(
        total=3,                    # 最多重试 3 次
        backoff_factor=1,           # 指数退避
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"]
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session

# 使用示例
session = create_session_with_retries()
response = session.post(url, json=data)
```

### 3. 连接池复用

```python
# 复用同一个 Session 对象
session = requests.Session()

# 多次请求复用连接
for i in range(10):
    response = session.post(
        'http://localhost:8000/api/chat',
        json={'message': f'问题 {i}'}
    )
```

### 4. 异步请求（提升并发）

```python
import asyncio
import aiohttp

async def async_chat(session, message):
    async with session.post(
        'http://localhost:8000/api/chat',
        json={'message': message}
    ) as response:
        return await response.json()

async def main():
    async with aiohttp.ClientSession() as session:
        tasks = [
            async_chat(session, f'问题 {i}')
            for i in range(5)
        ]
        results = await asyncio.gather(*tasks)
        return results

# 运行
results = asyncio.run(main())
```

### 5. 图片优化建议

```python
from PIL import Image

def optimize_image_for_vision(image_path, max_size=1280):
    """优化图片以提升处理速度"""
    img = Image.open(image_path)

    # 转换为 RGB
    if img.mode != 'RGB':
        img = img.convert('RGB')

    # 缩小过大的图片
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

    # 保存为临时文件
    temp_path = 'temp_optimized.jpg'
    img.save(temp_path, 'JPEG', quality=85)

    return temp_path
```

### 6. 流式响应处理模板

```python
def handle_sse_stream(url, data):
    """通用的 SSE 流式响应处理"""
    response = requests.post(
        url,
        json=data,
        stream=True,
        headers={'Accept': 'text/event-stream'}
    )

    buffer = ""
    for chunk in response.iter_content(chunk_size=1, decode_unicode=True):
        buffer += chunk
        if buffer.endswith('\n\n'):
            lines = buffer.strip().split('\n')
            for line in lines:
                if line.startswith('data: '):
                    yield json.loads(line[6:])
            buffer = ""

# 使用示例
for event in handle_sse_stream(
    'http://localhost:8000/api/chat',
    {'message': '你好', 'stream': True}
):
    print(event)
```

---

## 参考资源

- **API 交互式文档**: http://localhost:8000/docs
- **源码仓库**: [GitHub](https://github.com/yourname/XAIChat)
- **问题反馈**: [Issues](https://github.com/yourname/XAIChat/issues)

---

Generated with ❤️ by Harei-chan (￣▽￣)ノ
