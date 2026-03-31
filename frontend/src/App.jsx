import { useState } from 'react'
import { useTheme, ThemeProvider } from './ThemeContext'
import { SpeakingProvider } from './SpeakingContext'
import ChatWindow from './components/ChatWindow'
import Header from './components/Header'
import Sidebar from './components/Sidebar'

function Layout() {
  const { theme } = useTheme()
  const [settingsOpen, setSettingsOpen] = useState(false)

  return (
    <div className="h-screen flex flex-col" style={{ background: theme.bg, color: theme.text }}>
      <Header onSettingsClick={() => setSettingsOpen(v => !v)} settingsOpen={settingsOpen} />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar settingsOpen={settingsOpen} onCloseSettings={() => setSettingsOpen(false)} />
        <main className="flex-1 overflow-hidden">
          <ChatWindow />
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <SpeakingProvider>
        <Layout />
      </SpeakingProvider>
    </ThemeProvider>
  )
}
