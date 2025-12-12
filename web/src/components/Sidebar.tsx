import { MessageSquare, Eye, Image } from 'lucide-react'
import type { Tab } from '../App'

interface SidebarProps {
  activeTab: Tab
  onTabChange: (tab: Tab) => void
}

const tabs = [
  { id: 'chat' as Tab, icon: MessageSquare, label: '文字聊天' },
  { id: 'vision' as Tab, icon: Eye, label: '图片理解' },
  { id: 'image' as Tab, icon: Image, label: '图片生成' },
]

export default function Sidebar({ activeTab, onTabChange }: SidebarProps) {
  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
      {/* Logo */}
      <div className="p-4 border-b border-gray-200">
        <h1 className="text-xl font-bold text-gray-800 flex items-center gap-2">
          <span className="text-2xl">🤖</span>
          Qwen Chat
        </h1>
        <p className="text-xs text-gray-500 mt-1">AI 助手 - 文字 / 视觉 / 生成</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4">
        <ul className="space-y-2">
          {tabs.map((tab) => {
            const Icon = tab.icon
            const isActive = activeTab === tab.id

            return (
              <li key={tab.id}>
                <button
                  onClick={() => onTabChange(tab.id)}
                  className={`
                    w-full flex items-center gap-3 px-4 py-3 rounded-lg
                    transition-all duration-200
                    ${isActive
                      ? 'bg-primary-50 text-primary-700 font-medium'
                      : 'text-gray-600 hover:bg-gray-100'
                    }
                  `}
                >
                  <Icon
                    className={`w-5 h-5 ${isActive ? 'text-primary-600' : 'text-gray-400'}`}
                  />
                  {tab.label}
                </button>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200">
        <div className="text-xs text-gray-400">
          <p>模型: Qwen3-8B / Qwen2-VL</p>
          <p className="mt-1">CPU 推理模式</p>
        </div>
      </div>
    </aside>
  )
}
