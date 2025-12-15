import { useState, useRef, useEffect } from 'react'
import { Send, Trash2, Loader2, Brain, ImagePlus, X, MessageSquarePlus, Menu, Edit2, Check } from 'lucide-react'
import { useMultimodalChat } from '../hooks/useMultimodalChat'
import MultimodalMessageBubble from './MultimodalMessageBubble'

export default function MultimodalPanel() {
  const [input, setInput] = useState('')
  const [selectedImage, setSelectedImage] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [showWatermark, setShowWatermark] = useState(() => {
    const saved = localStorage.getItem('showWatermark')
    return saved ? JSON.parse(saved) : true
  })
  const [showSessionList, setShowSessionList] = useState(false)
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null)
  const [editingTitle, setEditingTitle] = useState('')
  const {
    messages,
    isLoading,
    sendMessage,
    clearChat,
    enableThinking,
    setEnableThinking,
    currentProgress,
    sessions,
    currentSessionId,
    createNewSession,
    switchSession,
    deleteSession,
    renameSession,
  } = useMultimodalChat()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const sessionDropdownRef = useRef<HTMLDivElement>(null)

  // Persist watermark setting
  useEffect(() => {
    localStorage.setItem('showWatermark', JSON.stringify(showWatermark))
  }, [showWatermark])

  // Close session list when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (sessionDropdownRef.current && !sessionDropdownRef.current.contains(event.target as Node)) {
        setShowSessionList(false)
      }
    }

    if (showSessionList) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showSessionList])

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

  // Generate image preview
  useEffect(() => {
    if (selectedImage) {
      const reader = new FileReader()
      reader.onloadend = () => {
        setImagePreview(reader.result as string)
      }
      reader.readAsDataURL(selectedImage)
    } else {
      setImagePreview(null)
    }
  }, [selectedImage])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = input.trim()
    if (!trimmed || isLoading) return

    setInput('')
    const imageToSend = selectedImage
    setSelectedImage(null)
    await sendMessage(trimmed, imageToSend || undefined)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file && file.type.startsWith('image/')) {
      setSelectedImage(file)
    }
  }

  const handleRemoveImage = () => {
    setSelectedImage(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handlePaste = (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const items = e.clipboardData?.items
    if (!items) return

    for (let i = 0; i < items.length; i++) {
      const item = items[i]
      if (item.type.indexOf('image') !== -1) {
        e.preventDefault()
        const blob = item.getAsFile()
        if (blob) {
          // Create a proper File object with a name
          const file = new File([blob], `pasted-image-${Date.now()}.png`, { type: blob.type })
          setSelectedImage(file)
          console.log('粘贴图片成功:', file.name, file.type, file.size)
        }
        break
      }
    }
  }

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-gray-200">
        <div className="flex items-center gap-3">
          <div className="relative" ref={sessionDropdownRef}>
            <button
              onClick={() => setShowSessionList(!showSessionList)}
              className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              title="会话列表"
            >
              <Menu className="w-4 h-4" />
              <span className="font-medium">{sessions.find(s => s.id === currentSessionId)?.title || '新对话'}</span>
            </button>
            {/* Session dropdown */}
            {showSessionList && (
              <div className="absolute top-full left-0 mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 max-h-96 overflow-y-auto z-50">
                <div className="p-2 border-b border-gray-200">
                  <button
                    onClick={() => {
                      createNewSession()
                      setShowSessionList(false)
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-purple-600 hover:bg-purple-50 rounded-lg transition-colors"
                  >
                    <MessageSquarePlus className="w-4 h-4" />
                    新建对话
                  </button>
                </div>
                <div className="p-2">
                  {sessions.map((session) => (
                    <div
                      key={session.id}
                      className={`flex items-center gap-2 px-3 py-2 rounded-lg mb-1 ${
                        session.id === currentSessionId
                          ? 'bg-purple-50 text-purple-700'
                          : 'hover:bg-gray-50 text-gray-700'
                      }`}
                    >
                      {editingSessionId === session.id ? (
                        <>
                          <input
                            type="text"
                            value={editingTitle}
                            onChange={(e) => setEditingTitle(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') {
                                e.preventDefault()
                                if (editingTitle.trim()) {
                                  renameSession(session.id, editingTitle.trim())
                                }
                                setEditingSessionId(null)
                                setEditingTitle('')
                              } else if (e.key === 'Escape') {
                                setEditingSessionId(null)
                                setEditingTitle('')
                              }
                            }}
                            className="flex-1 text-sm px-2 py-1 border border-purple-300 rounded focus:outline-none focus:ring-2 focus:ring-purple-500"
                            autoFocus
                            onClick={(e) => e.stopPropagation()}
                          />
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              if (editingTitle.trim()) {
                                renameSession(session.id, editingTitle.trim())
                              }
                              setEditingSessionId(null)
                              setEditingTitle('')
                            }}
                            className="flex-shrink-0 p-1 text-purple-600 hover:text-purple-700 transition-colors"
                            title="确认"
                          >
                            <Check className="w-3 h-3" />
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            onClick={() => {
                              switchSession(session.id)
                              setShowSessionList(false)
                            }}
                            className="flex-1 text-left text-sm truncate"
                          >
                            {session.title}
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              setEditingSessionId(session.id)
                              setEditingTitle(session.title)
                            }}
                            className="flex-shrink-0 p-1 text-gray-400 hover:text-purple-600 transition-colors"
                            title="重命名"
                          >
                            <Edit2 className="w-3 h-3" />
                          </button>
                          {sessions.length > 1 && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                deleteSession(session.id)
                              }}
                              className="flex-shrink-0 p-1 text-gray-400 hover:text-red-600 transition-colors"
                              title="删除会话"
                            >
                              <X className="w-3 h-3" />
                            </button>
                          )}
                        </>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
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
            <div className="text-6xl mb-4">🎨</div>
            <p className="text-lg font-medium mb-2">多模态 AI 对话</p>
            <div className="text-sm text-center space-y-1">
              <p>💬 发送文字进行对话</p>
              <p>🖼️ 上传图片让 AI 分析</p>
              <p>🎨 输入"画一只猫"生成图片</p>
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, idx) => (
              <MultimodalMessageBubble key={idx} message={msg} showWatermark={showWatermark} />
            ))}
            {/* Loading indicator when waiting for response */}
            {isLoading && messages.length > 0 && messages[messages.length - 1].role === 'user' && !currentProgress && (
              <div className="flex gap-3 items-start animate-fade-in-up">
                <div className="flex flex-col items-center gap-1">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white font-medium shadow-sm">
                    AI
                  </div>
                  <div className="flex gap-1">
                    <span className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                    <span className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                    <span className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                  </div>
                </div>
              </div>
            )}
            {/* Image generation progress with preview */}
            {currentProgress && (
              <div className="flex gap-3 items-start">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white">
                  <Loader2 className="w-4 h-4 animate-spin" />
                </div>
                <div className="flex-1 space-y-3">
                  {/* Preview image */}
                  {currentProgress.preview && (
                    <div className="relative rounded-lg overflow-hidden border border-purple-200 shadow-md">
                      <img
                        src={currentProgress.preview}
                        alt="生成预览"
                        className="w-full h-auto"
                        style={{ imageRendering: 'pixelated' }}
                      />
                      <div className="absolute top-2 right-2 bg-black/60 backdrop-blur-sm text-white px-2 py-1 rounded text-xs font-mono">
                        {currentProgress.step}/{currentProgress.total}
                      </div>
                    </div>
                  )}
                  {/* Progress bar */}
                  <div className="bg-white rounded-lg px-4 py-3 shadow-sm border border-gray-200">
                    <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
                      <span>正在生成图片...</span>
                      <span className="font-mono text-xs">
                        {Math.round((currentProgress.step / currentProgress.total) * 100)}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-gradient-to-r from-purple-500 to-pink-500 h-2 rounded-full transition-all duration-300"
                        style={{
                          width: `${(currentProgress.step / currentProgress.total) * 100}%`,
                        }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 bg-white border-t border-gray-200">
        {/* Image preview */}
        {imagePreview && (
          <div className="mb-3 relative inline-block">
            <img
              src={imagePreview}
              alt="Preview"
              className="h-20 rounded-lg border-2 border-purple-200 shadow-sm"
            />
            <button
              type="button"
              onClick={handleRemoveImage}
              className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 hover:bg-red-600 text-white rounded-full flex items-center justify-center shadow-md transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
            <div className="absolute bottom-1 left-1 bg-black/60 text-white px-2 py-0.5 rounded text-xs">
              {selectedImage?.name}
            </div>
          </div>
        )}

        <div className="flex gap-3 items-end">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            placeholder={
              selectedImage
                ? '描述你想了解的内容...'
                : '输入消息或点击图标上传图片... (支持Ctrl+V粘贴图片)'
            }
            disabled={isLoading}
            className="flex-1 resize-none rounded-lg border border-gray-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed max-h-[150px]"
            rows={1}
          />
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleImageSelect}
            className="hidden"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isLoading}
            className="flex-shrink-0 p-3 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="上传图片"
          >
            <ImagePlus className="w-5 h-5" />
          </button>
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="flex-shrink-0 p-3 rounded-lg bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md hover:shadow-lg"
            title="发送消息 (Enter)"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
        <div className="flex items-center justify-between mt-2">
          <div className="flex items-center gap-3">
            {/* Thinking mode toggle */}
            <button
              onClick={() => setEnableThinking(!enableThinking)}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg transition-all border ${
                enableThinking
                  ? 'text-purple-600 bg-purple-50 hover:bg-purple-100 border-purple-200 shadow-sm'
                  : 'text-gray-600 bg-gray-50 hover:bg-gray-100 border-gray-200'
              }`}
              title={enableThinking ? '深度思考：已开启' : '深度思考：已关闭'}
            >
              <Brain className={`w-3.5 h-3.5 ${enableThinking ? 'text-purple-600' : 'text-gray-500'}`} />
              <span className="font-medium">深度思考</span>
              {enableThinking && (
                <span className="ml-0.5 w-1.5 h-1.5 rounded-full bg-purple-600 animate-pulse"></span>
              )}
            </button>
            {/* Watermark toggle */}
            <button
              onClick={() => setShowWatermark(!showWatermark)}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg transition-all border ${
                showWatermark
                  ? 'text-purple-600 bg-purple-50 hover:bg-purple-100 border-purple-200 shadow-sm'
                  : 'text-gray-600 bg-gray-50 hover:bg-gray-100 border-gray-200'
              }`}
              title={showWatermark ? '图片水印：已开启' : '图片水印：已关闭'}
            >
              <span className="font-medium">💧 水印</span>
              {showWatermark && (
                <span className="ml-0.5 w-1.5 h-1.5 rounded-full bg-purple-600 animate-pulse"></span>
              )}
            </button>
          </div>
          <div className="text-xs text-gray-500">
            <span>按 Enter 发送，Shift+Enter 换行</span>
            {selectedImage && (
              <span className="ml-3 text-purple-600">📷 已选择图片</span>
            )}
          </div>
        </div>
      </form>
    </div>
  )
}
