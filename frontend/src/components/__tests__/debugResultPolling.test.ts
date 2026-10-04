import type { DebugRunResponse } from '@/types/debug'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'

vi.mock('@/api/debug', () => ({ getDebugRun: vi.fn() }))
vi.mock('element-plus', () => ({ ElMessage: { warning: vi.fn(), error: vi.fn() } }))
import DebugResultPanel from '../DebugResultPanel.vue'
import { getDebugRun } from '@/api/debug'
import { ElMessage } from 'element-plus'

let wrapper: ReturnType<typeof mountPanel> | undefined
beforeEach(() => {
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'setInterval', 'clearInterval', 'Date'] })
  vi.clearAllMocks()
  vi.mocked(getDebugRun).mockReset()
})
afterEach(() => {
  wrapper?.unmount(); wrapper = undefined
  vi.clearAllTimers(); vi.useRealTimers(); vi.restoreAllMocks()
})
function mountPanel() {
  const mounted = shallowMount(DebugResultPanel, {
    props: { debugRunId: 1 }, global: {
      directives: { loading: () => {} }, stubs: { 'el-card': true, 'el-tag': true },
    },
  })
  wrapper = mounted
  return mounted
}
const debugResponse = (value: Partial<DebugRunResponse>): DebugRunResponse => ({
  id: 1, status: 'Pending', language: 'python', case_name: null, input: null, expected_output: null,
  actual_output: null, error_output: null, time_used_ms: null, memory_used_kb: null,
  created_at: null, finished_at: null, problem_id: 1, exam_id: null, ...value,
})
function deferred() {
  let resolve!: (value: Partial<DebugRunResponse>) => void
  let reject!: (error: unknown) => void
  const promise = new Promise<DebugRunResponse>((yes, no) => {
    resolve = value => yes(debugResponse(value)); reject = no
  })
  return { promise, resolve, reject }
}
function current() {
  if (!wrapper) throw new Error('调试面板未挂载')
  return wrapper
}
// 测试工具可读取 setup 状态，但 Vue 公共组件类型不公开这些内部字段。
function setupState() {
  return current().vm as unknown as { detail: DebugRunResponse | null; loading: boolean }
}

describe('调试结果轮询', () => {
  it('初始请求未完成时不叠加轮询', async () => {
    const request = deferred()
    vi.mocked(getDebugRun).mockReturnValue(request.promise)
    mountPanel()
    await vi.advanceTimersByTimeAsync(6000)
    expect(getDebugRun).toHaveBeenCalledTimes(1)
    request.resolve({ status: 'Accepted' })
    await flushPromises()
    await vi.advanceTimersByTimeAsync(180000)
    expect(getDebugRun).toHaveBeenCalledTimes(1)
    expect(ElMessage.warning).not.toHaveBeenCalled()
  })

  it('新调试运行开始后，旧结果不能覆盖或停止新轮询', async () => {
    const old = deferred()
    vi.mocked(getDebugRun).mockReturnValueOnce(old.promise).mockResolvedValue(debugResponse({ id: 2, status: 'Pending' }))
    mountPanel()
    await current().setProps({ debugRunId: 2 })
    await flushPromises()
    old.resolve({ id: 1, status: 'Accepted' })
    await flushPromises()
    expect(setupState().detail?.id).toBe(2)
    await vi.advanceTimersByTimeAsync(1500)
    expect(getDebugRun).toHaveBeenLastCalledWith(2)
    expect(getDebugRun).toHaveBeenCalledTimes(3)
  })

  it('请求失败向用户提示并停止轮询', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    vi.mocked(getDebugRun).mockRejectedValue(new Error('网络失败'))
    mountPanel()
    await flushPromises()
    expect(ElMessage.error).toHaveBeenCalledWith('获取调试结果失败，请稍后重试')
    await vi.advanceTimersByTimeAsync(6000)
    expect(getDebugRun).toHaveBeenCalledTimes(1)
  })

  it('卸载后忽略迟到的错误', async () => {
    const request = deferred()
    vi.mocked(getDebugRun).mockReturnValue(request.promise)
    mountPanel()
    current().unmount(); wrapper = undefined
    request.reject(new Error('迟到错误'))
    await flushPromises()
    expect(ElMessage.error).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(6000)
    expect(getDebugRun).toHaveBeenCalledTimes(1)
  })

  it('三分钟超时后忽略迟到响应并结束加载', async () => {
    const request = deferred()
    vi.mocked(getDebugRun).mockReturnValue(request.promise)
    mountPanel()
    await vi.advanceTimersByTimeAsync(180000)
    expect(ElMessage.warning).toHaveBeenCalledTimes(1)
    expect(setupState().loading).toBe(false)
    request.resolve({ id: 1, status: 'Accepted' })
    await flushPromises()
    expect(setupState().detail).toBeNull()
  })

  it('旧请求失败不停止当前运行，当前终态不会再触发超时提示', async () => {
    const old = deferred()
    vi.mocked(getDebugRun).mockReturnValueOnce(old.promise)
      .mockResolvedValueOnce(debugResponse({ id: 2, status: 'Pending' }))
      .mockResolvedValueOnce(debugResponse({ id: 2, status: 'Accepted' }))
    mountPanel()
    await current().setProps({ debugRunId: 2 })
    await flushPromises()
    old.reject(new Error('旧请求失败'))
    await flushPromises()
    expect(ElMessage.error).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(180000)
    expect(setupState().detail?.status).toBe('Accepted')
    expect(getDebugRun).toHaveBeenCalledTimes(3)
    expect(ElMessage.warning).not.toHaveBeenCalled()
  })

  it('清除运行 ID 时取消轮询并清空旧结果', async () => {
    vi.mocked(getDebugRun).mockResolvedValue(debugResponse({ id: 1, status: 'Pending' }))
    mountPanel()
    await flushPromises()
    await current().setProps({ debugRunId: 0 })
    await vi.advanceTimersByTimeAsync(180000)
    expect(setupState().detail).toBeNull()
    expect(getDebugRun).toHaveBeenCalledTimes(1)
    expect(ElMessage.warning).not.toHaveBeenCalled()
  })
})
