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

const RECONNECT_INITIAL_DELAY_MS = 1000
const RECONNECT_MAX_DELAY_MS = 30000
const TERMINAL_CLOSE_CODES = new Set([1000, 1001, 1008, 4001, 4003, 4004])

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
    if (closed || reconnectTimer !== null) return
    const delay = Math.min(
      RECONNECT_MAX_DELAY_MS,
      RECONNECT_INITIAL_DELAY_MS * 2 ** reconnectAttempt
    )
    reconnectAttempt += 1
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      try {
        onReconnect?.(reconnectAttempt)
      } finally {
        // 页面通知出错不能中断连接恢复；主动关闭仍由 connect() 的守卫处理。
        connect()
      }
    }, delay)
  }

  function connect() {
    if (closed || (ws && ws.readyState < 2)) return
    clearReconnect()
    const url = buildUrl()
    try {
      ws = new WebSocket(url)
    } catch (err) {
      try {
        onError?.(err)
      } finally {
        scheduleReconnect()
      }
      return
    }
    const socket = ws

    socket.onmessage = (event) => {
      if (closed || ws !== socket) return
      // 握手成功仍可能立即掉线；收到消息后才视为恢复，重置退避计数。
      reconnectAttempt = 0
      let data = event.data
      try {
        data = JSON.parse(event.data)
      } catch {
        // 非 JSON 直接透传
      }
      // 回调异常不属于 JSON 解析失败，同一条消息只分发一次。
      onMessage?.(data)
    }

    socket.onerror = (event) => {
      if (closed || ws !== socket) return
      onError?.(event)
    }

    socket.onclose = (event) => {
      // 主动 close() 时 closed=true，不重连、不回调 onClose（避免误以为服务端关闭）。
      if (closed || ws !== socket) {
        return
      }
      ws = null
      // 已完成、无效身份、无权访问和记录不存在均不能靠重连恢复。
      if (TERMINAL_CLOSE_CODES.has(event.code)) closed = true
      try {
        onClose?.(event)
      } finally {
        scheduleReconnect()
      }
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
