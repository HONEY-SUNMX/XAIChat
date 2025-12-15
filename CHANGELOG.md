# 更新日志 (Changelog)

所有重要的项目变更都将记录在此文件中。

本项目遵循 [语义化版本控制](https://semver.org/lang/zh-CN/)。

---

## [1.1.0] - 2025-12-15

### ✨ 新增功能

#### 🎨 统一多模态聊天 (Multimodal Chat)

全新的多模态聊天功能，在单个会话中无缝整合文本对话、图像理解和图片生成！

**后端新增：**
- 新增 `server/services/multimodal_service.py` - 多模态服务核心
  - 智能路由：自动检测用户意图（文本/图像/生成）
  - 统一会话管理：支持多模态消息历史记录
  - 关键词检测：自动识别图片生成请求（"画"、"生成图片"等）
  - 流式输出支持：实时传输各种类型的响应

- 新增 `server/routers/multimodal.py` - 多模态 API 路由
  - `POST /api/multimodal/chat` - 文本输入的多模态聊天
  - `POST /api/multimodal/chat-with-image` - 文本+图片输入
  - `GET /api/multimodal/conversation/{id}` - 获取会话历史
  - `DELETE /api/multimodal/conversation/{id}` - 清空会话

**前端新增：**
- 新增 `web/src/hooks/useMultimodalChat.ts` - React Hook
  - 统一管理多模态消息状态
  - 支持文本和图片输入
  - localStorage 持久化
  - 实时进度跟踪（图片生成时）

- 新增 `web/src/components/MultimodalPanel.tsx` - 多模态聊天面板
  - 统一的输入界面（文本 + 图片上传）
  - 优雅的紫粉渐变主题
  - 实时进度显示
  - 思考模式开关

- 新增 `web/src/components/MultimodalMessageBubble.tsx` - 多模态消息气泡
  - 支持多种消息类型：文本、图片分析、生成的图片
  - 可折叠的思考过程显示
  - 图片预览和元数据展示

**API 服务更新：**
- 扩展 `web/src/services/api.ts` 添加多模态 API 函数
  - `streamMultimodalChat()` - 流式多模态聊天
  - `streamMultimodalChatWithImage()` - 带图片的多模态聊天
  - `clearMultimodalConversation()` - 清空多模态会话
  - 新增 `MultimodalMessage` 和 `MultimodalStreamEvent` 类型定义

**UI 更新：**
- 更新 `web/src/App.tsx` - 添加多模态面板，默认展示
- 更新 `web/src/components/Sidebar.tsx` - 添加多模态入口（带 NEW 徽章）
- 应用标题更新为 "XAI Chat - 多模态 AI 助手"

### 🎯 核心特性

1. **智能意图识别**
   - 自动检测用户输入类型
   - 智能路由到相应服务
   - 无需手动切换模式

2. **统一会话体验**
   - 所有交互在同一会话中
   - 完整的上下文记忆
   - 支持混合模式交互

3. **优雅的用户界面**
   - 紫粉渐变主题设计
   - 实时流式输出
   - 图片生成进度条
   - 可折叠的思考过程

### 🏗️ 架构改进

- **遵循 SOLID 原则**
  - 开闭原则：通过组合现有服务实现新功能
  - 单一职责：MultimodalService 只负责协调
  - 依赖倒置：依赖抽象服务接口

- **保持 KISS 和 DRY**
  - 简洁的架构设计
  - 复用现有服务
  - 避免重复代码

### 📚 文档更新

- 更新 `README.md`：
  - 添加多模态聊天特性说明
  - 更新项目结构图
  - 新增多模态 API 端点文档
  - 添加使用示例和场景说明
  - 更新快速开始指南

- 新增 `CHANGELOG.md`：记录版本变更历史

### 🐛 Bug 修复

- 无

### 🔧 其他改进

- 更新 `server/main.py`：注册多模态路由
- 更新 `server/services/__init__.py`：导出 MultimodalService

---

## [1.0.0] - 2025-12-15

### 初始发布

- ✅ 基于 Qwen3 GGUF 的文本对话功能
- ✅ 基于 Qwen2-VL 的图像理解功能
- ✅ 基于 LCM 的快速图片生成功能
- ✅ React + TypeScript 前端界面
- ✅ FastAPI 后端服务
- ✅ 流式输出支持
- ✅ 思考模式
- ✅ CPU 友好设计

---

Generated with ❤️ by Harei-chan (￣▽￣)ノ
