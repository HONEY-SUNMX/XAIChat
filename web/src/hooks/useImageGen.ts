import { useState, useCallback, useEffect } from 'react'
import { streamImageGenerate } from '../services/api'

// localStorage keys
const STORAGE_KEYS = {
  generatedImages: 'qwen-imagegen-images',
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

interface GeneratedImage {
  url: string
  filename: string
  prompt: string
  seed: number
}

interface UseImageGenReturn {
  generatedImages: GeneratedImage[]
  isGenerating: boolean
  progress: { step: number; total: number } | null
  error: string | null
  generate: (prompt: string, options?: GenerateOptions) => Promise<void>
  clearImages: () => void
}

interface GenerateOptions {
  negativePrompt?: string
  width?: number
  height?: number
  seed?: number
  numSteps?: number
}

export function useImageGen(): UseImageGenReturn {
  // Initialize state from localStorage
  const [generatedImages, setGeneratedImages] = useState<GeneratedImage[]>(() =>
    loadFromStorage(STORAGE_KEYS.generatedImages, [])
  )
  const [isGenerating, setIsGenerating] = useState(false)
  const [progress, setProgress] = useState<{ step: number; total: number } | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Persist generatedImages to localStorage whenever they change
  useEffect(() => {
    saveToStorage(STORAGE_KEYS.generatedImages, generatedImages)
  }, [generatedImages])

  const generate = useCallback(async (prompt: string, options: GenerateOptions = {}) => {
    setIsGenerating(true)
    setProgress({ step: 0, total: options.numSteps || 6 })
    setError(null)

    try {
      let resultSeed = options.seed || 0

      for await (const event of streamImageGenerate(prompt, options)) {
        switch (event.type) {
          case 'progress':
            setProgress({
              step: event.step || 0,
              total: event.total || 6,
            })
            break

          case 'done':
            if (event.image_url && event.filename) {
              setGeneratedImages((prev) => [
                {
                  url: event.image_url!,
                  filename: event.filename!,
                  prompt,
                  seed: resultSeed,
                },
                ...prev,
              ])
            }
            break

          case 'error':
            setError(event.error || '生成失败')
            break
        }
      }
    } catch (err) {
      console.error('Image generation failed:', err)
      setError(err instanceof Error ? err.message : '生成失败')
    } finally {
      setIsGenerating(false)
      setProgress(null)
    }
  }, [])

  const clearImages = useCallback(() => {
    setGeneratedImages([])
    setError(null)
  }, [])

  return {
    generatedImages,
    isGenerating,
    progress,
    error,
    generate,
    clearImages,
  }
}
