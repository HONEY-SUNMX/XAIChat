import { Brain, ImageIcon, Sparkles } from 'lucide-react'
import { MultimodalMessage } from '../services/api'
import { useState, useEffect } from 'react'

interface Props {
  message: MultimodalMessage
  showWatermark?: boolean
}

export default function MultimodalMessageBubble({ message, showWatermark = true }: Props) {
  const isUser = message.role === 'user'
  const isThinking = message.role === 'thinking'
  const [imagePreview, setImagePreview] = useState<string | null>(null)

  // Generate image preview for user uploaded images
  useEffect(() => {
    if (message.image_file && message.image_file instanceof Blob) {
      const reader = new FileReader()
      reader.onloadend = () => {
        setImagePreview(reader.result as string)
      }
      reader.readAsDataURL(message.image_file)
    }
  }, [message.image_file])

  // Thinking message style - 默认折叠，美化设计
  if (isThinking) {
    return (
      <div className="flex gap-3 items-start text-sm animate-fade-in-up">
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white font-medium shadow-sm">
          AI
        </div>
        <div className="flex-1">
          <details className="group">
            <summary className="cursor-pointer flex items-center gap-2 px-3 py-2 bg-gradient-to-r from-purple-50 to-pink-50 hover:from-purple-100 hover:to-pink-100 rounded-lg border border-purple-200 transition-all list-none shadow-sm">
              <svg
                className="w-3.5 h-3.5 text-purple-600 transition-transform group-open:rotate-90"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              <span className="w-5 h-5 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white text-[10px] font-medium">
                AI
              </span>
              <span className="text-xs font-medium text-purple-700">思考中</span>
              {/* 动画点点点 */}
              <span className="flex gap-0.5 ml-1">
                <span className="w-1 h-1 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                <span className="w-1 h-1 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                <span className="w-1 h-1 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
              </span>
            </summary>
            <div className="mt-2 bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg px-4 py-3 border border-purple-200 shadow-inner">
              <div className="text-gray-700 whitespace-pre-wrap text-xs leading-relaxed">
                {message.content}
              </div>
            </div>
          </details>
        </div>
      </div>
    )
  }

  // User message
  if (isUser) {
    return (
      <div className="flex gap-3 items-start justify-end">
        <div className="max-w-[70%]">
          {/* User uploaded image */}
          {message.type === 'image_analysis' && (imagePreview || message.image_url) && (
            <div className="mb-2">
              <img
                src={imagePreview || message.image_url}
                alt="Uploaded"
                className="rounded-lg max-w-full h-auto shadow-sm border border-gray-200"
              />
            </div>
          )}
          {/* User text */}
          <div className="bg-blue-600 text-white rounded-lg px-4 py-3 shadow-sm">
            <div className="whitespace-pre-wrap break-words">{message.content}</div>
          </div>
        </div>
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white font-medium">
          你
        </div>
      </div>
    )
  }

  // Assistant message
  return (
    <div className="flex gap-3 items-start">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white font-medium">
        AI
      </div>
      <div className="flex-1 max-w-[70%]">
        {/* Thinking content (collapsed by default) - 美化样式 */}
        {message.thinking && (
          <details className="mb-2 group">
            <summary className="cursor-pointer flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-purple-50 to-pink-50 hover:from-purple-100 hover:to-pink-100 border border-purple-200 rounded-lg transition-all shadow-sm list-none">
              <svg
                className="w-3.5 h-3.5 text-purple-600 transition-transform group-open:rotate-90"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              <span className="w-5 h-5 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white text-[10px] font-medium">
                AI
              </span>
              <span className="text-xs font-medium text-purple-700">查看思考过程</span>
            </summary>
            <div className="mt-2 bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg px-4 py-3 text-xs text-gray-700 border border-purple-200 shadow-inner whitespace-pre-wrap leading-relaxed">
              {message.thinking}
            </div>
          </details>
        )}

        {/* Generated image */}
        {message.type === 'generated_image' && message.image_url && (
          <div className="mb-2 relative group">
            <img
              src={message.image_url}
              alt="Generated"
              className="rounded-lg max-w-full h-auto shadow-md border border-gray-200"
            />
            {showWatermark && (
              <div className="absolute top-2 left-2 bg-black/60 text-white px-2 py-1 rounded text-xs flex items-center gap-1">
                <Sparkles className="w-3 h-3" />
                AI 生成
              </div>
            )}
            {message.metadata?.seed && (
              <div className="absolute bottom-2 right-2 bg-black/60 text-white px-2 py-1 rounded text-xs">
                Seed: {message.metadata.seed}
              </div>
            )}
          </div>
        )}

        {/* Assistant text response */}
        <div className="bg-white rounded-lg px-4 py-3 shadow-sm border border-gray-200">
          <div className="text-gray-800 whitespace-pre-wrap break-words leading-relaxed">
            {message.content}
          </div>
        </div>
      </div>
    </div>
  )
}
