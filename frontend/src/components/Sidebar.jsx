import { useTheme } from '../ThemeContext'
import { useSpeaking } from '../SpeakingContext'

const DIALECTS = [
  { key: 'zh',        label: '普通话',  desc: '标准、清晰的普通话' },
  { key: 'minnan',    label: '闽南语',  desc: '地道、亲切的闽南方言' },
  { key: 'dongbei',   label: '东北话',  desc: '豪爽、幽默的东北方言' },
  { key: 'shaanxi',   label: '陕西话',  desc: '淳朴、厚重的陕西话' },
]

export default function Sidebar({ settingsOpen, onCloseSettings }) {
  const { theme } = useTheme()
  const { isSpeaking, ttsLang, setTtsLang, ttsEnabled, setTtsEnabled } = useSpeaking()

  return (
    <aside
      className="shrink-0 relative overflow-hidden"
      style={{ width: '30%', background: theme.panel, borderRight: `1px solid ${theme.border}` }}
    >
      {/* ── 主面板：数字人 ── */}
      <div
        className="absolute inset-0 flex flex-col items-center py-8 px-4 gap-4 transition-transform duration-300 ease-in-out"
        style={{ transform: settingsOpen ? 'translateX(-100%)' : 'translateX(0)' }}
      >
        {/* 数字人矩形框 */}
        <div
          className="flex flex-col items-center justify-center rounded-2xl relative overflow-hidden"
          style={{
            width: '85%',
            height: '420px',
            background: theme.avatarBg,
            border: `1px solid ${isSpeaking ? '#1d6fe8' : theme.avatarBorder}`,
            transition: 'border-color 0.3s',
          }}
        >
          {isSpeaking && (
            <div
              className="absolute inset-0 rounded-2xl pointer-events-none"
              style={{
                boxShadow: '0 0 30px 8px rgba(29,111,232,0.35)',
                animation: 'pulse 1.2s ease-in-out infinite',
              }}
            />
          )}
          <svg
            width="100" height="120" viewBox="0 0 24 24" fill="none"
            style={{ transform: isSpeaking ? 'scale(1.04)' : 'scale(1)', transition: 'transform 0.3s ease' }}
          >
            <circle cx="12" cy="8" r="4" fill="#4a90d9" />
            <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" fill="#4a90d9" />
          </svg>
          {isSpeaking && (
            <div className="flex items-end gap-0.5 mt-3" style={{ height: 20 }}>
              {[1, 2, 3, 4, 5].map(i => (
                <div
                  key={i}
                  className="w-1 rounded-full"
                  style={{
                    background: '#4a90d9',
                    height: `${8 + Math.random() * 12}px`,
                    animation: `wave ${0.4 + i * 0.1}s ease-in-out infinite alternate`,
                  }}
                />
              ))}
            </div>
          )}
        </div>

        {/* 在线标签 */}
        <div
          className="px-3 py-0.5 rounded-full text-xs font-medium flex items-center gap-1.5"
          style={{ background: theme.tagBg, color: theme.tagColor, border: `1px solid ${theme.tagBorder}` }}
        >
          {isSpeaking && <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse inline-block" />}
          {isSpeaking ? '正在朗读...' : '小智在线'}
        </div>

        <div className="text-center">
          <div className="font-bold text-lg" style={{ color: theme.text }}>你好，我是小智</div>
          <div className="text-xs mt-1 leading-relaxed" style={{ color: theme.textMuted }}>
            我可以为您提供深度搜索、方言朗读以及智能问答服务。
          </div>
        </div>
      </div>

      {/* ── 设置面板 ── */}
      <div
        className="absolute inset-0 flex flex-col py-6 px-5 transition-transform duration-300 ease-in-out overflow-y-auto"
        style={{
          transform: settingsOpen ? 'translateX(0)' : 'translateX(100%)',
          background: theme.panel,
        }}
      >
        {/* 标题栏 */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2" style={{ color: theme.text }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M4 6h16M4 12h16M4 18h7"/>
            </svg>
            <span className="font-semibold text-sm">朗读语言设置</span>
          </div>
          <button
            onClick={onCloseSettings}
            className="text-xs px-2 py-1 rounded-lg transition-colors"
            style={{ color: '#1d6fe8', background: 'rgba(29,111,232,0.1)' }}
          >
            返回
          </button>
        </div>

        {/* 朗读开关 */}
        <div
          className="flex items-center justify-between rounded-xl px-4 py-3 mb-4"
          style={{ background: theme.dialectBg, border: `1px solid ${theme.dialectBorder}` }}
        >
          <div>
            <div className="text-sm font-medium" style={{ color: theme.text }}>朗读功能</div>
            <div className="text-xs mt-0.5" style={{ color: theme.textMuted }}>
              {ttsEnabled ? '已开启自动朗读' : '已关闭自动朗读'}
            </div>
          </div>
          {/* Toggle switch */}
          <button
            onClick={() => setTtsEnabled(v => !v)}
            className="relative w-11 h-6 rounded-full transition-colors duration-200 focus:outline-none"
            style={{ background: ttsEnabled ? '#1d6fe8' : '#4b5563' }}
          >
            <span
              className="absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform duration-200"
              style={{ transform: ttsEnabled ? 'translateX(20px)' : 'translateX(0)' }}
            />
          </button>
        </div>

        {/* 方言选择 */}
        <div className="text-xs font-medium mb-2" style={{ color: theme.textMuted }}>选择方言</div>
        <div className="flex flex-col gap-2">
          {DIALECTS.map(d => (
            <button
              key={d.key}
              onClick={() => setTtsLang(d.key)}
              className="flex items-center justify-between rounded-xl px-4 py-3 text-left transition-all"
              style={{
                background: ttsLang === d.key ? 'rgba(29,111,232,0.15)' : theme.dialectBg,
                border: `1px solid ${ttsLang === d.key ? '#1d6fe8' : theme.dialectBorder}`,
              }}
            >
              <div>
                <div className="text-sm font-medium" style={{ color: theme.text }}>{d.label}</div>
                <div className="text-xs mt-0.5" style={{ color: theme.textMuted }}>{d.desc}</div>
              </div>
              {ttsLang === d.key && (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#1d6fe8" strokeWidth="2.5">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* CSS 动画 */}
      <style>{`
        @keyframes wave {
          from { transform: scaleY(0.4); }
          to   { transform: scaleY(1.2); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 0.4; }
          50%       { opacity: 0.9; }
        }
      `}</style>
    </aside>
  )
}
