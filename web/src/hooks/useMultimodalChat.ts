import { useState, useCallback, useEffect } from 'react'
import {
  streamMultimodalChat,
  streamMultimodalChatWithImage,
  clearMultimodalConversation,
  MultimodalMessage,
  MultimodalStreamEvent,
} from '../services/api'

// localStorage keys
const STORAGE_KEYS = {
  sessions: 'qwen-multimodal-sessions',
  currentSessionId: 'qwen-multimodal-current-session',
  enableThinking: 'qwen-multimodal-enable-thinking',
}

// Session interface
interface ChatSession {
  id: string
  title: string
  messages: MultimodalMessage[]
  conversationId: string | null
  createdAt: number
  updatedAt: number
}

// Helper functions for localStorage
function loadFromStorage<T>(key: string, defaultValue: T): T {
  try {
    const saved = localStorage.getItem(key)
    return saved ? JSON.parse(saved) : defaultValue
  } catch {
    return defaultValue
  }
}

function saveToStorage<T>(key: string, value: T): void {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch (e) {
    console.error('Failed to save to localStorage:', e)
  }
}

// Generate session title from first message
function generateSessionTitle(firstMessage: string): string {
  const maxLength = 30
  const trimmed = firstMessage.trim()
  if (trimmed.length <= maxLength) return trimmed
  return trimmed.substring(0, maxLength) + '...'
}

