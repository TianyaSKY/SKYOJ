import { deferred } from './fixtures'
import type { ProblemDetailResponse } from '@/types/problem'
import type { SubmitCodeResponse } from '@/types/submission'
import type { CreateDebugRunResponse } from '@/types/debug'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { nextTick, reactive } from 'vue'
const state = vi.hoisted(() => ({ route: { params: { id: '1' }, query: {} as { exam_id?: string } } }))
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
let wrapper: ReturnType<typeof mountPage> | undefined
function mountedWrapper() {
  if (!wrapper) throw new Error('题目详情未挂载')
  return wrapper
}
// 测试访问 setup 状态，公共组件类型不公开这些字段。
function setupState() {
  return mountedWrapper().vm as unknown as {
    problem: ProblemDetailResponse; selectedFile: File | null; debugRunId: number | null; debugDrawerVisible: boolean;
    realtimeStatus: string; realtimeResult: { submission_id?: number } | null; submitting: boolean;
    handleSubmit(): Promise<void>; handleDebug(): Promise<void>; handleSubmitKaggle(): Promise<void>;
    startRealtimeWait(id: number): void;
  }
}
function socketCallbacks() {
  const callbacks = vi.mocked(createSubmissionWS).mock.calls[0]?.[2]
  if (!callbacks?.onMessage || !callbacks.onClose || !callbacks.onError || !callbacks.onReconnect) throw new Error('未注册完整订阅回调')
  return { onMessage: callbacks.onMessage, onClose: callbacks.onClose, onError: callbacks.onError, onReconnect: callbacks.onReconnect }
}
const submitted = (id: number): SubmitCodeResponse => ({ submission_id: id, message: '已提交', status: 'Pending', exam_id: null })
const debugged: CreateDebugRunResponse = { debug_run_id: 9, message: '已启动调试', status: 'Pending', exam_id: null }
const problem = (id: number): ProblemDetailResponse => ({ id, title: String(id), content: '', type: 'acm', language: 'python', time_limit: 1000, memory_limit: 128, template_code: null })

