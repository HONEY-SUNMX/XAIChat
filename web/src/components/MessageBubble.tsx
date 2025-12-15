import { useState, useEffect, useRef } from 'react'
import { User, Bot, Loader2, ChevronDown, ChevronRight, Brain } from 'lucide-react'
import { ChatMessage } from '../services/api'

interface MessageBubbleProps {
  message: ChatMessage
  messageIndex?: number  // 用于稳定的key
}

export default function MessageBubble({ message, messageIndex }: MessageBubbleProps) {
  // 思考过程默认折叠状态（初始值为false = 折叠）
  const [isThinkingExpanded, setIsThinkingExpanded] = useState(false)
  const hadThinkingRef = useRef(false)
  
  // 监听thinking属性的变化，当thinking从无到有时，强制重置为折叠状态
  useEffect(() => {
    if (message.thinking && !hadThinkingRef.current) {
      // thinking首次出现，确保折叠
      setIsThinkingExpanded(false)
      hadThinkingRef.current = true
    } else if (!message.thinking) {
      // 重置标记
      hadThinkingRef.current = false
    }
  }, [message.thinking])

  const isUser = message.role === 'user'
  const isThinking = message.role === 'thinking'
  const isAssistant = message.role === 'assistant'

  // 思考中状态（单独的 thinking 消息，流式显示中）- 默认折叠，美化设计
  if (isThinking) {
    return (
      <div className="flex gap-3 items-start animate-fade-in-up">
        {/* Avatar - 渐变背景 + 旋转动画 */}
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-purple-400 to-pink-400 flex items-center justify-center shadow-sm">
          <Loader2 className="w-4 h-4 text-white animate-spin" />
        </div>

        {/* Thinking Content - 可折叠，美化样式 */}
        <div className="max-w-[70%]">
          <button
            onClick={() => setIsThinkingExpanded(!isThinkingExpanded)}
            className="flex items-center gap-2 px-3 py-2 bg-gradient-to-r from-purple-50 to-pink-50 hover:from-purple-100 hover:to-pink-100 border border-purple-200 rounded-lg transition-all shadow-sm"
          >
            {isThinkingExpanded ? (
              <ChevronDown className="w-3.5 h-3.5 text-purple-600" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5 text-purple-600" />
            )}
            <Brain className="w-4 h-4 text-purple-600 animate-pulse" />
            <span className="text-xs font-medium text-purple-700">思考中</span>
            {/* 动画点点点 */}
            <span className="flex gap-0.5 ml-1">
              <span className="w-1 h-1 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
              <span className="w-1 h-1 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
              <span className="w-1 h-1 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
            </span>
          </button>
          {isThinkingExpanded && (
            <div className="mt-2 px-4 py-3 bg-gradient-to-br from-purple-50 to-pink-50 border border-purple-200 rounded-lg shadow-inner">
              <p className="text-xs text-gray-700 whitespace-pre-wrap break-words leading-relaxed">
                {message.content}
              </p>
            </div>
          )}
        </div>
      </div>
    )
  }

  // 用户消息
  if (isUser) {
    return (
      <div className="flex gap-3 items-start animate-fade-in-up flex-row-reverse">
        {/* Avatar */}
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary-500 flex items-center justify-center">
          <User className="w-5 h-5 text-white" />
        </div>

        {/* Message Content */}
        <div className="max-w-[70%] rounded-2xl px-4 py-3 bg-primary-500 text-white">
          <div className="whitespace-pre-wrap break-words">
            {message.content}
          </div>
        </div>
      </div>
    )
  }

  // Assistant 消息（可能带有可折叠的思考内容）
  return (
    <div className="flex gap-3 items-start animate-fade-in-up">
      {/* Avatar */}
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center">
        <Bot className="w-5 h-5 text-white" />
      </div>

      {/* Message Content with Collapsible Thinking */}
      <div className="max-w-[70%]">
        {/* 可折叠的思考内容（只在有 thinking 内容时显示） - 美化样式 */}
        {message.thinking && (
          <div className="mb-2">
            <button
              onClick={() => setIsThinkingExpanded(!isThinkingExpanded)}
              className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-purple-50 to-pink-50 hover:from-purple-100 hover:to-pink-100 border border-purple-200 rounded-lg transition-all shadow-sm"
            >
              {isThinkingExpanded ? (
                <ChevronDown className="w-3.5 h-3.5 text-purple-600" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 text-purple-600" />
              )}
              <Brain className="w-3.5 h-3.5 text-purple-600" />
              <span className="text-xs font-medium text-purple-700">查看思考过程</span>
            </button>
            {isThinkingExpanded && (
              <div className="mt-2 px-4 py-3 bg-gradient-to-br from-purple-50 to-pink-50 border border-purple-200 rounded-lg shadow-inner">
                <p className="text-xs text-gray-700 whitespace-pre-wrap break-words leading-relaxed">
                  {message.thinking}
                </p>
              </div>
            )}
          </div>
        )}

        {/* 回复内容 */}
        <div className="rounded-2xl px-4 py-3 bg-white border border-gray-200 text-gray-800">
          <div className="whitespace-pre-wrap break-words">
            {message.content}
          </div>
        </div>
      </div>
    </div>
  )
}
