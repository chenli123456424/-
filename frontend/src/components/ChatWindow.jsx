import { useState, useRef, useEffect } from 'react'
import { useTheme } from '../ThemeContext'
import { useSpeaking } from '../SpeakingContext'
import MessageBubble from './MessageBubble'
import InputBox from './InputBox'
import { ChatWebSocket } from '../api/websocket'

const INITIAL_MESSAGES = [
  { id: 1, type: 'assistant', content: '你好！我是小智数码助手，可以为您提供深度搜索、方言朗读以及智能问答服务。有什么我可以帮助你的吗？' }
]

export default function ChatWindow() {
  const { theme } = useTheme()
  const { isSpeaking, setIsSpeaking, ttsLang, ttsEnabled, setTtsEnabled, audioObjRef, stopAudio } = useSpeaking()
  const ttsLangRef = useRef(ttsLang)
  ttsLangRef.current = ttsLang  // 每次渲染都更新 ref
  const [messages, setMessages] = useState(INITIAL_MESSAGES)
  const [loading, setLoading] = useState(false)
  const [wsStatus, setWsStatus] = useState('disconnected')
  const messagesEndRef = useRef(null)
  const wsRef = useRef(null)
  const activeIdRef = useRef(null)
  // 用 ref 保存 setIsSpeaking，避免 WebSocket 闭包捕获旧引用
  const setIsSpeakingRef = useRef(setIsSpeaking)
  setIsSpeakingRef.current = setIsSpeaking

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const playAudio = (base64Data) => {
    try {
      const bytes = Uint8Array.from(atob(base64Data), c => c.charCodeAt(0))
      const blob = new Blob([bytes], { type: 'audio/mp3' })
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      audioObjRef.current = audio  // 存引用，供外部控制
      audio.play()
        .then(() => setIsSpeakingRef.current(true))
        .catch(e => console.error('[Audio] 播放被阻止:', e))
      audio.onended = () => {
        setIsSpeakingRef.current(false)
        audioObjRef.current = null
        URL.revokeObjectURL(url)
      }
      audio.onerror = () => {
        setIsSpeakingRef.current(false)
        audioObjRef.current = null
      }
    } catch (e) {
      console.error('[Audio] 解码失败:', e)
    }
  }

  const playAudioRef = useRef(playAudio)
  playAudioRef.current = playAudio

  const makeHandlers = () => ({
    onOpen: () => setWsStatus('connected'),
    onClose: () => { setWsStatus('disconnected'); wsRef.current = null },
    onError: (err) => {
      setWsStatus('error')
      setLoading(false)
      if (activeIdRef.current) {
        setMessages(prev => prev.map(m =>
          m.id === activeIdRef.current
            ? { ...m, content: `错误: ${err}`, error: true, thinking: false }
            : m
        ))
        activeIdRef.current = null
      }
    },
    onThought: ({ count, source }) => {
      setMessages(prev => prev.map(m =>
        m.id === activeIdRef.current ? {
          ...m, thinking: true, searchingCount: count,
          searchingSources: [...(m.searchingSources || []), source],
        } : m
      ))
    },
    onThoughtSummary: (summary) => {
      setMessages(prev => prev.map(m =>
        m.id === activeIdRef.current ? { ...m, thoughtSummary: summary } : m
      ))
    },
    onSearch: (data) => {
      setMessages(prev => prev.map(m =>
        m.id === activeIdRef.current ? { ...m, researchData: data } : m
      ))
    },
    onSources: (sources) => {
      setMessages(prev => prev.map(m =>
        m.id === activeIdRef.current ? { ...m, sources } : m
      ))
    },
    onContentPatch: (patch) => {
      setMessages(prev => prev.map(m =>
        m.id === activeIdRef.current
          ? { ...m, content: (m.content || '') + patch, thinking: false }
          : m
      ))
    },
    onContentReset: () => {
      setMessages(prev => prev.map(m =>
        m.id === activeIdRef.current ? { ...m, content: '' } : m
      ))
    },
    onRetry: (count) => {
      setMessages(prev => prev.map(m =>
        m.id === activeIdRef.current ? { ...m, retryCount: count } : m
      ))
    },
    onDone: () => {
      setMessages(prev => prev.map(m =>
        m.id === activeIdRef.current ? { ...m, thinking: false } : m
      ))
      activeIdRef.current = null
      setLoading(false)
    },
    onStopped: () => {
      const id = activeIdRef.current
      setMessages(prev => prev.map(m =>
        m.id === id ? { ...m, thinking: false, stopped: true } : m
      ))
      activeIdRef.current = null
      setLoading(false)
    },
    onAudio: (base64Data) => {
      // 通过 ref 调用，确保拿到最新的 playAudio
      playAudioRef.current(base64Data)
    },
  })

  const connectWS = async () => {
    if (wsRef.current?.isConnected) return
    const ws = new ChatWebSocket(makeHandlers())
    try {
      await ws.connect()
      wsRef.current = ws
    } catch {
      setWsStatus('error')
    }
  }

  useEffect(() => {
    connectWS()
    return () => wsRef.current?.disconnect()
  }, [])

  const handleSendMessage = async (message) => {
    if (!message.trim() || loading) return

    setMessages(prev => [...prev, { id: Date.now(), type: 'user', content: message }])
    setLoading(true)

    const assistantId = Date.now() + 1
    activeIdRef.current = assistantId
    setMessages(prev => [...prev, {
      id: assistantId, type: 'assistant', content: '',
      thinking: true, searchingSources: [], searchingCount: 0,
      thoughtSummary: '', researchData: null, retryCount: 0,
    }])

    if (!wsRef.current?.isConnected) {
      await connectWS()
    }

    const sent = wsRef.current?.send(message, ttsLangRef.current, ttsEnabled)
    if (!sent) {
      setMessages(prev => prev.map(m =>
        m.id === assistantId
          ? { ...m, content: '发送失败，请刷新页面重试。', error: true, thinking: false }
          : m
      ))
      activeIdRef.current = null
      setLoading(false)
    }
  }

  const handleStop = () => {
    wsRef.current?.stop()
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4">
        {messages.map(msg => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="px-6 pb-4 pt-3" style={{ borderTop: `1px solid ${theme.border}` }}>
        <InputBox
          onSendMessage={handleSendMessage}
          onStop={handleStop}
          disabled={loading}
          loading={loading}
        />

        {/* 朗读控制按钮已移至消息气泡右下角 */}

        <div className="text-center mt-2 text-xs flex items-center justify-center gap-2" style={{ color: theme.textFaint }}>
          <span
            className="w-1.5 h-1.5 rounded-full inline-block"
            style={{ background: wsStatus === 'connected' ? '#4ade80' : wsStatus === 'error' ? '#f87171' : '#6b7280' }}
          />
          POWERED BY QWEN-TURBO · 深度搜索模式已开启
        </div>
      </div>
    </div>
  )
}
