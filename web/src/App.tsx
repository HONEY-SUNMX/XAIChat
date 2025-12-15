import { useState } from 'react'
import Sidebar from './components/Sidebar'
import ChatPanel from './components/ChatPanel'
import VisionPanel from './components/VisionPanel'
import ImageGenPanel from './components/ImageGenPanel'
import MultimodalPanel from './components/MultimodalPanel'

export type Tab = 'chat' | 'vision' | 'image' | 'multimodal'

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('multimodal')

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Main Content - 使用 CSS 隐藏代替条件渲染，保持各面板状态 */}
      <main className="flex-1 overflow-hidden">
        <div className={`h-full ${activeTab === 'multimodal' ? '' : 'hidden'}`}>
          <MultimodalPanel />
        </div>
        <div className={`h-full ${activeTab === 'chat' ? '' : 'hidden'}`}>
          <ChatPanel />
        </div>
        <div className={`h-full ${activeTab === 'vision' ? '' : 'hidden'}`}>
          <VisionPanel />
        </div>
        <div className={`h-full ${activeTab === 'image' ? '' : 'hidden'}`}>
          <ImageGenPanel />
        </div>
      </main>
    </div>
  )
}

export default App
