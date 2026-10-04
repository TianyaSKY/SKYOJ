import { examResponse, examStatus, problemResponse, deferred } from './fixtures'
import type { ExamDetailResponse, ExamListResponse, ExamProblemStatusResponse, ExamResponse, ExamTokenResponse } from '@/types/exam'
import { beforeEach, afterEach, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { reactive, nextTick } from 'vue'
import { shallowMount, flushPromises } from '@vue/test-utils'
const { push, routeHolder } = vi.hoisted(() => ({ push: vi.fn(), routeHolder: { route: { params: { id: '1' } } } }))
vi.mock('vue-router', () => ({ useRoute: () => routeHolder.route, useRouter: () => ({ push }) }))
vi.mock('@/utils/request', () => ({ default: {} }))
vi.mock('@/api/exam', () => ({ getExamDetail: vi.fn(), getMyExamStatus: vi.fn(), exitExam: vi.fn() }))
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn(), success: vi.fn() }, ElMessageBox: { confirm: vi.fn(), alert: vi.fn() } }))
import ExamDetailView from '../ExamDetailView.vue'
import { getExamDetail, getMyExamStatus, exitExam } from '@/api/exam'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
interface PageState { totalCurrentScore: number; problemStatus: ExamProblemStatusResponse[]; exam: ExamDetailResponse;
  statusLoading: boolean; exitConfirming: boolean; goToProblem(id: number): void; goToRank(): void;
  fetchStatus(): Promise<void>; handleExitExam(): Promise<void>; performExit(): Promise<void>; handleExamEnd(): void; }
let wrapper: ReturnType<typeof shallowMount> | undefined
function mountedWrapper() {
  if (!wrapper) throw new Error('考试页面未挂载')
  return wrapper
}
const exam = examResponse

