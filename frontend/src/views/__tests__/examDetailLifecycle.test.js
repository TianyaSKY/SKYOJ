import { beforeEach, afterEach, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { reactive, nextTick } from 'vue'
import { shallowMount, flushPromises } from '@vue/test-utils'
const { push, routeHolder } = vi.hoisted(() => ({ push: vi.fn(), routeHolder: {} }))
vi.mock('vue-router', () => ({ useRoute: () => routeHolder.route, useRouter: () => ({ push }) }))
vi.mock('@/utils/request', () => ({ default: {} }))
vi.mock('@/api/exam', () => ({ getExamDetail: vi.fn(), getMyExamStatus: vi.fn(), exitExam: vi.fn() }))
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn(), success: vi.fn() }, ElMessageBox: { confirm: vi.fn(), alert: vi.fn() } }))
import ExamDetailView from '../ExamDetailView.vue'
import { getExamDetail, getMyExamStatus, exitExam } from '@/api/exam'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
let wrapper
const exam = id => ({ id, title: `考试${id}`, start_time: '2090-06-15T10:00:00', end_time: '2090-06-15T11:00:00', problems: [] })
function deferred() {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
function mountPage() {
  wrapper = shallowMount(ExamDetailView, { global: { directives: { loading: () => {} }, stubs: Object.fromEntries(['el-icon','el-row','el-col','el-card','el-tag','el-link','el-table','el-table-column','el-button','el-progress','el-divider','el-alert'].map(name => [name,true])) } })
  return wrapper.vm
}
beforeEach(() => {
  vi.resetAllMocks(); localStorage.clear(); setActivePinia(createPinia()); useUserStore().setToken('exam-token')
  routeHolder.route = reactive({ params: { id: 1 } })
  getExamDetail.mockImplementation(id => Promise.resolve(exam(id))); getMyExamStatus.mockResolvedValue([])
  exitExam.mockResolvedValue({ token: 'practice-token' }); push.mockResolvedValue(undefined)
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined; vi.restoreAllMocks() })
it('组件复用后加载新考试，清空旧得分，导航使用新 ID', async () => {
  getMyExamStatus.mockResolvedValueOnce([{ current_score: 100, max_score: 100 }])
  const vm = mountPage(); await flushPromises(); expect(vm.totalCurrentScore).toBe(100)
  const detail = deferred(); getExamDetail.mockReturnValueOnce(detail.promise)
  routeHolder.route.params.id = 2; await nextTick()
  expect(vm.problemStatus).toEqual([]); expect(vm.exam.title).toBe('加载中...')
  expect(getExamDetail).toHaveBeenLastCalledWith(2)
  detail.resolve(exam(2)); await flushPromises(); expect(vm.exam.title).toBe('考试2')
  vm.goToProblem(7); expect(push).toHaveBeenLastCalledWith({ path: '/problem/7', query: { exam_id: 2 } })
  vm.goToRank(); expect(push).toHaveBeenLastCalledWith('/exam/2/rank')
})
it.each(['resolve','reject'])('切换后旧详情 %s 不能覆盖当前考试或跳转', async outcome => {
  const old = deferred(); getExamDetail.mockReturnValueOnce(old.promise)
  const vm = mountPage(); routeHolder.route.params.id = 2; await flushPromises()
  old[outcome](outcome === 'resolve' ? exam(1) : new Error('old')); await flushPromises()
  expect(vm.exam.title).toBe('考试2'); expect(push).not.toHaveBeenCalled(); expect(ElMessage.error).not.toHaveBeenCalled()
  expect(getMyExamStatus).toHaveBeenCalledOnce()
})
it('连续刷新只发一次状态请求，完成后可以再次刷新', async () => {
  const vm = mountPage(); await flushPromises()
  const status = deferred(); getMyExamStatus.mockReturnValueOnce(status.promise)
  const pending = vm.fetchStatus(); await vm.fetchStatus(); expect(getMyExamStatus).toHaveBeenCalledTimes(2)
  status.resolve([{ current_score: 50 }]); await pending; expect(vm.totalCurrentScore).toBe(50)
  await vm.fetchStatus(); expect(getMyExamStatus).toHaveBeenCalledTimes(3)
})
it.each(['resolve','reject'])('旧状态 %s 不能覆盖新考试或解开新请求的加载状态', async outcome => {
  const old = deferred(), current = deferred(); getMyExamStatus.mockReturnValueOnce(old.promise).mockReturnValueOnce(current.promise)
  const vm = mountPage(); await flushPromises(); routeHolder.route.params.id = 2; await flushPromises()
  old[outcome](outcome === 'resolve' ? [{ current_score: 100 }] : new Error('old')); await flushPromises()
  expect(vm.statusLoading).toBe(true); expect(vm.problemStatus).toEqual([]); expect(ElMessage.error).not.toHaveBeenCalled()
  current.resolve([{ current_score: 25 }]); await flushPromises(); expect(vm.totalCurrentScore).toBe(25); expect(vm.statusLoading).toBe(false)
})
it('当前状态失败保留成绩并提示重试，下一次刷新成功', async () => {
  getMyExamStatus.mockResolvedValueOnce([{ current_score: 25 }]); const vm = mountPage(); await flushPromises()
  const diagnostic = vi.spyOn(console, 'error').mockImplementation(() => {})
  getMyExamStatus.mockRejectedValueOnce(new Error('network')); await vm.fetchStatus()
  expect(vm.totalCurrentScore).toBe(25); expect(vm.statusLoading).toBe(false); expect(ElMessage.error).toHaveBeenCalledOnce(); expect(diagnostic).toHaveBeenCalledOnce()
  getMyExamStatus.mockResolvedValueOnce([{ current_score: 50 }]); await vm.fetchStatus(); expect(vm.totalCurrentScore).toBe(50)
})
it('路由切换使旧退出确认失效，即使令牌相同也不退出新页面', async () => {
  const confirmation = deferred(); ElMessageBox.confirm.mockReturnValueOnce(confirmation.promise)
  const vm = mountPage(); await flushPromises(); const pending = vm.handleExitExam()
  routeHolder.route.params.id = 2; await flushPromises(); confirmation.resolve(); await pending
  expect(exitExam).not.toHaveBeenCalled(); expect(vm.exitConfirming).toBe(false)
})
it('路由切换使已发出的旧退出响应失效', async () => {
  const response = deferred(); exitExam.mockReturnValueOnce(response.promise)
  const vm = mountPage(); await flushPromises(); const pending = vm.performExit()
  routeHolder.route.params.id = 2; await flushPromises(); response.resolve({ token: 'old' }); await pending
  expect(useUserStore().token).toBe('exam-token'); expect(push).not.toHaveBeenCalled(); expect(ElMessage.success).not.toHaveBeenCalled()
})
it('退出登录后迟到的状态不显示旧得分，离开页面后不能重新刷新', async () => {
  const response = deferred(); getMyExamStatus.mockReturnValueOnce(response.promise)
  const vm = mountPage(); await flushPromises(); useUserStore().logout()
  response.resolve([{ current_score: 100 }]); await flushPromises(); expect(vm.problemStatus).toEqual([])
  wrapper.unmount(); wrapper = undefined; await vm.fetchStatus(); expect(getMyExamStatus).toHaveBeenCalledOnce()
})
