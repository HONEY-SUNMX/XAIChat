import { useState } from 'react'
import { Wand2, Loader2, Download, Trash2 } from 'lucide-react'
import { useImageGen } from '../hooks/useImageGen'

export default function ImageGenPanel() {
  const [prompt, setPrompt] = useState('')
  const [negativePrompt, setNegativePrompt] = useState('')
  const [showAdvanced, setShowAdvanced] = useState(false)

  const { generatedImages, isGenerating, progress, error, generate, clearImages } = useImageGen()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!prompt.trim() || isGenerating) return

    await generate(prompt, {
      negativePrompt,
      width: 512,
      height: 512,
    })
  }

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-gray-200">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">图片生成</h2>
          <p className="text-sm text-gray-500">从文字描述生成图片</p>
        </div>
        {generatedImages.length > 0 && (
          <button
            onClick={clearImages}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          >
            <Trash2 className="w-4 h-4" />
            清空
          </button>
        )}
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Input Form (Left) */}
        <div className="w-1/3 border-r border-gray-200 bg-white p-6 overflow-y-auto">
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Prompt */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                图片描述 (Prompt)
              </label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="描述你想生成的图片..."
                className="w-full px-4 py-3 border border-gray-300 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-primary-500"
                rows={4}
                disabled={isGenerating}
              />
            </div>

            {/* Advanced Options Toggle */}
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-sm text-primary-600 hover:text-primary-700"
            >
              {showAdvanced ? '隐藏高级选项' : '显示高级选项'}
            </button>

            {/* Advanced Options */}
            {showAdvanced && (
              <div className="space-y-4 pt-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    负面提示词 (Negative Prompt)
                  </label>
                  <textarea
                    value={negativePrompt}
                    onChange={(e) => setNegativePrompt(e.target.value)}
                    placeholder="你不想出现在图片中的内容..."
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-primary-500"
                    rows={2}
                    disabled={isGenerating}
                  />
                </div>
              </div>
            )}

            {/* Progress */}
            {isGenerating && progress && (
              <div className="space-y-2">
                <div className="flex justify-between text-sm text-gray-600">
                  <span>生成中...</span>
                  <span>{progress.step}/{progress.total}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-primary-500 h-full transition-all duration-300 progress-bar-shine"
                    style={{ width: `${(progress.step / progress.total) * 100}%` }}
                  />
                </div>
              </div>
            )}

            {/* Error */}
            {error && (
              <div className="p-3 bg-red-50 text-red-600 rounded-lg text-sm">
                {error}
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isGenerating || !prompt.trim()}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary-500 text-white rounded-xl hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  生成中...
                </>
              ) : (
                <>
                  <Wand2 className="w-5 h-5" />
                  生成图片
                </>
              )}
            </button>

            <p className="text-xs text-gray-400 text-center">
              CPU 模式下生成约需 30-60 秒
            </p>
          </form>
        </div>

        {/* Generated Images (Right) */}
        <div className="flex-1 overflow-y-auto p-6">
          {generatedImages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-400">
              <Wand2 className="w-16 h-16 mb-4" />
              <p className="text-lg">还没有生成的图片</p>
              <p className="text-sm mt-2">输入描述开始创作</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              {generatedImages.map((img, idx) => (
                <div key={idx} className="bg-white rounded-xl shadow-md overflow-hidden">
                  <img
                    src={img.url}
                    alt={img.prompt}
                    className="w-full aspect-square object-cover"
                  />
                  <div className="p-3">
                    <p className="text-sm text-gray-600 truncate" title={img.prompt}>
                      {img.prompt}
                    </p>
                    <div className="flex items-center justify-between mt-2">
                      <span className="text-xs text-gray-400">Seed: {img.seed}</span>
                      <a
                        href={img.url}
                        download={img.filename}
                        className="flex items-center gap-1 text-xs text-primary-600 hover:text-primary-700"
                      >
                        <Download className="w-3 h-3" />
                        下载
                      </a>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
