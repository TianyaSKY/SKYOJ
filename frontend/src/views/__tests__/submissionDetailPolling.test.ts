import type { ComponentPublicInstance } from 'vue'
import type { SubmissionDetailResponse } from '@/types/submission'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { reactive, nextTick } from 'vue'

const state = vi.hoisted(() => ({ route: { params: { id: '1' as string | string[] } } }))
vi.mock('vue-router', () => ({ useRoute: () => state.route }))
vi.mock('@/api/problem', () => ({ getSubmissionDetail: vi.fn() }))
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn(), success: vi.fn() } }))
vi.mock('@guolao/vue-monaco-editor', () => ({ VueMonacoEditor: { template: '<div />' } }))

import SubmissionDetailView from '../SubmissionDetailView.vue'
import { getSubmissionDetail } from '@/api/problem'
import { ElMessage } from 'element-plus'

let wrapper: ReturnType<typeof mountPage> | undefined
function mountedWrapper() {
  if (!wrapper) throw new Error('提交详情未挂载')
  return wrapper
}
// 公共组件类型不公开 setup 状态，声明测试读取的字段。
function setupState() {
  return mountedWrapper().vm as unknown as {
    submission: Pick<SubmissionDetailResponse, 'id' | 'status'>;
    loading: boolean; loadError: boolean; retrySubmission(): Promise<void>;
  }
}
beforeEach(() => {
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'setInterval', 'clearInterval'] })
  vi.clearAllMocks()
  vi.mocked(getSubmissionDetail).mockReset()
  state.route = reactive({ params: { id: '1' } })
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined; vi.clearAllTimers(); vi.useRealTimers() })

function mountPage() {
  const mounted = shallowMount(SubmissionDetailView, {
    global: {
      directives: { loading: () => {} },
      stubs: { ...Object.fromEntries(['el-card', 'el-icon', 'el-tag', 'el-progress', 'el-button', 'el-empty']
        .map(name => [name, true])), 'el-alert': { template: '<div class="load-error"><slot /></div>' } },

    },
  })
  wrapper = mounted
  return mounted
}
function deferred() {
  let resolve!: (value: SubmissionDetailResponse) => void, reject!: (reason: unknown) => void
  const promise = new Promise<SubmissionDetailResponse>((res, rej) => { resolve = res; reject = rej })
  return { promise, resolve, reject }
}
const result = (id: number, status: string): SubmissionDetailResponse => ({ id, status, score: 0, code: '', log: '', language: 'python', exam_id: null, created_at: null, case_results: [] })

describe('提交详情轮询生命周期', () => {
  it('卸载后迟到的 Pending 响应不能重新启动轮询', async () => {
    const request = deferred()
    vi.mocked(getSubmissionDetail).mockReturnValue(request.promise)
    mountPage()
    mountedWrapper().unmount(); wrapper = undefined
    request.resolve(result(1, 'Pending'))
    await flushPromises()
    await vi.advanceTimersByTimeAsync(6000)
    expect(getSubmissionDetail).toHaveBeenCalledTimes(1)
  })

  it('慢请求期间不重叠轮询，终态停止继续查询', async () => {
    const poll = deferred()
    vi.mocked(getSubmissionDetail).mockResolvedValueOnce(result(1, 'Pending')).mockReturnValue(poll.promise)
    mountPage()
    await flushPromises()
    await vi.advanceTimersByTimeAsync(8000)
    expect(getSubmissionDetail).toHaveBeenCalledTimes(2)
    poll.resolve(result(1, 'Accepted'))
    await flushPromises()
    await vi.advanceTimersByTimeAsync(6000)
    expect(getSubmissionDetail).toHaveBeenCalledTimes(2)
    expect(setupState().submission.status).toBe('Accepted')
  })

  it('组件复用时加载新 ID，旧响应不能覆盖新记录', async () => {
    const old = deferred()
    vi.mocked(getSubmissionDetail).mockReturnValueOnce(old.promise).mockResolvedValueOnce(result(2, 'Accepted'))
    mountPage()
    state.route.params.id = '2'
    await nextTick()
    await flushPromises()
    expect(getSubmissionDetail).toHaveBeenLastCalledWith(2)
    old.resolve(result(1, 'Pending'))
    await flushPromises()
    expect(setupState().submission.id).toBe(2)
    await vi.advanceTimersByTimeAsync(6000)
    expect(getSubmissionDetail).toHaveBeenCalledTimes(2)
  })

  it('卸载后迟到的失败不弹出错误', async () => {
    const request = deferred()
    vi.mocked(getSubmissionDetail).mockReturnValue(request.promise)
    mountPage()
    mountedWrapper().unmount(); wrapper = undefined
    request.reject(new Error('页面已经离开'))
    await flushPromises()
    expect(ElMessage.error).not.toHaveBeenCalled()
  })

  it('切换提交后旧请求失败不停止新记录的轮询', async () => {
    const old = deferred()
    vi.mocked(getSubmissionDetail).mockReturnValueOnce(old.promise)
      .mockResolvedValueOnce(result(2, 'Pending')).mockResolvedValueOnce(result(2, 'Accepted'))
    mountPage()
    state.route.params.id = '2'
    await nextTick()
    await flushPromises()
    old.reject(new Error('旧请求失败'))
    await flushPromises()
    expect(ElMessage.error).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(2000)
    expect(getSubmissionDetail).toHaveBeenCalledTimes(3)
    expect(getSubmissionDetail).toHaveBeenLastCalledWith(2)
    expect(setupState().submission.status).toBe('Accepted')
    await vi.advanceTimersByTimeAsync(4000)
    expect(getSubmissionDetail).toHaveBeenCalledTimes(3)
  })

  it('当前轮询失败时提示错误并停止发送请求', async () => {
    vi.mocked(getSubmissionDetail).mockResolvedValueOnce(result(1, 'Pending'))
      .mockRejectedValueOnce(new Error('查询失败'))
    mountPage()
    await flushPromises()
    await vi.advanceTimersByTimeAsync(6000)
    expect(getSubmissionDetail).toHaveBeenCalledTimes(2)
    expect(ElMessage.error).toHaveBeenCalledWith('Failed to load submission details')
  })
})

