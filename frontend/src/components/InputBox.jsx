import { useState } from 'react'
import { useTheme } from '../ThemeContext'

export default function InputBox({ onSendMessage, onStop, disabled, loading }) {
  const { theme } = useTheme()
  const [input, setInput] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (input.trim() && !disabled) {
      onSendMessage(input)
      setInput('')
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !disabled) handleSubmit(e)
  }

  const canSend = !disabled && input.trim()

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-3">
      <div
        className="flex-1 flex items-center gap-2 px-4 py-2.5 rounded-2xl"
        style={{ background: theme.input, border: `1px solid ${theme.inputBorder}` }}
      >
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入您的问题，小智为您深度思考..."
          disabled={disabled}
          className="flex-1 bg-transparent outline-none text-sm"
          style={{ color: theme.text }}
        />
        <button
          type="button"
          className="shrink-0 transition-colors"
          style={{ color: theme.textMuted }}
          onMouseEnter={e => e.currentTarget.style.color = theme.text}
          onMouseLeave={e => e.currentTarget.style.color = theme.textMuted}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
            <line x1="12" y1="19" x2="12" y2="23"/>
            <line x1="8" y1="23" x2="16" y2="23"/>
          </svg>
        </button>
      </div>

      {/* 发送 / 停止 按钮 */}
      {loading ? (
        <button
          type="button"
          onClick={onStop}
          className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 transition-all"
          style={{ background: '#dc2626', color: '#fff', border: '1px solid #dc2626' }}
          title="停止回答"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <rect x="4" y="4" width="16" height="16" rx="2"/>
          </svg>
        </button>
      ) : (
        <button
          type="submit"
          disabled={!canSend}
          className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 transition-all"
          style={{
            background: canSend ? theme.sendBtn : theme.input,
            color: canSend ? '#fff' : theme.textMuted,
            border: `1px solid ${theme.inputBorder}`
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </button>
      )}
    </form>
  )
}