function mountPage() {
  wrapper = shallowMount(ExamDetailView, { global: { directives: { loading: () => {} }, stubs: Object.fromEntries(['el-icon','el-row','el-col','el-card','el-tag','el-link','el-table','el-table-column','el-button','el-progress','el-divider','el-alert'].map(name => [name,true])) } })
  return wrapper.vm as unknown as PageState
}
beforeEach(() => {
  vi.resetAllMocks(); localStorage.clear(); setActivePinia(createPinia()); useUserStore().setToken('exam-token')
  routeHolder.route = reactive({ params: { id: '1' } })
  vi.mocked(getExamDetail).mockImplementation(id => Promise.resolve(exam(id))); vi.mocked(getMyExamStatus).mockResolvedValue([])
  vi.mocked(exitExam).mockResolvedValue({ token: 'practice-token', message: '成功' }); push.mockResolvedValue(undefined)
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined; vi.restoreAllMocks() })
it('组件复用后加载新考试，清空旧得分，导航使用新 ID', async () => {
  vi.mocked(getMyExamStatus).mockResolvedValueOnce([examStatus({ current_score: 100, max_score: 100 })])
  const vm = mountPage(); await flushPromises(); expect(vm.totalCurrentScore).toBe(100)
  const detail = deferred<ExamDetailResponse>(); vi.mocked(getExamDetail).mockReturnValueOnce(detail.promise)
  routeHolder.route.params.id = '2'; await nextTick()
  expect(vm.problemStatus).toEqual([]); expect(vm.exam.title).toBe('加载中...')
  expect(getExamDetail).toHaveBeenLastCalledWith(2)
  detail.resolve(exam(2)); await flushPromises(); expect(vm.exam.title).toBe('考试2')
  expect(getMyExamStatus).toHaveBeenLastCalledWith(2)
  vm.goToProblem(7); expect(push).toHaveBeenLastCalledWith({ path: '/problem/7', query: { exam_id: 2 } })
  vm.goToRank(); expect(push).toHaveBeenLastCalledWith('/exam/2/rank')
})
it.each(['resolve','reject'])('切换后旧详情 %s 不能覆盖当前考试或跳转', async outcome => {
  const old = deferred<ExamDetailResponse>(); vi.mocked(getExamDetail).mockReturnValueOnce(old.promise)
  const vm = mountPage(); routeHolder.route.params.id = '2'; await flushPromises()
  if (outcome === 'resolve') old.resolve(exam(1)); else old.reject(new Error('old')); await flushPromises()
  expect(vm.exam.title).toBe('考试2'); expect(push).not.toHaveBeenCalled(); expect(ElMessage.error).not.toHaveBeenCalled()
  expect(getMyExamStatus).toHaveBeenCalledOnce()
})
it('连续刷新只发一次状态请求，完成后可以再次刷新', async () => {
  const vm = mountPage(); await flushPromises()
  const status = deferred<ExamProblemStatusResponse[]>(); vi.mocked(getMyExamStatus).mockReturnValueOnce(status.promise)
  const pending = vm.fetchStatus(); await vm.fetchStatus(); expect(getMyExamStatus).toHaveBeenCalledTimes(2)
  status.resolve([examStatus({ current_score: 50 })]); await pending; expect(vm.totalCurrentScore).toBe(50)
  await vm.fetchStatus(); expect(getMyExamStatus).toHaveBeenCalledTimes(3)
})
it.each(['resolve','reject'])('旧状态 %s 不能覆盖新考试或解开新请求的加载状态', async outcome => {
  const old = deferred<ExamProblemStatusResponse[]>(), current = deferred<ExamProblemStatusResponse[]>(); vi.mocked(getMyExamStatus).mockReturnValueOnce(old.promise).mockReturnValueOnce(current.promise)
  const vm = mountPage(); await flushPromises(); routeHolder.route.params.id = '2'; await flushPromises()
  if (outcome === 'resolve') old.resolve([examStatus({ current_score: 100 })]); else old.reject(new Error('old')); await flushPromises()
  expect(vm.statusLoading).toBe(true); expect(vm.problemStatus).toEqual([]); expect(ElMessage.error).not.toHaveBeenCalled()
  current.resolve([examStatus({ current_score: 25 })]); await flushPromises(); expect(vm.totalCurrentScore).toBe(25); expect(vm.statusLoading).toBe(false)
})
it('当前状态失败保留成绩并提示重试，下一次刷新成功', async () => {
  vi.mocked(getMyExamStatus).mockResolvedValueOnce([examStatus({ current_score: 25 })]); const vm = mountPage(); await flushPromises()
  const diagnostic = vi.spyOn(console, 'error').mockImplementation(() => {})
  vi.mocked(getMyExamStatus).mockRejectedValueOnce(new Error('network')); await vm.fetchStatus()
  expect(vm.totalCurrentScore).toBe(25); expect(vm.statusLoading).toBe(false); expect(ElMessage.error).toHaveBeenCalledOnce(); expect(diagnostic).toHaveBeenCalledOnce()
  vi.mocked(getMyExamStatus).mockResolvedValueOnce([examStatus({ current_score: 50 })]); await vm.fetchStatus(); expect(vm.totalCurrentScore).toBe(50)
})
it('路由切换使旧退出确认失效，即使令牌相同也不退出新页面', async () => {
  const confirmation = deferred<Awaited<ReturnType<typeof ElMessageBox.confirm>>>(); vi.mocked(ElMessageBox.confirm).mockReturnValueOnce(confirmation.promise)
  const vm = mountPage(); await flushPromises(); const pending = vm.handleExitExam()
  routeHolder.route.params.id = '2'; await flushPromises(); confirmation.resolve('confirm' as Awaited<ReturnType<typeof ElMessageBox.confirm>>); await pending
  expect(exitExam).not.toHaveBeenCalled(); expect(vm.exitConfirming).toBe(false)
})
it('路由切换使已发出的旧退出响应失效', async () => {
  const response = deferred<ExamTokenResponse>(); vi.mocked(exitExam).mockReturnValueOnce(response.promise)
  const vm = mountPage(); await flushPromises(); const pending = vm.performExit()
  routeHolder.route.params.id = '2'; await flushPromises(); response.resolve({ token: 'old', message: '成功' }); await pending
  expect(useUserStore().token).toBe('exam-token'); expect(push).not.toHaveBeenCalled(); expect(ElMessage.success).not.toHaveBeenCalled()
})
it('退出登录后迟到的状态不显示旧得分，离开页面后不能重新刷新', async () => {
  const response = deferred<ExamProblemStatusResponse[]>(); vi.mocked(getMyExamStatus).mockReturnValueOnce(response.promise)
  const vm = mountPage(); await flushPromises(); useUserStore().logout()
  response.resolve([examStatus({ current_score: 100 })]); await flushPromises(); expect(vm.problemStatus).toEqual([])
  mountedWrapper().unmount(); wrapper = undefined; await vm.fetchStatus(); expect(getMyExamStatus).toHaveBeenCalledOnce()
})
it('会话与页面考试不匹配时不能沿用前一场考试的得分', async () => {
  vi.mocked(getMyExamStatus).mockResolvedValueOnce([examStatus({ current_score: 100 })])
  const vm = mountPage(); await flushPromises(); expect(vm.totalCurrentScore).toBe(100)
  vi.spyOn(console, 'error').mockImplementation(() => {})
  vi.mocked(getMyExamStatus).mockRejectedValueOnce(new Error('未进入该考试，无法查询题目状态'))
  routeHolder.route.params.id = '2'; await flushPromises()
  expect(getMyExamStatus).toHaveBeenLastCalledWith(2)
  expect(vm.problemStatus).toEqual([]); expect(vm.totalCurrentScore).toBe(0)
  expect(ElMessage.error).toHaveBeenCalledWith('获取题目状态失败，请重试')
})

it('不匹配的已结束考试不能触发自动退出当前会话', async () => {
  vi.mocked(getExamDetail).mockResolvedValueOnce({ ...exam(2), start_time: '2020-06-15T10:00:00', end_time: '2020-06-15T11:00:00' })
  vi.mocked(getMyExamStatus).mockRejectedValueOnce(new Error('未进入该考试'))
  vi.spyOn(console, 'error').mockImplementation(() => {})
  const vm = mountPage(); await flushPromises(); vm.handleExamEnd()
  expect(ElMessageBox.alert).not.toHaveBeenCalled(); expect(exitExam).not.toHaveBeenCalled()
})
