import { useState, useRef, useEffect } from 'react'
import { Send, Trash2, Loader2, Brain } from 'lucide-react'
import { useChat } from '../hooks/useChat'
import MessageBubble from './MessageBubble'

export default function ChatPanel() {
  const [input, setInput] = useState('')
  const { messages, isLoading, sendMessage, clearChat, enableThinking, setEnableThinking } = useChat()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto'
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 150)}px`
    }
  }, [input])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = input.trim()
    if (!trimmed || isLoading) return

    setInput('')
    await sendMessage(trimmed)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-gray-200">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">文字聊天</h2>
          <p className="text-sm text-gray-500">与 Qwen3 进行对话</p>
        </div>
        <button
          onClick={clearChat}
          className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          title="清空对话"
        >
          <Trash2 className="w-4 h-4" />
          清空
        </button>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <div className="text-6xl mb-4">💬</div>
            <p className="text-lg">开始与 AI 对话吧</p>
            <p className="text-sm mt-2">输入消息后按 Enter 发送</p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <MessageBubble key={idx} message={msg} />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 bg-white border-t border-gray-200">
        <div className="flex gap-3 items-end">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入消息... (Shift+Enter 换行)"
            className="flex-1 px-4 py-3 border border-gray-300 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            rows={1}
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="flex items-center justify-center w-12 h-12 bg-primary-500 text-white rounded-xl hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
        <div className="flex items-center justify-between mt-2">
          {/* Thinking mode toggle */}
          <button
            onClick={() => setEnableThinking(!enableThinking)}
            className={`flex items-center gap-1.5 px-2 py-1 text-xs rounded-md transition-colors ${
              enableThinking
                ? 'text-primary-600 bg-primary-50 hover:bg-primary-100'
                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
            }`}
            title={enableThinking ? '深度思考：已开启' : '深度思考：已关闭'}
          >
            <Brain className="w-3.5 h-3.5" />
            深度思考
          </button>
          <p className="text-xs text-gray-400">
            CPU 模式下响应可能需要几秒钟
          </p>
        </div>
      </form>
    </div>
  )
}
