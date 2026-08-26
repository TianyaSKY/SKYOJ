/**
 * WebSocket 工具：建立、保持、清理、**自动重连**。
 *
 * 设计要点：
 * - 判题结果通常一次成功即关闭，但服务端/中间链路可能短暂掉线。
 * - 自动重连采用指数退避（1s → 2s → 4s → ... → 30s 上限），避免反复抖动。
 * - 客户端调用 `close()` 后不再重连；浏览器切到后台再回来时由浏览器重发 onclose
 *   触发重连逻辑，无需组件层额外处理。
 * - 主动 onClose 回调只在被调用方（组件）显式调用 close() 时跳过，避免重连抖动误导。
 *
 * 用法：
 *   import { createSubmissionWS } from '@/utils/websocket'
 *
 *   const ws = createSubmissionWS(submissionId, token, {
 *     onMessage: (data) => { console.log('result:', data) },
 *     onError: (err) => { console.error('ws error:', err) },
 *     onClose: () => { console.log('ws closed') },
 *     onReconnect: (attempt) => { console.log('reconnecting', attempt) },
 *   })
 *   ws.connect()
 *   // 组件卸载时
 *   ws.close()
 */

const WS_READY_TIMEOUT_MS = 5000
const RECONNECT_INITIAL_DELAY_MS = 1000
const RECONNECT_MAX_DELAY_MS = 30000

export function createSubmissionWS(submissionId, token, {
  onMessage,
  onError,
  onClose,
  onReconnect,
} = {}) {
  let ws = null
  let closed = false
  let reconnectAttempt = 0
  let reconnectTimer = null

  function buildUrl() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    // WebSocket URL: ws://host/api/submissions/ws/{id}?token=xxx
    return `${protocol}//${host}/api/submissions/ws/${submissionId}?token=${encodeURIComponent(token)}`
  }

  function clearReconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  function scheduleReconnect() {
    if (closed) return
    const delay = Math.min(
      RECONNECT_MAX_DELAY_MS,
      RECONNECT_INITIAL_DELAY_MS * 2 ** reconnectAttempt
    )
    reconnectAttempt += 1
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      onReconnect?.(reconnectAttempt)
      connect()
    }, delay)
  }

  function connect() {
    if (closed) return
    clearReconnect()
    const url = buildUrl()
    try {
      ws = new WebSocket(url)
    } catch (err) {
      onError?.(err)
      scheduleReconnect()
      return
    }

    ws.onopen = () => {
      // 连接建立：成功拿到一次消息就重置重连计数，下次提交走干净的连接。
      reconnectAttempt = 0
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
      // 主动 close() 时 closed=true，不重连、不回调 onClose（避免误以为服务端关闭）。
      if (closed) {
        return
      }
      onClose?.(event)
      // 正常关闭（服务端判题结束主动断开 code=1000）无需重连。
      // 服务端未声明关闭 → 触发重连。1000 是正常关闭，1001 是端点离开，
      // 1005/1006 通常是网络抖动或服务端异常。
      if (event.code === 1000 || event.code === 1001) {
        return
      }
      scheduleReconnect()
    }
  }

  function close() {
    closed = true
    clearReconnect()
    if (ws) {
      try {
        ws.close(1000, 'client closed')
      } catch {
        // 某些异常状态下 ws 已半关闭，忽略。
      }
      ws = null
    }
  }

  return { connect, close }
}