// Generate UUID (compatible fallback)
function generateUUID(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  // Fallback for older browsers
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

interface UseMultimodalChatReturn {
  // Current session
  messages: MultimodalMessage[]
  isLoading: boolean
  conversationId: string | null
  currentProgress: { step: number; total: number; preview?: string } | null
  
  // Settings
  enableThinking: boolean
  setEnableThinking: (value: boolean) => void
  
  // Actions
  sendMessage: (content: string, imageFile?: File) => Promise<void>
  clearChat: () => Promise<void>
  
  // Session management
  sessions: ChatSession[]
  currentSessionId: string
  createNewSession: () => void
  switchSession: (sessionId: string) => void
  deleteSession: (sessionId: string) => void
  renameSession: (sessionId: string, newTitle: string) => void
}

export function useMultimodalChat(): UseMultimodalChatReturn {
  // Load all sessions
  const [sessions, setSessions] = useState<ChatSession[]>(() => {
    const saved = loadFromStorage<ChatSession[]>(STORAGE_KEYS.sessions, [])
    // If no sessions, create a default one
    if (saved.length === 0) {
      const defaultSession: ChatSession = {
        id: generateUUID(),
        title: '新对话',
        messages: [],
        conversationId: null,
        createdAt: Date.now(),
        updatedAt: Date.now(),
      }
      return [defaultSession]
    }
    return saved
  })

  // Current session ID
  const [currentSessionId, setCurrentSessionId] = useState<string>(() => {
    const saved = loadFromStorage<string | null>(STORAGE_KEYS.currentSessionId, null)
    return saved || sessions[0]?.id || ''
  })

  // Get current session
  const currentSession = sessions.find((s) => s.id === currentSessionId) || sessions[0]

  // State for current session
  const [isLoading, setIsLoading] = useState(false)
  const [enableThinking, setEnableThinking] = useState(() =>
    loadFromStorage(STORAGE_KEYS.enableThinking, true)
  )
  const [currentProgress, setCurrentProgress] = useState<{ step: number; total: number; preview?: string } | null>(null)

  // Persist sessions
  useEffect(() => {
    saveToStorage(STORAGE_KEYS.sessions, sessions)
  }, [sessions])

  // Persist current session ID
  useEffect(() => {
    saveToStorage(STORAGE_KEYS.currentSessionId, currentSessionId)
  }, [currentSessionId])

  // Persist enableThinking
  useEffect(() => {
    saveToStorage(STORAGE_KEYS.enableThinking, enableThinking)
  }, [enableThinking])

  const sendMessage = useCallback(
    async (content: string, imageFile?: File) => {
      const session = sessions.find((s) => s.id === currentSessionId)
      if (!session) return

      // Add user message
      const userMessage: MultimodalMessage = {
        role: 'user',
        type: imageFile ? 'image_analysis' : 'text',
        content,
        image_file: imageFile,
      }

      const newMessages = [...session.messages, userMessage]
      
      // Update title if this is the first message
      const title = session.messages.length === 0 ? generateSessionTitle(content) : session.title
      
      // Update session with user message
      setSessions((prev) =>
        prev.map((s) =>
          s.id === currentSessionId
            ? { ...s, messages: newMessages, title, updatedAt: Date.now() }
            : s
        )
      )
      setIsLoading(true)
      setCurrentProgress(null)

      let assistantMessage = ''
      let thinkingContent = ''
      let generatedImageUrl: string | undefined
      let generatedImageMetadata: { filename?: string; seed?: number } | undefined

      try {
        // Choose appropriate stream function
        const stream = imageFile
          ? streamMultimodalChatWithImage(content, imageFile, session.conversationId || undefined, enableThinking)
          : streamMultimodalChat(content, session.conversationId || undefined, enableThinking)

        for await (const event of stream) {
          switch (event.type) {
            case 'thinking':
              thinkingContent = event.content || ''
              setSessions((prev) =>
                prev.map((s) =>
                  s.id === currentSessionId
                    ? {
                        ...s,
                        messages: [
                          ...s.messages.filter((m) => m.role !== 'thinking'),
                          { role: 'thinking', type: 'text', content: thinkingContent },
                        ],
                        updatedAt: Date.now(),
                      }
                    : s
                )
              )
              break

            case 'thinking_stream':
              thinkingContent += event.content || ''
              setSessions((prev) =>
                prev.map((s) =>
                  s.id === currentSessionId
                    ? {
                        ...s,
                        messages: [
                          ...s.messages.filter((m) => m.role !== 'thinking'),
                          { role: 'thinking', type: 'text', content: thinkingContent },
                        ],
                        updatedAt: Date.now(),
                      }
                    : s
                )
              )
              break

            case 'response':
              assistantMessage += event.content || ''
              setSessions((prev) =>
                prev.map((s) => {
                  if (s.id !== currentSessionId) return s
                  
                  const lastUserIndex = s.messages.map((m) => m.role).lastIndexOf('user')
                  const beforeCurrentTurn = s.messages.slice(0, lastUserIndex + 1)
                  const thinkingMsg = s.messages.find((m) => m.role === 'thinking')

                  const updatedMessages = [...beforeCurrentTurn]
                  if (thinkingMsg) {
                    updatedMessages.push(thinkingMsg)
                  }
                  updatedMessages.push({
                    role: 'assistant',
                    type: generatedImageUrl ? 'generated_image' : 'text',
                    content: assistantMessage,
                    image_url: generatedImageUrl,
                    metadata: generatedImageMetadata,
                  })

                  return { ...s, messages: updatedMessages, updatedAt: Date.now() }
                })
              )
              break

            case 'image_generated':
              generatedImageUrl = event.image_url
              generatedImageMetadata = {
                filename: event.filename,
                seed: event.seed,
              }
              setCurrentProgress(null)
              
              // Update with image
              setSessions((prev) =>
                prev.map((s) => {
                  if (s.id !== currentSessionId) return s
                  
                  const userIdx = s.messages.map((m) => m.role).lastIndexOf('user')
                  const before = s.messages.slice(0, userIdx + 1)
                  const thinking = s.messages.find((m) => m.role === 'thinking')
                  const existing = s.messages.slice(userIdx + 1).find((m) => m.role === 'assistant')

                  const finalMessages = [...before]
                  if (thinking) finalMessages.push(thinking)
                  finalMessages.push({
                    role: 'assistant',
                    type: 'generated_image',
                    content: existing?.content || assistantMessage,
                    image_url: generatedImageUrl,
                    metadata: generatedImageMetadata,
                  })

                  return { ...s, messages: finalMessages, updatedAt: Date.now() }
                })
              )
              break

            case 'progress':
              if (event.step !== undefined && event.total !== undefined) {
                setCurrentProgress({ 
                  step: event.step, 
                  total: event.total,
                  preview: event.preview,
                })
              }
              break

            case 'done':
              setSessions((prev) =>
                prev.map((s) => {
                  if (s.id !== currentSessionId) return s
                  
                  let updates: Partial<ChatSession> = { updatedAt: Date.now() }
                  if (event.conversation_id) {
                    updates.conversationId = event.conversation_id
                  }
                  
                  // Merge thinking
                  const withoutThinking = s.messages.filter((m) => m.role !== 'thinking')
                  const lastIdx = withoutThinking.length - 1

                  if (lastIdx >= 0 && withoutThinking[lastIdx].role === 'assistant' && thinkingContent) {
                    withoutThinking[lastIdx] = {
                      ...withoutThinking[lastIdx],
                      thinking: thinkingContent,
                    }
                  }
                  
                  updates.messages = withoutThinking

                  return { ...s, ...updates }
                })
              )
              break

            case 'error':
              console.error('Multimodal chat error:', event.content)
              setSessions((prev) =>
                prev.map((s) => {
                  if (s.id !== currentSessionId) return s
                  
                  return {
                    ...s,
                    messages: [
                      ...s.messages.filter((m) => m.role !== 'thinking'),
                      {
                        role: 'assistant',
                        type: 'text',
                        content: `错误: ${event.content}`,
                      },
                    ],
                    updatedAt: Date.now(),
                  }
                })
              )
              break
          }
        }
      } catch (error) {
        console.error('Multimodal chat failed:', error)
        setSessions((prev) =>
          prev.map((s) => {
            if (s.id !== currentSessionId) return s
            
            return {
              ...s,
              messages: [
                ...s.messages.filter((m) => m.role !== 'thinking'),
                {
                  role: 'assistant',
                  type: 'text',
                  content: `请求失败: ${error instanceof Error ? error.message : '未知错误'}`,
                },
              ],
              updatedAt: Date.now(),
            }
          })
        )
      } finally {
        setIsLoading(false)
        setCurrentProgress(null)
      }
    },
    [sessions, currentSessionId, enableThinking]
  )

  const clearChat = useCallback(async () => {
    const session = sessions.find((s) => s.id === currentSessionId)
    if (session?.conversationId) {
      try {
        await clearMultimodalConversation(session.conversationId)
      } catch (e) {
        console.error('Failed to clear conversation:', e)
      }
    }
    setSessions((prev) =>
      prev.map((s) =>
        s.id === currentSessionId
          ? { ...s, messages: [], conversationId: null, updatedAt: Date.now() }
          : s
      )
    )
    setCurrentProgress(null)
  }, [sessions, currentSessionId])

  const createNewSession = useCallback(() => {
    // Check if there's any empty session
    const emptySession = sessions.find((s) => s.messages.length === 0)
    if (emptySession) {
      // Switch to the existing empty session instead of creating new one
      setCurrentSessionId(emptySession.id)
      return
    }
    
    // No empty session found, create a new one
    const newSession: ChatSession = {
      id: generateUUID(),
      title: '新对话',
      messages: [],
      conversationId: null,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    }
    setSessions((prev) => [newSession, ...prev])
    setCurrentSessionId(newSession.id)
  }, [sessions, currentSessionId])

  const switchSession = useCallback((sessionId: string) => {
    setCurrentSessionId(sessionId)
    setCurrentProgress(null)
  }, [])

  const deleteSession = useCallback((sessionId: string) => {
    setSessions((prev) => {
      const filtered = prev.filter((s) => s.id !== sessionId)
      // Ensure at least one session exists
      if (filtered.length === 0) {
        const defaultSession: ChatSession = {
          id: generateUUID(),
          title: '新对话',
          messages: [],
          conversationId: null,
          createdAt: Date.now(),
          updatedAt: Date.now(),
        }
        setCurrentSessionId(defaultSession.id)
        return [defaultSession]
      }
      // Switch to another session if deleting current
      if (sessionId === currentSessionId) {
        setCurrentSessionId(filtered[0].id)
      }
      return filtered
    })
  }, [currentSessionId])

  const renameSession = useCallback((sessionId: string, newTitle: string) => {
    setSessions((prev) =>
      prev.map((s) =>
        s.id === sessionId
          ? { ...s, title: newTitle, updatedAt: Date.now() }
          : s
      )
    )
  }, [])

  return {
    messages: currentSession?.messages || [],
    isLoading,
    conversationId: currentSession?.conversationId || null,
    currentProgress,
    enableThinking,
    setEnableThinking,
    sendMessage,
    clearChat,
    sessions,
    currentSessionId,
    createNewSession,
    switchSession,
    deleteSession,
    renameSession,
  }
}
