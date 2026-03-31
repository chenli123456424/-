/**
 * WebSocket client for Xiaozhi Digital Assistant
 * Message types from server:
 *   thought         - Planner: search source found
 *   thought_summary - Planner: analysis conclusion
 *   search          - Researcher: structured product data
 *   content_patch   - Synthesizer: streaming token
 *   retry           - Critic: retry count
 *   done            - Stream complete
 *   stopped         - Stream stopped by user
 *   error           - Error occurred
 */

const WS_URL = `ws://${window.location.hostname}:8000/ws/chat`

export class ChatWebSocket {
  constructor(handlers = {}) {
    this.ws = null
    this.handlers = handlers
  }

  connect() {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(WS_URL)

      this.ws.onopen = () => {
        this.handlers.onOpen?.()
        resolve()
      }

      this.ws.onclose = (e) => {
        this.handlers.onClose?.(e)
      }

      this.ws.onerror = (e) => {
        reject(e)
        this.handlers.onError?.('WebSocket connection failed')
      }

      this.ws.onmessage = (event) => {
        try {
          // 音频数据可能很大，先检查是否是 audio 类型再解析
          const raw = event.data
          // 快速检查类型，避免解析超大 JSON
          if (raw.includes('"type":"audio"') || raw.includes('"type": "audio"')) {
            const typeMatch = raw.match(/"type"\s*:\s*"audio"/)
            if (typeMatch) {
              // 提取 data 字段（Base64）
              const dataMatch = raw.match(/"data"\s*:\s*"([^"]+)"/)
              const langMatch = raw.match(/"lang"\s*:\s*"([^"]+)"/)
              if (dataMatch) {
                this.handlers.onAudio?.(dataMatch[1], langMatch?.[1] || 'zh')
                return
              }
            }
          }
          const msg = JSON.parse(raw)
          this._dispatch(msg)
        } catch (e) {
          console.error('[WS] Failed to parse message:', e.message)
        }
      }
    })
  }

  _dispatch({ type, data }) {
    switch (type) {
      case 'thought':         this.handlers.onThought?.(data);        break
      case 'thought_summary': this.handlers.onThoughtSummary?.(data); break
      case 'search':          this.handlers.onSearch?.(data);         break
      case 'sources':         this.handlers.onSources?.(data);        break
      case 'content_patch':   this.handlers.onContentPatch?.(data);   break
      case 'content_reset':   this.handlers.onContentReset?.();        break
      case 'retry':           this.handlers.onRetry?.(data);          break
      case 'done':            this.handlers.onDone?.();               break
      case 'stopped':         this.handlers.onStopped?.();            break
      case 'audio':           
        this.handlers.onAudio?.(msg.data, msg.lang)
        break
      case 'error':           this.handlers.onError?.(data);          break
      default: console.warn('[WS] Unknown type:', type)
    }
  }

  send(message, lang = 'zh', ttsEnabled = true) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ message, lang, tts_enabled: ttsEnabled }))
      return true
    }
    return false
  }

  stop() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'stop' }))
      return true
    }
    return false
  }

  disconnect() {
    this.ws?.close()
    this.ws = null
  }

  get isConnected() {
    return this.ws?.readyState === WebSocket.OPEN
  }
}
