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
  it.each([1008, 4001, 4003, 4004])('服务端终止码 %s 不重复重连', async (code) => {
    const { createSubmissionWS } = await import('@/utils/websocket')
    const ws = createSubmissionWS(1, 't')
    ws.connect()
    const first = FakeWebSocket.lastInstance
    first.triggerServerClose(code)
    await vi.advanceTimersByTimeAsync(60000)
    expect(FakeWebSocket.lastInstance).toBe(first)
    ws.close()
  })

  it('消息回调异常不会将同一条 JSON 再作为文本发送', async () => {
    const { createSubmissionWS } = await import('@/utils/websocket')
    const onMessage = vi.fn(() => { throw new Error('回调失败') })
    const ws = createSubmissionWS(1, 't', { onMessage })
    ws.connect()
    expect(() => FakeWebSocket.lastInstance.onmessage({ data: '{"status":"Accepted"}' })).toThrow('回调失败')
    expect(onMessage).toHaveBeenCalledTimes(1)
    ws.close()
  })

  it('重复 connect 不创建并行连接，主动关闭后忽略迟到消息', async () => {
    const { createSubmissionWS } = await import('@/utils/websocket')
    const onMessage = vi.fn()
    const ws = createSubmissionWS(1, 't', { onMessage })
    ws.connect()
    const first = FakeWebSocket.lastInstance
    ws.connect()
    expect(FakeWebSocket.lastInstance).toBe(first)
    ws.close()
    first.onmessage({ data: '{"status":"Accepted"}' })
    expect(onMessage).not.toHaveBeenCalled()
  })

  it('重连后旧连接的消息与关闭事件不影响当前连接', async () => {
    const { createSubmissionWS } = await import('@/utils/websocket')
    const onMessage = vi.fn(), onReconnect = vi.fn()
    const ws = createSubmissionWS(1, 't', { onMessage, onReconnect })
    ws.connect()
    const first = FakeWebSocket.lastInstance
    first.triggerServerClose(1006)
    await vi.advanceTimersByTimeAsync(1000)
    const second = FakeWebSocket.lastInstance
    first.onmessage({ data: '{"status":"Accepted"}' })
    first.triggerServerClose(1006)
    await vi.advanceTimersByTimeAsync(60000)
    expect(onMessage).not.toHaveBeenCalled()
    expect(onReconnect).toHaveBeenCalledTimes(1)
    expect(FakeWebSocket.lastInstance).toBe(second)
    ws.close()
  })

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

it('握手成功后立即断线仍按指数退避，并保持 30 秒上限', async () => {
  const { createSubmissionWS } = await import('@/utils/websocket')
  const onReconnect = vi.fn()
  const ws = createSubmissionWS(1, 't', { onReconnect })
  ws.connect()
  for (const delay of [1000, 2000, 4000, 8000, 16000, 30000, 30000]) {
    const current = FakeWebSocket.lastInstance
    current.readyState = 1
    current.onopen?.()
    current.triggerServerClose(1006)
    const attempts = onReconnect.mock.calls.length
    await vi.advanceTimersByTimeAsync(delay - 1)
    expect(onReconnect).toHaveBeenCalledTimes(attempts)
    expect(FakeWebSocket.lastInstance).toBe(current)
    await vi.advanceTimersByTimeAsync(1)
    expect(onReconnect).toHaveBeenCalledTimes(attempts + 1)
    expect(FakeWebSocket.lastInstance).not.toBe(current)
  }
  ws.close()
})

it('成功收到消息后恢复初始重连等待时间', async () => {
  const { createSubmissionWS } = await import('@/utils/websocket')
  const onReconnect = vi.fn(), onMessage = vi.fn()
  const ws = createSubmissionWS(1, 't', { onReconnect, onMessage })
  ws.connect()
  FakeWebSocket.lastInstance.triggerServerClose(1006)
  await vi.advanceTimersByTimeAsync(1000)
  FakeWebSocket.lastInstance.triggerServerClose(1006)
  await vi.advanceTimersByTimeAsync(2000)
  const recovered = FakeWebSocket.lastInstance
  recovered.onmessage({ data: '{"status":"Accepted","score":100}' })
  expect(onMessage).toHaveBeenCalledOnce()
  recovered.triggerServerClose(1006)
  await vi.advanceTimersByTimeAsync(999)
  expect(onReconnect).toHaveBeenCalledTimes(2)
  await vi.advanceTimersByTimeAsync(1)
  expect(onReconnect).toHaveBeenLastCalledWith(1)
  expect(FakeWebSocket.lastInstance).not.toBe(recovered)
  ws.close()
})

it('重连通知抛错仍建立连接，并保留原始回调异常', async () => {
  const { createSubmissionWS } = await import('@/utils/websocket')
  const error = new Error('reconnect notification failed')
  const ws = createSubmissionWS(1, 't', { onReconnect: () => { throw error } })
  ws.connect()
  const first = FakeWebSocket.lastInstance
  first.triggerServerClose(1006)
  await expect(vi.advanceTimersByTimeAsync(1000)).rejects.toBe(error)
  expect(FakeWebSocket.lastInstance).not.toBe(first)
  ws.close()
})

it('构造连接失败时错误回调抛错也不能停止后续重试', async () => {
  const { createSubmissionWS } = await import('@/utils/websocket')
  let attempts = 0
  global.WebSocket = class extends FakeWebSocket {
    constructor(url) {
      attempts += 1
      if (attempts === 1) throw new Error('constructor failed')
      super(url)
    }
  }
  const error = new Error('error notification failed')
  const ws = createSubmissionWS(1, 't', { onError: () => { throw error } })
  expect(() => ws.connect()).toThrow(error)
  await vi.advanceTimersByTimeAsync(1000)
  expect(attempts).toBe(2)
  expect(FakeWebSocket.lastInstance).toBeTruthy()
  ws.close()
})

it('重连通知主动关闭时不再建立新连接', async () => {
  const { createSubmissionWS } = await import('@/utils/websocket')
  const ws = createSubmissionWS(1, 't', { onReconnect: () => ws.close() })
  ws.connect()
  const first = FakeWebSocket.lastInstance
  first.triggerServerClose(1006)
  await vi.advanceTimersByTimeAsync(60000)
  expect(FakeWebSocket.lastInstance).toBe(first)
})
