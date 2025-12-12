/**
 * API Service
 * Centralized API communication with the FastAPI backend.
 */

const API_BASE = '/api'

// Types
export interface ChatMessage {
  role: 'user' | 'assistant' | 'thinking'
  content: string
  thinking?: string  // assistant 消息可以携带已完成的思考内容
}

export interface ChatStreamEvent {
  type: 'thinking' | 'thinking_stream' | 'response' | 'done' | 'error'
  content?: string
  conversation_id?: string
}

export interface VisionUploadResponse {
  image_id: string
  filename: string
  size: number[]
  message: string
}

export interface VisionStreamEvent {
  type: 'response' | 'done' | 'error'
  content?: string
}

export interface ImageProgressEvent {
  type: 'progress' | 'done' | 'error'
  step?: number
  total?: number
  image_url?: string
  filename?: string
  error?: string
}

/**
 * Send a chat message with streaming support.
 */
export async function* streamChat(
  message: string,
  conversationId?: string,
  enableThinking: boolean = true
): AsyncGenerator<ChatStreamEvent> {
  const response = await fetch(`${API_BASE}/chat/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
      stream: true,
      enable_thinking: enableThinking,
    }),
  })

  if (!response.ok) {
    throw new Error(`Chat request failed: ${response.statusText}`)
  }

  const reader = response.body?.getReader()
  const decoder = new TextDecoder()

  if (!reader) {
    throw new Error('No response body')
  }

  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6)) as ChatStreamEvent
          yield data
        } catch (e) {
          console.error('Failed to parse SSE data:', e)
        }
      }
    }
  }
}

/**
 * Upload an image for vision processing.
 */
export async function uploadImage(file: File): Promise<VisionUploadResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE}/vision/upload`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Upload failed')
  }

  return response.json()
}

/**
 * Ask a question about an image with streaming support.
 */
export async function* streamVisionAsk(
  imageId: string,
  question: string
): AsyncGenerator<VisionStreamEvent> {
  const response = await fetch(`${API_BASE}/vision/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      image_id: imageId,
      question,
      stream: true,
    }),
  })

  if (!response.ok) {
    throw new Error(`Vision request failed: ${response.statusText}`)
  }

  const reader = response.body?.getReader()
  const decoder = new TextDecoder()

  if (!reader) {
    throw new Error('No response body')
  }

  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6)) as VisionStreamEvent
          yield data
        } catch (e) {
          console.error('Failed to parse SSE data:', e)
        }
      }
    }
  }
}

/**
 * Generate an image with streaming progress.
 */
export async function* streamImageGenerate(
  prompt: string,
  options: {
    negativePrompt?: string
    width?: number
    height?: number
    seed?: number
    numSteps?: number
  } = {}
): AsyncGenerator<ImageProgressEvent> {
  const response = await fetch(`${API_BASE}/image/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      prompt,
      negative_prompt: options.negativePrompt || '',
      width: options.width || 512,
      height: options.height || 512,
      seed: options.seed,
      num_steps: options.numSteps || 6,
    }),
  })

  if (!response.ok) {
    throw new Error(`Image generation failed: ${response.statusText}`)
  }

  const reader = response.body?.getReader()
  const decoder = new TextDecoder()

  if (!reader) {
    throw new Error('No response body')
  }

  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6)) as ImageProgressEvent
          yield data
        } catch (e) {
          console.error('Failed to parse SSE data:', e)
        }
      }
    }
  }
}

/**
 * Delete an uploaded image.
 */
export async function deleteImage(imageId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/vision/${imageId}`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    throw new Error('Failed to delete image')
  }
}

/**
 * Clear conversation history.
 */
export async function clearConversation(conversationId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/chat/${conversationId}`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    throw new Error('Failed to clear conversation')
  }
}
