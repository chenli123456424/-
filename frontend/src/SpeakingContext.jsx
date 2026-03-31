import { createContext, useContext, useState, useRef } from 'react'

export const SpeakingContext = createContext()

export function SpeakingProvider({ children }) {
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [ttsLang, setTtsLang] = useState('zh')
  const [ttsEnabled, setTtsEnabled] = useState(true)
  const audioRef = useRef(null)        // 当前播放的 Audio 对象
  const audioObjRef = useRef(null)     // 用于暂停/继续控制

  const stopAudio = () => {
    if (audioObjRef.current) {
      audioObjRef.current.pause()
      audioObjRef.current.currentTime = 0
      audioObjRef.current = null
    }
    setIsSpeaking(false)
  }

  return (
    <SpeakingContext.Provider value={{
      isSpeaking, setIsSpeaking,
      ttsLang, setTtsLang,
      ttsEnabled, setTtsEnabled,
      audioRef, audioObjRef,
      stopAudio,
    }}>
      {children}
      <audio ref={audioRef} style={{ display: 'none' }} />
    </SpeakingContext.Provider>
  )
}

export const useSpeaking = () => useContext(SpeakingContext)
