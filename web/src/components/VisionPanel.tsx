import { useState, useRef, useEffect } from 'react'
import { Upload, Send, Trash2, Loader2, Image as ImageIcon, X } from 'lucide-react'
import { useVision } from '../hooks/useVision'

export default function VisionPanel() {
  const [input, setInput] = useState('')
  const { imageId, imageInfo, messages, isLoading, isUploading, upload, ask, clear } = useVision()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      await upload(file)
    } catch (error) {
      console.error('Upload error:', error)
      alert('图片上传失败')
    }

    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = input.trim()
    if (!trimmed || isLoading || !imageId) return

    setInput('')
    await ask(trimmed)
  }

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file && file.type.startsWith('image/')) {
      try {
        await upload(file)
      } catch (error) {
        console.error('Upload error:', error)
        alert('图片上传失败')
      }
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
  }

  // Handle Ctrl+V paste from clipboard
  const handlePaste = async (e: ClipboardEvent) => {
    const items = e.clipboardData?.items
    if (!items) return

    for (const item of items) {
      if (item.type.startsWith('image/')) {
        e.preventDefault()
        const file = item.getAsFile()
        if (file) {
          try {
            await upload(file)
          } catch (error) {
            console.error('Paste upload error:', error)
            alert('图片粘贴上传失败')
          }
        }
        break
      }
    }
  }

  // Add global paste event listener
  useEffect(() => {
    document.addEventListener('paste', handlePaste)
    return () => {
      document.removeEventListener('paste', handlePaste)
    }
  }, [upload])

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-gray-200">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">图片理解</h2>
          <p className="text-sm text-gray-500">上传图片，让 AI 分析</p>
        </div>
        {imageId && (
          <button
            onClick={clear}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          >
            <Trash2 className="w-4 h-4" />
            清除图片
          </button>
        )}
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Image Preview (Left) */}
        <div className="w-1/3 border-r border-gray-200 bg-white p-4">
          {imageId && imageInfo ? (
            <div className="relative">
              <img
                src={`/uploads/${imageId}${imageInfo.filename.substring(imageInfo.filename.lastIndexOf('.'))}`}
                alt="Uploaded"
                className="w-full rounded-lg shadow-md"
              />
              <button
                onClick={clear}
                className="absolute top-2 right-2 p-1 bg-red-500 text-white rounded-full hover:bg-red-600"
              >
                <X className="w-4 h-4" />
              </button>
              <div className="mt-2 text-xs text-gray-500">
                {imageInfo.filename} ({imageInfo.size[0]}x{imageInfo.size[1]})
              </div>
            </div>
          ) : (
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              className="h-full flex flex-col items-center justify-center border-2 border-dashed border-gray-300 rounded-lg hover:border-primary-500 transition-colors cursor-pointer"
              onClick={() => fileInputRef.current?.click()}
            >
              {isUploading ? (
                <Loader2 className="w-12 h-12 text-primary-500 animate-spin" />
              ) : (
                <>
                  <Upload className="w-12 h-12 text-gray-400 mb-4" />
                  <p className="text-gray-600 font-medium">点击或拖拽上传图片</p>
                  <p className="text-sm text-gray-400 mt-2">也可以直接 Ctrl+V 粘贴</p>
                  <p className="text-xs text-gray-400 mt-1">支持 JPG, PNG, GIF, WebP</p>
                </>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileSelect}
                className="hidden"
              />
            </div>
          )}
        </div>

        {/* Chat (Right) */}
        <div className="flex-1 flex flex-col">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {!imageId ? (
              <div className="flex flex-col items-center justify-center h-full text-gray-400">
                <ImageIcon className="w-16 h-16 mb-4" />
                <p className="text-lg">请先上传图片</p>
              </div>
            ) : messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-gray-400">
                <p className="text-lg">图片已加载</p>
                <p className="text-sm mt-2">输入问题开始分析图片</p>
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
                >
                  <div
                    className={`
                      max-w-[70%] rounded-2xl px-4 py-3
                      ${msg.role === 'user'
                        ? 'bg-primary-500 text-white'
                        : 'bg-white border border-gray-200'
                      }
                    `}
                  >
                    {msg.content}
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <form onSubmit={handleSubmit} className="p-4 bg-white border-t border-gray-200">
            <div className="flex gap-3">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={imageId ? "输入问题..." : "请先上传图片"}
                className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500"
                disabled={!imageId || isLoading}
              />
              <button
                type="submit"
                disabled={!imageId || isLoading || !input.trim()}
                className="flex items-center justify-center w-12 h-12 bg-primary-500 text-white rounded-xl hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </div>
            <p className="text-xs text-gray-400 mt-2 text-center">
              视觉理解在 CPU 上可能需要 1-2 分钟
            </p>
          </form>
        </div>
      </div>
    </div>
  )
}
