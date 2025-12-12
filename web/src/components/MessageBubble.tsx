import { useState } from 'react'
import { User, Bot, Loader2, ChevronDown, ChevronRight, Brain } from 'lucide-react'
import { ChatMessage } from '../services/api'

interface MessageBubbleProps {
  message: ChatMessage
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const [isThinkingExpanded, setIsThinkingExpanded] = useState(false)

  const isUser = message.role === 'user'
  const isThinking = message.role === 'thinking'
  const isAssistant = message.role === 'assistant'

  // 思考中状态（单独的 thinking 消息，流式显示中）- 默认折叠，可展开
  if (isThinking) {
    return (
      <div className="flex gap-3 animate-fade-in-up">
        {/* Avatar */}
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-yellow-500 flex items-center justify-center">
          <Loader2 className="w-5 h-5 text-white animate-spin" />
        </div>

        {/* Thinking Content - 可折叠 */}
        <div className="max-w-[70%]">
          <button
            onClick={() => setIsThinkingExpanded(!isThinkingExpanded)}
            className="flex items-center gap-1.5 px-3 py-2 text-xs text-yellow-700 bg-yellow-50 border border-yellow-200 rounded-lg hover:bg-yellow-100 transition-colors"
          >
            {isThinkingExpanded ? (
              <ChevronDown className="w-3.5 h-3.5" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5" />
            )}
            <Brain className="w-3.5 h-3.5" />
            <span>思考中...</span>
            <Loader2 className="w-3 h-3 animate-spin ml-1" />
          </button>
          {isThinkingExpanded && (
            <div className="mt-2 px-3 py-2 bg-yellow-50 border border-yellow-200 rounded-lg">
              <p className="text-xs text-yellow-800 whitespace-pre-wrap break-words italic">
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
      <div className="flex gap-3 animate-fade-in-up flex-row-reverse">
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
    <div className="flex gap-3 animate-fade-in-up">
      {/* Avatar */}
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center">
        <Bot className="w-5 h-5 text-white" />
      </div>

      {/* Message Content with Collapsible Thinking */}
      <div className="max-w-[70%]">
        {/* 可折叠的思考内容（只在有 thinking 内容时显示） */}
        {message.thinking && (
          <div className="mb-2">
            <button
              onClick={() => setIsThinkingExpanded(!isThinkingExpanded)}
              className="flex items-center gap-1.5 px-2 py-1 text-xs text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
            >
              {isThinkingExpanded ? (
                <ChevronDown className="w-3.5 h-3.5" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5" />
              )}
              <Brain className="w-3.5 h-3.5" />
              <span>已完成思考</span>
            </button>
            {isThinkingExpanded && (
              <div className="mt-2 px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg">
                <p className="text-xs text-gray-600 whitespace-pre-wrap break-words">
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
