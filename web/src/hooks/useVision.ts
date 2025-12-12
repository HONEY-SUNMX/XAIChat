import { useState, useCallback } from 'react'
import { uploadImage, streamVisionAsk, deleteImage, VisionUploadResponse } from '../services/api'

interface VisionMessage {
  role: 'user' | 'assistant'
  content: string
}

interface UseVisionReturn {
  imageId: string | null
  imageInfo: VisionUploadResponse | null
  messages: VisionMessage[]
  isLoading: boolean
  isUploading: boolean
  upload: (file: File) => Promise<void>
  ask: (question: string) => Promise<void>
  clear: () => Promise<void>
}

export function useVision(): UseVisionReturn {
  const [imageId, setImageId] = useState<string | null>(null)
  const [imageInfo, setImageInfo] = useState<VisionUploadResponse | null>(null)
  const [messages, setMessages] = useState<VisionMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isUploading, setIsUploading] = useState(false)

  const upload = useCallback(async (file: File) => {
    setIsUploading(true)

    try {
      const response = await uploadImage(file)
      setImageId(response.image_id)
      setImageInfo(response)
      setMessages([]) // Clear previous conversation
    } catch (error) {
      console.error('Upload failed:', error)
      throw error
    } finally {
      setIsUploading(false)
    }
  }, [])

  const ask = useCallback(async (question: string) => {
    if (!imageId) {
      throw new Error('No image uploaded')
    }

    setMessages((prev) => [...prev, { role: 'user', content: question }])
    setIsLoading(true)

    let response = ''

    try {
      for await (const event of streamVisionAsk(imageId, question)) {
        switch (event.type) {
          case 'response':
            response += event.content || ''
            // Update with streaming content
            setMessages((prev) => {
              const lastIsAssistant = prev[prev.length - 1]?.role === 'assistant'
              if (lastIsAssistant) {
                return [...prev.slice(0, -1), { role: 'assistant', content: response }]
              }
              return [...prev, { role: 'assistant', content: response }]
            })
            break

          case 'done':
            // Response complete
            break

          case 'error':
            setMessages((prev) => [
              ...prev,
              { role: 'assistant', content: `错误: ${event.content}` },
            ])
            break
        }
      }
    } catch (error) {
      console.error('Vision query failed:', error)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `请求失败: ${error instanceof Error ? error.message : '未知错误'}` },
      ])
    } finally {
      setIsLoading(false)
    }
  }, [imageId])

  const clear = useCallback(async () => {
    if (imageId) {
      try {
        await deleteImage(imageId)
      } catch (e) {
        console.error('Failed to delete image:', e)
      }
    }
    setImageId(null)
    setImageInfo(null)
    setMessages([])
  }, [imageId])

  return {
    imageId,
    imageInfo,
    messages,
    isLoading,
    isUploading,
    upload,
    ask,
    clear,
  }
}
