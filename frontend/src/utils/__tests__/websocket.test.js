// Test 2: websocket.js 自动重连
/**
 * 验证 createSubmissionWS 的自动重连与指数退避逻辑：
 * - 主动 close() 后不触发重连；
 * - 服务端正常关闭 (code=1000/1001) 不触发重连；
 * - 其他关闭码会触发 scheduleReconnect()。
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

// 1) 用 fake timers 控制 setTimeout；
// 2) Mock global WebSocket 为构造器，捕获实例。
class FakeWebSocket {
  constructor (url) {
    this.url = url
    this.readyState = 0
    this.onopen = null
    this.onclose = null
    this.onerror = null
    this.onmessage = null
    FakeWebSocket.lastInstance = this
  }
  close (code, reason) {
    this.readyState = 3
    if (this.onclose) this.onclose({ code: code ?? 1000, reason })
  }
  triggerServerClose (code) {
    this.readyState = 3
    if (this.onclose) this.onclose({ code })
  }
}
FakeWebSocket.lastInstance = null

beforeEach(() => {
  FakeWebSocket.lastInstance = null
  global.WebSocket = FakeWebSocket
  global.window.location.protocol = 'http:'
  global.window.location.host = 'localhost:5173'
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('websocket 自动重连', () => {
  it('主动 close() 后不会触发重连调度', async () => {
    const { createSubmissionWS } = await import('@/utils/websocket')
    const ws = createSubmissionWS(42, 'tok', {})
    ws.connect()
    expect(FakeWebSocket.lastInstance).toBeTruthy()
    ws.close()
    await vi.advanceTimersByTimeAsync(60000)
    expect(FakeWebSocket.lastInstance.readyState).toBe(3)
  })

  it('服务端 1000 正常关闭不会重连', async () => {
    const { createSubmissionWS } = await import('@/utils/websocket')
    const ws = createSubmissionWS(1, 't', {})
    ws.connect()
    const w1 = FakeWebSocket.lastInstance
    expect(w1).toBeTruthy()
    w1.triggerServerClose(1000)
    await vi.advanceTimersByTimeAsync(35000)
    expect(FakeWebSocket.lastInstance).toBe(w1)
  })

  it('服务端 1006 (异常断线) 会触发 scheduleReconnect', async () => {
    const { createSubmissionWS } = await import('@/utils/websocket')
    const onReconnect = vi.fn()
    const ws = createSubmissionWS(2, 't', { onReconnect })
    ws.connect()
    const w1 = FakeWebSocket.lastInstance
    w1.triggerServerClose(1006)
    // 第一次重连延迟 1000ms。
    await vi.advanceTimersByTimeAsync(1500)
    expect(onReconnect).toHaveBeenCalled()
    ws.close()
  })

  it('指数退避：第二次重连延迟 2000ms', async () => {
    const { createSubmissionWS } = await import('@/utils/websocket')
    const onReconnect = vi.fn()
    const ws = createSubmissionWS(3, 't', { onReconnect })
    ws.connect()
    FakeWebSocket.lastInstance.triggerServerClose(1006)
    await vi.advanceTimersByTimeAsync(1500) // 第一次重连
    expect(onReconnect).toHaveBeenCalledTimes(1)
    const w2 = FakeWebSocket.lastInstance
    w2.triggerServerClose(1006)
    await vi.advanceTimersByTimeAsync(2500) // 第二次重连(延迟 2000ms)
    expect(onReconnect).toHaveBeenCalledTimes(2)
    ws.close()
  })

  it('onMessage 正确解析 JSON 数据', async () => {
    const { createSubmissionWS } = await import('@/utils/websocket')
    const onMessage = vi.fn()
    const ws = createSubmissionWS(5, 't', { onMessage })
    ws.connect()
    const w = FakeWebSocket.lastInstance
    w.onmessage({ data: JSON.stringify({ status: 'Accepted', score: 100 }) })
    expect(onMessage).toHaveBeenCalledWith({ status: 'Accepted', score: 100 })
    ws.close()
  })
})
