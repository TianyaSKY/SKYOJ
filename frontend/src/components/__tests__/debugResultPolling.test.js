import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'

vi.mock('@/api/debug', () => ({ getDebugRun: vi.fn() }))
vi.mock('element-plus', () => ({ ElMessage: { warning: vi.fn(), error: vi.fn() } }))
import DebugResultPanel from '../DebugResultPanel.vue'
import { getDebugRun } from '@/api/debug'
import { ElMessage } from 'element-plus'

let wrapper
beforeEach(() => {
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'setInterval', 'clearInterval', 'Date'] })
  vi.clearAllMocks()
  getDebugRun.mockReset()
})
afterEach(() => {
  wrapper?.unmount(); wrapper = undefined
  vi.clearAllTimers(); vi.useRealTimers(); vi.restoreAllMocks()
})
function mountPanel() {
  wrapper = shallowMount(DebugResultPanel, {
    props: { debugRunId: 1 }, global: {
      directives: { loading: () => {} }, stubs: { 'el-card': true, 'el-tag': true },
    },
  })
}
function deferred() {
  let resolve, reject
  const promise = new Promise((res, rej) => { resolve = res; reject = rej })
  return { promise, resolve, reject }
}

describe('调试结果轮询', () => {
  it('初始请求未完成时不叠加轮询', async () => {
    const request = deferred()
    getDebugRun.mockReturnValue(request.promise)
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
    getDebugRun.mockReturnValueOnce(old.promise).mockResolvedValue({ id: 2, status: 'Pending' })
    mountPanel()
    await wrapper.setProps({ debugRunId: 2 })
    await flushPromises()
    old.resolve({ id: 1, status: 'Accepted' })
    await flushPromises()
    expect(wrapper.vm.detail.id).toBe(2)
    await vi.advanceTimersByTimeAsync(1500)
    expect(getDebugRun).toHaveBeenLastCalledWith(2)
    expect(getDebugRun).toHaveBeenCalledTimes(3)
  })

  it('请求失败向用户提示并停止轮询', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    getDebugRun.mockRejectedValue(new Error('网络失败'))
    mountPanel()
    await flushPromises()
    expect(ElMessage.error).toHaveBeenCalledWith('获取调试结果失败，请稍后重试')
    await vi.advanceTimersByTimeAsync(6000)
    expect(getDebugRun).toHaveBeenCalledTimes(1)
  })

  it('卸载后忽略迟到的错误', async () => {
    const request = deferred()
    getDebugRun.mockReturnValue(request.promise)
    mountPanel()
    wrapper.unmount(); wrapper = undefined
    request.reject(new Error('迟到错误'))
    await flushPromises()
    expect(ElMessage.error).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(6000)
    expect(getDebugRun).toHaveBeenCalledTimes(1)
  })

  it('三分钟超时后忽略迟到响应并结束加载', async () => {
    const request = deferred()
    getDebugRun.mockReturnValue(request.promise)
    mountPanel()
    await vi.advanceTimersByTimeAsync(180000)
    expect(ElMessage.warning).toHaveBeenCalledTimes(1)
    expect(wrapper.vm.loading).toBe(false)
    request.resolve({ id: 1, status: 'Accepted' })
    await flushPromises()
    expect(wrapper.vm.detail).toBeNull()
  })

  it('旧请求失败不停止当前运行，当前终态不会再触发超时提示', async () => {
    const old = deferred()
    getDebugRun.mockReturnValueOnce(old.promise)
      .mockResolvedValueOnce({ id: 2, status: 'Pending' })
      .mockResolvedValueOnce({ id: 2, status: 'Accepted' })
    mountPanel()
    await wrapper.setProps({ debugRunId: 2 })
    await flushPromises()
    old.reject(new Error('旧请求失败'))
    await flushPromises()
    expect(ElMessage.error).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(180000)
    expect(wrapper.vm.detail.status).toBe('Accepted')
    expect(getDebugRun).toHaveBeenCalledTimes(3)
    expect(ElMessage.warning).not.toHaveBeenCalled()
  })

  it('清除运行 ID 时取消轮询并清空旧结果', async () => {
    getDebugRun.mockResolvedValue({ id: 1, status: 'Pending' })
    mountPanel()
    await flushPromises()
    await wrapper.setProps({ debugRunId: 0 })
    await vi.advanceTimersByTimeAsync(180000)
    expect(wrapper.vm.detail).toBeNull()
    expect(getDebugRun).toHaveBeenCalledTimes(1)
    expect(ElMessage.warning).not.toHaveBeenCalled()
  })
})
