import { useState, useCallback, useEffect } from 'react'
import { streamChat, clearConversation, ChatMessage, ChatStreamEvent } from '../services/api'

// localStorage keys
const STORAGE_KEYS = {
  messages: 'qwen-chat-messages',
  conversationId: 'qwen-chat-conversation-id',
  enableThinking: 'qwen-chat-enable-thinking',
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

interface UseChatReturn {
  messages: ChatMessage[]
  isLoading: boolean
  conversationId: string | null
  enableThinking: boolean
  setEnableThinking: (value: boolean) => void
  sendMessage: (content: string) => Promise<void>
  clearChat: () => Promise<void>
}

export function useChat(): UseChatReturn {
  // Initialize state from localStorage
  const [messages, setMessages] = useState<ChatMessage[]>(() =>
    loadFromStorage(STORAGE_KEYS.messages, [])
  )
  const [isLoading, setIsLoading] = useState(false)
  const [conversationId, setConversationId] = useState<string | null>(() =>
    loadFromStorage(STORAGE_KEYS.conversationId, null)
  )
  const [enableThinking, setEnableThinking] = useState(() =>
    loadFromStorage(STORAGE_KEYS.enableThinking, true)
  )

  // Persist messages to localStorage whenever they change
  useEffect(() => {
    saveToStorage(STORAGE_KEYS.messages, messages)
  }, [messages])

  // Persist conversationId to localStorage
  useEffect(() => {
    saveToStorage(STORAGE_KEYS.conversationId, conversationId)
  }, [conversationId])

  // Persist enableThinking to localStorage
  useEffect(() => {
    saveToStorage(STORAGE_KEYS.enableThinking, enableThinking)
  }, [enableThinking])

  const sendMessage = useCallback(async (content: string) => {
    // Add user message
    setMessages((prev) => [...prev, { role: 'user', content }])
    setIsLoading(true)

    let assistantMessage = ''
    let thinkingContent = ''
    let updateCounter = 0
    const UPDATE_THROTTLE = 2  // Only update UI every N events for better performance

    try {
      for await (const event of streamChat(content, conversationId || undefined, enableThinking)) {
        switch (event.type) {
          case 'thinking':
            // Complete thinking content received (after </think> detected)
            thinkingContent = event.content || ''
            setMessages((prev) => {
              const filtered = prev.filter((m) => m.role !== 'thinking')
              return [...filtered, { role: 'thinking', content: thinkingContent }]
            })
            break

          case 'thinking_stream':
            // Real-time streaming of thinking content - throttle updates
            thinkingContent += event.content || ''
            updateCounter++
            
            // Only update every UPDATE_THROTTLE events to reduce re-renders
            if (updateCounter % UPDATE_THROTTLE === 0) {
              setMessages((prev) => {
                const filtered = prev.filter((m) => m.role !== 'thinking')
                return [...filtered, { role: 'thinking', content: thinkingContent }]
              })
            }
            break

          case 'response':
            assistantMessage += event.content || ''
            updateCounter++
            
            // Only update every UPDATE_THROTTLE events to reduce re-renders
            if (updateCounter % UPDATE_THROTTLE === 0) {
              setMessages((prev) => {
                const lastUserIndex = prev.map((m) => m.role).lastIndexOf('user')
                const beforeCurrentTurn = prev.slice(0, lastUserIndex + 1)
                const thinkingMsg = prev.find((m) => m.role === 'thinking')

                const newMessages = [...beforeCurrentTurn]
                if (thinkingMsg) {
                  newMessages.push(thinkingMsg)
                }
                newMessages.push({ role: 'assistant', content: assistantMessage })

                return newMessages
              })
            }
            break

          case 'done':
            if (event.conversation_id) {
              setConversationId(event.conversation_id)
            }
            // Final update with complete content
            setMessages((prev) => {
              const withoutThinking = prev.filter((m) => m.role !== 'thinking')
              const lastIndex = withoutThinking.length - 1
              
              if (lastIndex >= 0 && withoutThinking[lastIndex].role === 'assistant' && thinkingContent) {
                const result = [...withoutThinking]
                result[lastIndex] = {
                  ...result[lastIndex],
                  content: assistantMessage,  // Ensure final content is complete
                  thinking: thinkingContent
                }
                return result
              }

              return withoutThinking
            })
            break

          case 'error':
            console.error('Chat error:', event.content)
            setMessages((prev) => [
              ...prev.filter((m) => m.role !== 'thinking'),
              { role: 'assistant', content: `错误: ${event.content}` },
            ])
            break
        }
      }
    } catch (error) {
      console.error('Chat failed:', error)
      setMessages((prev) => [
        ...prev.filter((m) => m.role !== 'thinking'),
        { role: 'assistant', content: `请求失败: ${error instanceof Error ? error.message : '未知错误'}` },
      ])
    } finally {
      setIsLoading(false)
    }
  }, [conversationId, enableThinking])

  const clearChat = useCallback(async () => {
    if (conversationId) {
      try {
        await clearConversation(conversationId)
      } catch (e) {
        console.error('Failed to clear conversation:', e)
      }
    }
    setMessages([])
    setConversationId(null)
  }, [conversationId])

  return {
    messages,
    isLoading,
    conversationId,
    enableThinking,
    setEnableThinking,
    sendMessage,
    clearChat,
  }
}