function mountPage() {
  const mounted = shallowMount(ProblemDetailView, { global: {
    directives: { loading: () => {} },
    stubs: Object.fromEntries(['el-icon','el-tag','el-button','el-select','el-option','el-tooltip','el-drawer','el-popover','el-input-number','el-switch','el-divider','el-card','el-upload','el-col','el-row','el-form','el-form-item','el-tabs','el-tab-pane','el-input'].map(name => [name,true])),
  } })
  wrapper = mounted
  return mounted
}
beforeEach(() => {
  vi.resetAllMocks()
  state.route = reactive({ params: { id: '1' }, query: {} })
  vi.mocked(getProblemDetail).mockImplementation(id => Promise.resolve(problem(id)))
  vi.mocked(createSubmissionWS).mockReturnValue({ connect: vi.fn(), close: vi.fn() })
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined })
it('复用题目页时加载新 ID，旧题面响应不能覆盖新题目', async () => {
  const old = deferred<ProblemDetailResponse>()
  vi.mocked(getProblemDetail).mockReturnValueOnce(old.promise)
  mountPage()
  state.route.params.id = '2'
  await nextTick(); await flushPromises()
  old.resolve(problem(1)); await flushPromises()
  expect(setupState().problem.id).toBe(2)
  vi.mocked(submitSolution).mockResolvedValue(submitted(20))
  await setupState().handleSubmit()
  const body = vi.mocked(submitSolution).mock.calls[0]?.[0]
  if (!body || body instanceof FormData) throw new Error('代码提交应使用对象请求体')
  expect(body.problem_id).toBe(2)
})
it('切换考试时清除附件、调试结果和实时订阅', async () => {
  mountPage(); await flushPromises()
  setupState().selectedFile = new File(['data'], 'answer.csv')
  setupState().debugRunId = 12
  setupState().debugDrawerVisible = true
  setupState().startRealtimeWait(10)
  const socket = vi.mocked(createSubmissionWS).mock.results[0].value
  state.route.query.exam_id = '8'
  await nextTick(); await flushPromises()
  expect(socket.close).toHaveBeenCalledOnce()
  expect(setupState().selectedFile).toBeNull()
  expect(setupState().debugRunId).toBeNull()
  expect(setupState().debugDrawerVisible).toBe(false)
  expect(setupState().realtimeStatus).toBe('idle')
})
it('旧提交返回不能启动订阅或清除新提交的加载状态', async () => {
  const old = deferred<SubmitCodeResponse>(), current = deferred<SubmitCodeResponse>()
  vi.mocked(submitSolution).mockReturnValueOnce(old.promise).mockReturnValueOnce(current.promise)
  mountPage(); await flushPromises()
  const first = setupState().handleSubmit()
  state.route.params.id = '2'
  await nextTick(); await flushPromises()
  const second = setupState().handleSubmit()
  old.resolve(submitted(10)); await first
  expect(createSubmissionWS).not.toHaveBeenCalled()
  expect(setupState().submitting).toBe(true)
  current.resolve(submitted(20)); await second
  expect(createSubmissionWS).toHaveBeenCalledWith(20, '', expect.any(Object))
})
it('卸载后迟到的调试响应不能打开结果面板', async () => {
  const response = deferred<CreateDebugRunResponse>()
  vi.mocked(debugSolution).mockReturnValue(response.promise)
  mountPage(); await flushPromises()
  const run = setupState().handleDebug(), vm = setupState()
  mountedWrapper().unmount(); wrapper = undefined
  response.resolve(debugged); await run
  expect(vm.debugRunId).toBeNull()
  expect(vm.debugDrawerVisible).toBe(false)
})
it('加载期间和重复点击不会发送请求', async () => {
  const detail = deferred<ProblemDetailResponse>(), run = deferred<CreateDebugRunResponse>()
  vi.mocked(getProblemDetail).mockReturnValue(detail.promise)
  mountPage()
  await setupState().handleSubmit(); await setupState().handleDebug()
  expect(submitSolution).not.toHaveBeenCalled()
  expect(debugSolution).not.toHaveBeenCalled()
  detail.resolve(problem(1)); await flushPromises()
  vi.mocked(debugSolution).mockReturnValue(run.promise)
  const first = setupState().handleDebug()
  await setupState().handleDebug()
  expect(debugSolution).toHaveBeenCalledOnce()
  run.resolve(debugged); await first
})
it('旧请求错误和订阅回调不会影响新题目', async () => {
  const response = deferred<CreateDebugRunResponse>()
  vi.mocked(debugSolution).mockReturnValue(response.promise)
  mountPage(); await flushPromises()
  setupState().startRealtimeWait(10)
  const callbacks = socketCallbacks()
  const run = setupState().handleDebug()
  state.route.params.id = '2'
  await nextTick(); await flushPromises()
  response.reject(new Error('old')); await run
  callbacks.onMessage({ status: 'Accepted', score: 100 })
  expect(ElMessage.error).not.toHaveBeenCalled()
  expect(setupState().realtimeResult).toBeNull()
})
it('旧 CSV 上传完成后不能为新题目启动结果订阅', async () => {
  const upload = deferred<SubmitCodeResponse>()
  vi.mocked(getProblemDetail).mockResolvedValue({ ...problem(1), type: 'kaggle' })
  vi.mocked(submitSolution).mockReturnValue(upload.promise)
  mountPage(); await flushPromises()
  setupState().selectedFile = new File(['id,value\n1,1'], 'answer.csv')
  const run = setupState().handleSubmitKaggle()
  const body = vi.mocked(submitSolution).mock.calls[0]?.[0]
  if (!(body instanceof FormData)) throw new Error('CSV 提交应使用 FormData')
  expect(body.get('problem_id')).toBe('1')
  state.route.params.id = '2'
  await nextTick(); await flushPromises()
  upload.resolve(submitted(19)); await run
  expect(createSubmissionWS).not.toHaveBeenCalled()
  expect(setupState().submitting).toBe(false)
})
it('收到结果后的正常关闭和网络错误都不能隐藏成绩或详情入口', async () => {
  mountPage(); await flushPromises()
  setupState().startRealtimeWait(10)
  const callbacks = socketCallbacks()
  callbacks.onMessage({ submission_id: 10, status: 'Accepted', score: 100 })
  callbacks.onClose(new CloseEvent('close', { code: 1000 }))
  callbacks.onError(new Error('connection already closed'))
  callbacks.onReconnect(1)
  await nextTick()
  expect(setupState().realtimeStatus).toBe('received')
  expect(mountedWrapper().find('.realtime-toast').text()).toContain('判题完成：Accepted')
  expect(mountedWrapper().find('.realtime-toast').text()).toContain('得分 100.0')
  expect(setupState().realtimeResult?.submission_id).toBe(10)
})
it('尚未收到结果时重连恢复等待提示，旧页重连不影响新页面', async () => {
  mountPage(); await flushPromises()
  setupState().startRealtimeWait(10)
  const callbacks = socketCallbacks()
  callbacks.onClose(new CloseEvent('close', { code: 1006 }))
  expect(setupState().realtimeStatus).toBe('closed')
  callbacks.onReconnect(1)
  expect(setupState().realtimeStatus).toBe('pending')
  state.route.params.id = '2'
  await nextTick(); await flushPromises()
  callbacks.onReconnect(2)
  expect(setupState().realtimeStatus).toBe('idle')
})
