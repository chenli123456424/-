import { useState } from 'react'
import { useTheme } from '../ThemeContext'
import { useSpeaking } from '../SpeakingContext'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

function ThoughtPanel({ message, theme }) {
  const [open, setOpen] = useState(true)
  const { searchingSources = [], searchingCount = 0, thoughtSummary = '', thinking } = message

  if (!searchingCount && !thoughtSummary && !thinking) return null

  return (
    <div className="mb-2">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1.5 text-xs mb-2 transition-opacity hover:opacity-80"
        style={{ color: theme.textMuted }}
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
        </svg>
        深度思考过程
        {searchingCount > 0 && (
          <span className="px-1.5 py-0.5 rounded text-xs" style={{ background: theme.tagBg, color: theme.tagColor }}>
            {searchingCount} 个来源
          </span>
        )}
        {thinking && searchingCount === 0 && (
          <span className="flex gap-0.5 ml-1">
            <span className="w-1 h-1 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '0ms' }}></span>
            <span className="w-1 h-1 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '150ms' }}></span>
            <span className="w-1 h-1 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '300ms' }}></span>
          </span>
        )}
        <span style={{ fontSize: 10 }}>{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="rounded-xl px-3 py-3 space-y-2" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>

          {/* 实时来源列表 */}
          {searchingSources.map((s, i) => (
            <div key={i} className="flex gap-2.5 items-start text-xs">
              <img
                src={`https://www.google.com/s2/favicons?domain=${s.domain}&sz=16`}
                alt=""
                className="w-4 h-4 rounded mt-0.5 shrink-0"
                onError={e => { e.target.style.display = 'none' }}
              />
              <div className="flex-1 min-w-0">
                <div className="font-medium truncate" style={{ color: theme.text }}>{s.title}</div>
                <div className="mt-0.5 leading-relaxed" style={{ color: theme.textMuted }}>
                  {/* 流式文字效果：逐字显示摘要 */}
                  正在对第 {i + 1} 个网站进行搜索并解析，解析得出：{s.summary}
                </div>
                <div className="mt-0.5" style={{ color: theme.textFaint }}>{s.domain}</div>
              </div>
            </div>
          ))}

          {/* 正在搜索中的动画占位（还没拿到来源时） */}
          {thinking && searchingCount === 0 && (
            <div className="text-xs" style={{ color: theme.textMuted }}>正在搜索相关资料...</div>
          )}

          {/* 分析总结 */}
          {thoughtSummary && (
            <div
              className="text-xs leading-relaxed pt-2"
              style={{ color: theme.textMuted, borderTop: `1px solid ${theme.border}` }}
            >
              {thoughtSummary}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// 清理正文中的内联引用角标和"参考来源"段落
function cleanContent(content) {
  return content
    // 去掉 [1] [2][3] 这类角标
    .replace(/\[\d+\](\[\d+\])*/g, '')
    // 去掉结尾的"参考来源"/"参考文献"整段（从该标题到文末）
    .replace(/\n*#{0,3}\s*(参考来源|参考文献|References|来源)[^\n]*\n[\s\S]*$/i, '')
    .trimEnd()
}

function SourcesBar({ sources, theme }) {
  if (!sources?.length) return null
  return (
    <div className="flex flex-wrap items-center gap-1.5 mt-2 pt-2" style={{ borderTop: `1px solid ${theme.border}` }}>
      <span className="text-xs shrink-0" style={{ color: theme.textFaint }}>参考来源</span>
      {sources.map((s, i) => {
        const domain = s.domain || (s.url ? new URL(s.url).hostname.replace('www.', '') : null)
        const label = domain || s.title || `来源${i + 1}`
        const href = s.url || '#'
        return (
          <a
            key={i}
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 px-2 py-0.5 rounded-full text-xs transition-opacity hover:opacity-80"
            style={{ background: theme.tagBg, color: theme.tagColor, border: `1px solid ${theme.border}` }}
          >
            <img
              src={`https://www.google.com/s2/favicons?domain=${domain}&sz=16`}
              alt=""
              className="w-3 h-3 rounded-sm"
              onError={e => { e.target.style.display = 'none' }}
            />
            {label}
          </a>
        )
      })}
    </div>
  )
}

function ResearchPanel({ data, theme }) {
  const [open, setOpen] = useState(false)
  const items = data?.items || data?.products || []
  if (!items.length) return null

  // 收集所有出现过的字段（排除 source）
  const allKeys = [...new Set(items.flatMap(item => Object.keys(item).filter(k => k !== 'source')))]

  return (
    <div className="mb-2">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1.5 text-xs mb-1 transition-opacity hover:opacity-80"
        style={{ color: theme.textMuted }}
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
        </svg>
        搜索数据 ({items.length} 条)
        <span style={{ fontSize: 10 }}>{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div
          className="rounded-xl px-3 py-2 text-xs overflow-x-auto"
          style={{ background: theme.card, border: `1px solid ${theme.border}`, color: theme.textMuted }}
        >
          <table className="w-full text-left" style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${theme.border}` }}>
                {allKeys.map(k => (
                  <th key={k} className="py-1 pr-3 font-medium whitespace-nowrap" style={{ color: theme.text }}>{k}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map((item, i) => (
                <tr key={i} style={{ borderBottom: `1px solid ${theme.border}20` }}>
                  {allKeys.map(k => (
                    <td key={k} className="py-1 pr-3 align-top">{item[k] ?? '-'}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {data.summary && (
            <div className="mt-2 pt-2" style={{ borderTop: `1px solid ${theme.border}` }}>
              {data.summary}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function MessageBubble({ message }) {
  const { theme } = useTheme()
  const { isSpeaking, stopAudio } = useSpeaking()
  const isUser = message.type === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div
          className="max-w-xs md:max-w-md px-4 py-2.5 rounded-2xl rounded-br-sm text-sm leading-relaxed"
          style={{ background: theme.userBubble, color: '#fff' }}
        >
          {message.content}
        </div>
      </div>
    )
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-xl w-full">
        {/* 思考链面板 */}
        <ThoughtPanel message={message} theme={theme} />

        {/* 研究数据面板 */}
        <ResearchPanel data={message.researchData} theme={theme} />

        {/* 主回答气泡 */}
        <div
          className="relative px-4 py-3 rounded-2xl rounded-bl-sm text-sm leading-relaxed"
          style={{
            background: message.error ? (theme.card === '#ffffff' ? '#fff0f0' : '#2d1b1b') : theme.card,
            color: message.error ? '#f85149' : theme.text,
            border: `1px solid ${message.error ? '#f8514940' : theme.border}`,
            wordBreak: 'break-word'
          }}
        >
          {message.thinking && !message.content && !message.stopped ? (
            <span className="flex items-center gap-2" style={{ color: theme.textMuted }}>
              <span className="flex gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '0ms' }}></span>
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '150ms' }}></span>
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '300ms' }}></span>
              </span>
              思考中...
            </span>
          ) : message.stopped && !message.content ? (
            <span style={{ color: theme.textMuted }}>⏹ 回复已中断</span>
          ) : message.error ? (
            message.content
          ) : (            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                h1: ({children}) => <h1 className="text-lg font-bold mt-3 mb-1" style={{ color: theme.text }}>{children}</h1>,
                h2: ({children}) => <h2 className="text-base font-bold mt-3 mb-1" style={{ color: theme.text }}>{children}</h2>,
                h3: ({children}) => <h3 className="text-sm font-bold mt-2 mb-1" style={{ color: theme.text }}>{children}</h3>,
                p: ({children}) => <p className="mb-2 leading-relaxed">{children}</p>,
                strong: ({children}) => <strong className="font-semibold" style={{ color: theme.text }}>{children}</strong>,
                em: ({children}) => <em className="italic">{children}</em>,
                ul: ({children}) => <ul className="list-disc list-inside mb-2 space-y-0.5">{children}</ul>,
                ol: ({children}) => <ol className="list-decimal list-inside mb-2 space-y-0.5">{children}</ol>,
                li: ({children}) => <li className="leading-relaxed">{children}</li>,
                code: ({inline, children}) => inline
                  ? <code className="px-1 py-0.5 rounded text-xs font-mono" style={{ background: theme.inputBorder, color: '#e06c75' }}>{children}</code>
                  : <pre className="p-3 rounded-lg text-xs font-mono overflow-x-auto mb-2" style={{ background: theme.bg }}><code>{children}</code></pre>,
                table: ({children}) => (
                  <div className="overflow-x-auto mb-2">
                    <table className="w-full text-xs border-collapse">{children}</table>
                  </div>
                ),
                thead: ({children}) => <thead>{children}</thead>,
                th: ({children}) => (
                  <th className="px-3 py-1.5 text-left font-semibold" style={{ borderBottom: `2px solid ${theme.border}`, color: theme.text }}>{children}</th>
                ),
                td: ({children}) => (
                  <td className="px-3 py-1.5" style={{ borderBottom: `1px solid ${theme.border}20` }}>{children}</td>
                ),
                hr: () => <hr className="my-3" style={{ borderColor: theme.border }} />,
                blockquote: ({children}) => (
                  <blockquote className="pl-3 my-2 italic" style={{ borderLeft: `3px solid ${theme.tagBorder}`, color: theme.textMuted }}>{children}</blockquote>
                ),
              }}
            >
              {cleanContent(message.content)}
            </ReactMarkdown>
          )}
          {/* 来源标签 */}
          {!message.thinking && message.sources?.length > 0 && (
            <SourcesBar sources={message.sources} theme={theme} />
          )}
          {/* 朗读控制按钮 - 右下角 */}
          {!message.thinking && !message.error && message.content && (
            <div className="flex justify-end mt-2">
              {isSpeaking ? (
                <button
                  onClick={stopAudio}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs transition-all"
                  style={{ background: 'rgba(248,81,73,0.12)', color: '#f87171', border: '1px solid rgba(248,81,73,0.3)' }}
                >
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor">
                    <rect x="4" y="4" width="16" height="16" rx="2"/>
                  </svg>
                  停止朗读
                </button>
              ) : (
                <div
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs"
                  style={{ color: theme.textFaint }}
                >
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
                    <path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
                  </svg>
                  朗读
                </div>
              )}
            </div>
          )}
        </div>

        {/* 中断提示 */}
        {message.stopped && message.content && (
          <div className="mt-1 text-xs" style={{ color: theme.textFaint }}>⏹ 回复已中断</div>
        )}

        {/* 重试次数提示 */}
        {message.retryCount > 0 && (
          <div className="mt-1 text-xs" style={{ color: theme.textFaint }}>
            Critic 审核重试了 {message.retryCount} 次
          </div>
        )}
      </div>
    </div>
  )
}
