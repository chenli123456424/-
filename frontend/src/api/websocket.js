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
          const msg = JSON.parse(event.data)
          this._dispatch(msg)
        } catch {
          console.error('[WS] Failed to parse message:', event.data)
        }
      }
    })
  }

  _dispatch({ type, data }) {
    switch (type) {
      case 'thought':         this.handlers.onThought?.(data);        break
      case 'thought_summary': this.handlers.onThoughtSummary?.(data); break
      case 'search':          this.handlers.onSearch?.(data);         break
      case 'content_patch':   this.handlers.onContentPatch?.(data);   break
      case 'retry':           this.handlers.onRetry?.(data);          break
      case 'done':            this.handlers.onDone?.();               break
      case 'stopped':         this.handlers.onStopped?.();            break
      case 'error':           this.handlers.onError?.(data);          break
      default: console.warn('[WS] Unknown type:', type)
    }
  }

  send(message) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ message }))
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
