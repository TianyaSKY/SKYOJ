import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { nextTick, reactive } from 'vue'
const state = vi.hoisted(() => ({ route: null }))
vi.mock('vue-router', () => ({ useRoute: () => state.route, useRouter: () => ({ push: vi.fn() }) }))
vi.mock('@/api/problem', () => ({ getProblemDetail: vi.fn(), submitSolution: vi.fn() }))
vi.mock('@/api/debug', () => ({ debugSolution: vi.fn() }))
vi.mock('@/utils/websocket', () => ({ createSubmissionWS: vi.fn() }))
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn(), success: vi.fn(), warning: vi.fn() } }))
vi.mock('@guolao/vue-monaco-editor', () => ({ VueMonacoEditor: { template: '<div />' } }))
vi.mock('@/components/DebugResultPanel.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/components/SolutionPanel.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/components/TagPanel.vue', () => ({ default: { template: '<div />' } }))
import ProblemDetailView from '../ProblemDetailView.vue'
import { getProblemDetail, submitSolution } from '@/api/problem'
import { debugSolution } from '@/api/debug'
import { createSubmissionWS } from '@/utils/websocket'
import { ElMessage } from 'element-plus'
let wrapper
const problem = id => ({ id, title: String(id), content: '', type: 'acm', language: 'python' })
function deferred() {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
function mountPage() {
  wrapper = shallowMount(ProblemDetailView, { global: {
    directives: { loading: () => {} },
    stubs: Object.fromEntries(['el-icon','el-tag','el-button','el-select','el-option','el-tooltip','el-drawer','el-popover','el-input-number','el-switch','el-divider'].map(name => [name,true])),
  } })
}
beforeEach(() => {
  vi.resetAllMocks()
  state.route = reactive({ params: { id: '1' }, query: {} })
  getProblemDetail.mockImplementation(id => Promise.resolve(problem(id)))
  createSubmissionWS.mockReturnValue({ connect: vi.fn(), close: vi.fn() })
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined })
it('复用题目页时加载新 ID，旧题面响应不能覆盖新题目', async () => {
  const old = deferred()
  getProblemDetail.mockReturnValueOnce(old.promise)
  mountPage()
  state.route.params.id = '2'
  await nextTick(); await flushPromises()
  old.resolve(problem('1')); await flushPromises()
  expect(wrapper.vm.problem.id).toBe('2')
  submitSolution.mockResolvedValue({ submission_id: 20 })
  await wrapper.vm.handleSubmit()
  expect(submitSolution.mock.calls[0][0].problem_id).toBe(2)
})
it('切换考试时清除附件、调试结果和实时订阅', async () => {
  mountPage(); await flushPromises()
  wrapper.vm.selectedFile = new File(['data'], 'answer.csv')
  wrapper.vm.debugRunId = 12
  wrapper.vm.debugDrawerVisible = true
  wrapper.vm.startRealtimeWait(10)
  const socket = createSubmissionWS.mock.results[0].value
  state.route.query.exam_id = '8'
  await nextTick(); await flushPromises()
  expect(socket.close).toHaveBeenCalledOnce()
  expect(wrapper.vm.selectedFile).toBeNull()
  expect(wrapper.vm.debugRunId).toBeNull()
  expect(wrapper.vm.debugDrawerVisible).toBe(false)
  expect(wrapper.vm.realtimeStatus).toBe('idle')
})
it('旧提交返回不能启动订阅或清除新提交的加载状态', async () => {
  const old = deferred(), current = deferred()
  submitSolution.mockReturnValueOnce(old.promise).mockReturnValueOnce(current.promise)
  mountPage(); await flushPromises()
  const first = wrapper.vm.handleSubmit()
  state.route.params.id = '2'
  await nextTick(); await flushPromises()
  const second = wrapper.vm.handleSubmit()
  old.resolve({ submission_id: 10 }); await first
  expect(createSubmissionWS).not.toHaveBeenCalled()
  expect(wrapper.vm.submitting).toBe(true)
  current.resolve({ submission_id: 20 }); await second
  expect(createSubmissionWS).toHaveBeenCalledWith(20, '', expect.any(Object))
})
it('卸载后迟到的调试响应不能打开结果面板', async () => {
  const response = deferred()
  debugSolution.mockReturnValue(response.promise)
  mountPage(); await flushPromises()
  const run = wrapper.vm.handleDebug(), vm = wrapper.vm
  wrapper.unmount(); wrapper = undefined
  response.resolve({ debug_run_id: 9 }); await run
  expect(vm.debugRunId).toBeNull()
  expect(vm.debugDrawerVisible).toBe(false)
})
it('加载期间和重复点击不会发送请求', async () => {
  const detail = deferred(), run = deferred()
  getProblemDetail.mockReturnValue(detail.promise)
  mountPage()
  await wrapper.vm.handleSubmit(); await wrapper.vm.handleDebug()
  expect(submitSolution).not.toHaveBeenCalled()
  expect(debugSolution).not.toHaveBeenCalled()
  detail.resolve(problem(1)); await flushPromises()
  debugSolution.mockReturnValue(run.promise)
  const first = wrapper.vm.handleDebug()
  await wrapper.vm.handleDebug()
  expect(debugSolution).toHaveBeenCalledOnce()
  run.resolve({ debug_run_id: 9 }); await first
})
it('旧请求错误和订阅回调不会影响新题目', async () => {
  const response = deferred()
  debugSolution.mockReturnValue(response.promise)
  mountPage(); await flushPromises()
  wrapper.vm.startRealtimeWait(10)
  const callbacks = createSubmissionWS.mock.calls[0][2]
  const run = wrapper.vm.handleDebug()
  state.route.params.id = '2'
  await nextTick(); await flushPromises()
  response.reject(new Error('old')); await run
  callbacks.onMessage({ status: 'Accepted', score: 100 })
  expect(ElMessage.error).not.toHaveBeenCalled()
  expect(wrapper.vm.realtimeResult).toBeNull()
})
it('旧 CSV 上传完成后不能为新题目启动结果订阅', async () => {
  const upload = deferred()
  getProblemDetail.mockResolvedValue({ ...problem(1), type: 'kaggle' })
  submitSolution.mockReturnValue(upload.promise)
  mountPage(); await flushPromises()
  wrapper.vm.selectedFile = new File(['id,value\n1,1'], 'answer.csv')
  const run = wrapper.vm.handleSubmitKaggle()
  expect(submitSolution.mock.calls[0][0].get('problem_id')).toBe('1')
  state.route.params.id = '2'
  await nextTick(); await flushPromises()
  upload.resolve({ submission_id: 19 }); await run
  expect(createSubmissionWS).not.toHaveBeenCalled()
  expect(wrapper.vm.submitting).toBe(false)
})
it('收到结果后的正常关闭和网络错误都不能隐藏成绩或详情入口', async () => {
  mountPage(); await flushPromises()
  wrapper.vm.startRealtimeWait(10)
  const callbacks = createSubmissionWS.mock.calls[0][2]
  callbacks.onMessage({ submission_id: 10, status: 'Accepted', score: 100 })
  callbacks.onClose({ code: 1000 })
  callbacks.onError(new Error('connection already closed'))
  callbacks.onReconnect(1)
  await nextTick()
  expect(wrapper.vm.realtimeStatus).toBe('received')
  expect(wrapper.find('.realtime-toast').text()).toContain('判题完成：Accepted')
  expect(wrapper.find('.realtime-toast').text()).toContain('得分 100.0')
  expect(wrapper.vm.realtimeResult.submission_id).toBe(10)
})
it('尚未收到结果时重连恢复等待提示，旧页重连不影响新页面', async () => {
  mountPage(); await flushPromises()
  wrapper.vm.startRealtimeWait(10)
  const callbacks = createSubmissionWS.mock.calls[0][2]
  callbacks.onClose({ code: 1006 })
  expect(wrapper.vm.realtimeStatus).toBe('closed')
  callbacks.onReconnect(1)
  expect(wrapper.vm.realtimeStatus).toBe('pending')
  state.route.params.id = '2'
  await nextTick(); await flushPromises()
  callbacks.onReconnect(2)
  expect(wrapper.vm.realtimeStatus).toBe('idle')
})
