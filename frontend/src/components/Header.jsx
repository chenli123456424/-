import { useTheme } from '../ThemeContext'

export default function Header({ onSettingsClick, settingsOpen }) {
  const { theme, mode, toggle } = useTheme()

  return (
    <header
      className="flex items-center justify-between px-5 py-3 shrink-0"
      style={{ background: theme.panel, borderBottom: `1px solid ${theme.border}` }}
    >
      <div className="flex items-center gap-3">
        <div
          className="w-9 h-9 rounded-xl flex items-center justify-center text-lg"
          style={{ background: 'linear-gradient(135deg, #1d6fe8, #7c3aed)' }}
        >
          🤖
        </div>
        <div>
          <div className="font-bold text-sm leading-tight" style={{ color: theme.text }}>小智数码助手</div>
          <div className="flex items-center gap-1 mt-0.5">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 inline-block"></span>
            <span className="text-green-400 text-xs">AI 智能体在线</span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {/* 主题切换按钮 */}
        <button
          onClick={toggle}
          className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors text-base"
          style={{ color: theme.textMuted, background: 'transparent' }}
          onMouseEnter={e => e.currentTarget.style.background = theme.border}
          onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
          title={mode === 'dark' ? '切换亮色' : '切换暗色'}
        >
          {mode === 'dark' ? '☀️' : '🌙'}
        </button>

        {/* 设置图标 */}
        <button
          onClick={onSettingsClick}
          className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors"
          style={{
            color: settingsOpen ? '#1d6fe8' : theme.textMuted,
            background: settingsOpen ? 'rgba(29,111,232,0.12)' : 'transparent',
          }}
          onMouseEnter={e => { if (!settingsOpen) e.currentTarget.style.background = theme.border }}
          onMouseLeave={e => { if (!settingsOpen) e.currentTarget.style.background = 'transparent' }}
          title="设置"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
          </svg>
        </button>
      </div>
    </header>
  )
}