it('首次加载失败显示可重试状态，重复点击只请求一次', async () => {
  const retry = deferred()
  vi.mocked(getSubmissionDetail).mockRejectedValueOnce(new Error('offline')).mockReturnValueOnce(retry.promise)
  mountPage(); await flushPromises()
  expect(setupState().submission.status).toBe('Load Failed')
  expect(mountedWrapper().find('.load-error').exists()).toBe(true)
  const button = mountedWrapper().findComponent<ComponentPublicInstance>('el-button-stub')
  button.vm.$emit('click'); button.vm.$emit('click')
  await nextTick()
  expect(getSubmissionDetail).toHaveBeenCalledTimes(2)
  expect(setupState().loading).toBe(true)
  retry.resolve(result(1, 'Accepted')); await flushPromises()
  expect(setupState().submission.status).toBe('Accepted')
  expect(mountedWrapper().find('.load-error').exists()).toBe(false)
  expect(setupState().loading).toBe(false)
})
it('轮询失败后重试可恢复 Pending 查询并等待终态', async () => {
  vi.mocked(getSubmissionDetail).mockResolvedValueOnce(result(1, 'Pending'))
    .mockRejectedValueOnce(new Error('offline'))
    .mockResolvedValueOnce(result(1, 'Pending'))
    .mockResolvedValueOnce(result(1, 'Accepted'))
  mountPage(); await flushPromises()
  await vi.advanceTimersByTimeAsync(2000)
  expect(setupState().loadError).toBe(true)
  expect(setupState().submission.status).toBe('Pending')
  await setupState().retrySubmission()
  expect(setupState().loadError).toBe(false)
  await vi.advanceTimersByTimeAsync(2000)
  expect(setupState().submission.status).toBe('Accepted')
  expect(getSubmissionDetail).toHaveBeenCalledTimes(4)
})
it('切换提交时清除旧失败提示，旧重试响应不能覆盖新记录', async () => {
  const old = deferred()
  vi.mocked(getSubmissionDetail).mockRejectedValueOnce(new Error('offline')).mockReturnValueOnce(old.promise)
    .mockResolvedValueOnce(result(2, 'Accepted'))
  mountPage(); await flushPromises()
  const retry = setupState().retrySubmission()
  state.route.params.id = '2'; await nextTick(); await flushPromises()
  expect(setupState().loadError).toBe(false)
  old.reject(new Error('old retry')); await retry
  expect(setupState().submission.id).toBe(2)
  expect(setupState().loadError).toBe(false)
  expect(ElMessage.error).toHaveBeenCalledTimes(1)
})

it.each(['invalid', '0', '-1', ['1']])('非法提交路由 ID %s 不请求或启动轮询', async id => {
  state.route.params.id = id
  mountPage(); await flushPromises()
  await vi.advanceTimersByTimeAsync(6000)
  expect(getSubmissionDetail).not.toHaveBeenCalled()
  expect(setupState().loadError).toBe(true)
  expect(setupState().submission.status).toBe('Load Failed')
})
