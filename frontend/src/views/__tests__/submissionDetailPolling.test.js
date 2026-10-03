import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { reactive, nextTick } from 'vue'

const state = vi.hoisted(() => ({ route: null }))
vi.mock('vue-router', () => ({ useRoute: () => state.route }))
vi.mock('@/api/problem', () => ({ getSubmissionDetail: vi.fn() }))
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn(), success: vi.fn() } }))
vi.mock('@guolao/vue-monaco-editor', () => ({ VueMonacoEditor: { template: '<div />' } }))

import SubmissionDetailView from '../SubmissionDetailView.vue'
import { getSubmissionDetail } from '@/api/problem'
import { ElMessage } from 'element-plus'

let wrapper
beforeEach(() => {
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'setInterval', 'clearInterval'] })
  vi.clearAllMocks()
  getSubmissionDetail.mockReset()
  state.route = reactive({ params: { id: '1' } })
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined; vi.clearAllTimers(); vi.useRealTimers() })

function mountPage() {
  wrapper = shallowMount(SubmissionDetailView, {
    global: {
      directives: { loading: () => {} },
      stubs: { ...Object.fromEntries(['el-card', 'el-icon', 'el-tag', 'el-progress', 'el-button', 'el-empty']
        .map(name => [name, true])), 'el-alert': { template: '<div class="load-error"><slot /></div>' } },

    },
  })
}
function deferred() {
  let resolve, reject
  const promise = new Promise((res, rej) => { resolve = res; reject = rej })
  return { promise, resolve, reject }
}
const result = (id, status) => ({ id, status, score: 0, code: '', log: '' })

describe('提交详情轮询生命周期', () => {
  it('卸载后迟到的 Pending 响应不能重新启动轮询', async () => {
    const request = deferred()
    getSubmissionDetail.mockReturnValue(request.promise)
    mountPage()
    wrapper.unmount(); wrapper = undefined
    request.resolve(result(1, 'Pending'))
    await flushPromises()
    await vi.advanceTimersByTimeAsync(6000)
    expect(getSubmissionDetail).toHaveBeenCalledTimes(1)
  })

  it('慢请求期间不重叠轮询，终态停止继续查询', async () => {
    const poll = deferred()
    getSubmissionDetail.mockResolvedValueOnce(result(1, 'Pending')).mockReturnValue(poll.promise)
    mountPage()
    await flushPromises()
    await vi.advanceTimersByTimeAsync(8000)
    expect(getSubmissionDetail).toHaveBeenCalledTimes(2)
    poll.resolve(result(1, 'Accepted'))
    await flushPromises()
    await vi.advanceTimersByTimeAsync(6000)
    expect(getSubmissionDetail).toHaveBeenCalledTimes(2)
    expect(wrapper.vm.submission.status).toBe('Accepted')
  })

  it('组件复用时加载新 ID，旧响应不能覆盖新记录', async () => {
    const old = deferred()
    getSubmissionDetail.mockReturnValueOnce(old.promise).mockResolvedValueOnce(result(2, 'Accepted'))
    mountPage()
    state.route.params.id = '2'
    await nextTick()
    await flushPromises()
    expect(getSubmissionDetail).toHaveBeenLastCalledWith('2')
    old.resolve(result(1, 'Pending'))
    await flushPromises()
    expect(wrapper.vm.submission.id).toBe(2)
    await vi.advanceTimersByTimeAsync(6000)
    expect(getSubmissionDetail).toHaveBeenCalledTimes(2)
  })

  it('卸载后迟到的失败不弹出错误', async () => {
    const request = deferred()
    getSubmissionDetail.mockReturnValue(request.promise)
    mountPage()
    wrapper.unmount(); wrapper = undefined
    request.reject(new Error('页面已经离开'))
    await flushPromises()
    expect(ElMessage.error).not.toHaveBeenCalled()
  })

  it('切换提交后旧请求失败不停止新记录的轮询', async () => {
    const old = deferred()
    getSubmissionDetail.mockReturnValueOnce(old.promise)
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
    expect(getSubmissionDetail).toHaveBeenLastCalledWith('2')
    expect(wrapper.vm.submission.status).toBe('Accepted')
    await vi.advanceTimersByTimeAsync(4000)
    expect(getSubmissionDetail).toHaveBeenCalledTimes(3)
  })

  it('当前轮询失败时提示错误并停止发送请求', async () => {
    getSubmissionDetail.mockResolvedValueOnce(result(1, 'Pending'))
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
  getSubmissionDetail.mockRejectedValueOnce(new Error('offline')).mockReturnValueOnce(retry.promise)
  mountPage(); await flushPromises()
  expect(wrapper.vm.submission.status).toBe('Load Failed')
  expect(wrapper.find('.load-error').exists()).toBe(true)
  const button = wrapper.findComponent('el-button-stub')
  button.vm.$emit('click'); button.vm.$emit('click')
  await nextTick()
  expect(getSubmissionDetail).toHaveBeenCalledTimes(2)
  expect(wrapper.vm.loading).toBe(true)
  retry.resolve(result(1, 'Accepted')); await flushPromises()
  expect(wrapper.vm.submission.status).toBe('Accepted')
  expect(wrapper.find('.load-error').exists()).toBe(false)
  expect(wrapper.vm.loading).toBe(false)
})
it('轮询失败后重试可恢复 Pending 查询并等待终态', async () => {
  getSubmissionDetail.mockResolvedValueOnce(result(1, 'Pending'))
    .mockRejectedValueOnce(new Error('offline'))
    .mockResolvedValueOnce(result(1, 'Pending'))
    .mockResolvedValueOnce(result(1, 'Accepted'))
  mountPage(); await flushPromises()
  await vi.advanceTimersByTimeAsync(2000)
  expect(wrapper.vm.loadError).toBe(true)
  expect(wrapper.vm.submission.status).toBe('Pending')
  await wrapper.vm.retrySubmission()
  expect(wrapper.vm.loadError).toBe(false)
  await vi.advanceTimersByTimeAsync(2000)
  expect(wrapper.vm.submission.status).toBe('Accepted')
  expect(getSubmissionDetail).toHaveBeenCalledTimes(4)
})
it('切换提交时清除旧失败提示，旧重试响应不能覆盖新记录', async () => {
  const old = deferred()
  getSubmissionDetail.mockRejectedValueOnce(new Error('offline')).mockReturnValueOnce(old.promise)
    .mockResolvedValueOnce(result(2, 'Accepted'))
  mountPage(); await flushPromises()
  const retry = wrapper.vm.retrySubmission()
  state.route.params.id = '2'; await nextTick(); await flushPromises()
  expect(wrapper.vm.loadError).toBe(false)
  old.reject(new Error('old retry')); await retry
  expect(wrapper.vm.submission.id).toBe(2)
  expect(wrapper.vm.loadError).toBe(false)
  expect(ElMessage.error).toHaveBeenCalledTimes(1)
})
