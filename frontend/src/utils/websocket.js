/** WebSocket 工具：建立、保持、清理 WebSocket 连接。
 *
 * 用法：
 *   import { createSubmissionWS } from '@/utils/websocket'
 *
 *   const ws = createSubmissionWS(submissionId, token, {
 *     onMessage: (data) => { console.log('result:', data) },
 *     onError: (err) => { console.error('ws error:', err) },
 *     onClose: () => { console.log('ws closed') },
 *   })
 *
 *   // 组件卸载时自动清理
 *   ws.connect()
 */

const WS_READY_TIMEOUT_MS = 5000
const RECONNECT_DELAY_MS = 2000

export function createSubmissionWS(submissionId, token, { onMessage, onError, onClose } = {}) {
  let ws = null
  let closed = false

  function buildUrl() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    // WebSocket URL: ws://host/api/submissions/ws/{id}?token=xxx
    return `${protocol}//${host}/api/submissions/ws/${submissionId}?token=${encodeURIComponent(token)}`
  }

  function connect() {
    if (closed) return
    const url = buildUrl()
    ws = new WebSocket(url)

    ws.onopen = () => {
      // 连接建立后等待消息
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage?.(data)
      } catch {
        // 非 JSON 直接透传
        onMessage?.(event.data)
      }
    }

    ws.onerror = (event) => {
      onError?.(event)
    }

    ws.onclose = (event) => {
      if (!closed) {
        onClose?.()
      }
    }
  }

  function close() {
    closed = true
    if (ws) {
      ws.close()
      ws = null
    }
  }

  return { connect, close }
}
