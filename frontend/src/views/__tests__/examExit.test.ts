import type { ExamListResponse, ExamDetailResponse, EnterExamResponse, ExamTokenResponse } from '@/types/exam'
import { beforeEach, afterEach, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { shallowMount, flushPromises } from '@vue/test-utils'
const { push } = vi.hoisted(() => ({ push: vi.fn() }))
vi.mock('vue-router', () => ({ useRoute: () => ({ params: { id: '1' } }), useRouter: () => ({ push }) }))
vi.mock('@/utils/request', () => ({ default: {} }))
vi.mock('@/api/exam', () => ({ getExamDetail: vi.fn(), getMyExamStatus: vi.fn(), exitExam: vi.fn() }))
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn(), success: vi.fn() }, ElMessageBox: { confirm: vi.fn(), alert: vi.fn() } }))
import ExamDetailView from '../ExamDetailView.vue'
import { getExamDetail, getMyExamStatus, exitExam } from '@/api/exam'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
interface PageState { exiting: boolean; exitConfirming: boolean; performExit(): Promise<void>; handleExitExam(): Promise<void>; handleExamEnd(): void; }
let wrapper: ReturnType<typeof shallowMount> | undefined
function mountedWrapper() {
  if (!wrapper) throw new Error('考试页面未挂载')
  return wrapper
}
function deferred<T = void>() {
  let resolve!: (value: T) => void, reject!: (reason: unknown) => void
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
async function mountPage() {
  wrapper = shallowMount(ExamDetailView, { global: { directives: { loading: () => {} }, stubs: Object.fromEntries(['el-icon','el-row','el-col','el-card','el-tag','el-link','el-table','el-table-column','el-button','el-progress','el-divider','el-alert'].map(name => [name,true])) } })
  await flushPromises(); return wrapper.vm as unknown as PageState
}
beforeEach(() => {
  vi.resetAllMocks(); localStorage.clear(); setActivePinia(createPinia()); useUserStore().setToken('exam-token')
  vi.mocked(getExamDetail).mockResolvedValue({ id: 1, description: '', contest_type: 'icpc', freeze_minutes: null, is_visible: true, created_by: 1, has_password: false, title: '考试', start_time: '2090-06-15T10:00:00', end_time: '2090-06-15T11:00:00', problems: [] })
  vi.mocked(getMyExamStatus).mockResolvedValue([]); vi.mocked(exitExam).mockResolvedValue({ token: 'practice-token', message: '成功' }); push.mockResolvedValue(undefined)
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined })
it('退出成功同步 Store 与缓存并跳转', async () => {
  const vm = await mountPage(); await vm.performExit()
  expect(useUserStore().token).toBe('practice-token'); expect(localStorage.getItem('token')).toBe('practice-token')
  expect(push).toHaveBeenCalledExactlyOnceWith('/exam'); expect(vm.exiting).toBe(false)
})
it('重复退出请求只发送一次，路由跳转完成前保持锁定', async () => {
  const response = deferred<ExamTokenResponse>(), navigation = deferred(); vi.mocked(exitExam).mockReturnValue(response.promise); push.mockReturnValue(navigation.promise)
  const vm = await mountPage(); const pending = vm.performExit(); await vm.performExit()
  expect(exitExam).toHaveBeenCalledOnce(); response.resolve({ token: 'practice-token', message: '成功' }); await flushPromises()
  await vm.performExit(); expect(exitExam).toHaveBeenCalledOnce(); expect(vm.exiting).toBe(true)
  navigation.resolve(); await pending; expect(vm.exiting).toBe(false)
})
it('重复点击只创建一个退出确认', async () => {
  const confirmation = deferred<Awaited<ReturnType<typeof ElMessageBox.confirm>>>(); vi.mocked(ElMessageBox.confirm).mockReturnValue(confirmation.promise)
  const vm = await mountPage(); const pending = vm.handleExitExam(); await vm.handleExitExam()
  expect(ElMessageBox.confirm).toHaveBeenCalledOnce(); expect(exitExam).not.toHaveBeenCalled()
  confirmation.resolve('confirm' as Awaited<ReturnType<typeof ElMessageBox.confirm>>); await pending; expect(exitExam).toHaveBeenCalledOnce(); expect(vm.exitConfirming).toBe(false)
})
it.each(['cancel','close'])('取消退出 %s 正常结束且允许重试', async reason => {
  vi.mocked(ElMessageBox.confirm).mockRejectedValueOnce(reason)
  const vm = await mountPage(); await vm.handleExitExam()
  expect(exitExam).not.toHaveBeenCalled(); expect(ElMessage.error).not.toHaveBeenCalled(); expect(vm.exitConfirming).toBe(false)
  vi.mocked(ElMessageBox.confirm).mockResolvedValueOnce('confirm' as Awaited<ReturnType<typeof ElMessageBox.confirm>>); await vm.handleExitExam(); expect(exitExam).toHaveBeenCalledOnce()
})
it('确认期间会话改变不能退出新的会话', async () => {
  const confirmation = deferred<Awaited<ReturnType<typeof ElMessageBox.confirm>>>(); vi.mocked(ElMessageBox.confirm).mockReturnValue(confirmation.promise)
  const vm = await mountPage(); const pending = vm.handleExitExam(); useUserStore().setToken('another-exam')
  confirmation.resolve('confirm' as Awaited<ReturnType<typeof ElMessageBox.confirm>>); await pending; expect(exitExam).not.toHaveBeenCalled(); expect(push).not.toHaveBeenCalled()
})
it('考试结束提示的旧回调不能退出新的会话', async () => {
  const vm = await mountPage(); vm.handleExamEnd()
  const callback = vi.mocked(ElMessageBox.alert).mock.calls[0]?.[2]?.callback
  useUserStore().setToken('another-exam'); await callback?.('confirm', 'confirm'); expect(exitExam).not.toHaveBeenCalled()
})
it('退出请求期间登出后旧响应不能恢复登录', async () => {
  const response = deferred<ExamTokenResponse>(); vi.mocked(exitExam).mockReturnValue(response.promise)
  const vm = await mountPage(); const pending = vm.performExit(); useUserStore().logout()
  response.resolve({ token: 'stale', message: '成功' }); await pending
  expect(useUserStore().token).toBe(''); expect(localStorage.getItem('token')).toBeNull()
  expect(push).not.toHaveBeenCalled(); expect(ElMessage.success).not.toHaveBeenCalled()
})
it('离开页面后迟到响应不修改令牌或跳转', async () => {
  const response = deferred<ExamTokenResponse>(); vi.mocked(exitExam).mockReturnValue(response.promise)
  const vm = await mountPage(); const pending = vm.performExit(); mountedWrapper().unmount(); wrapper = undefined
  response.resolve({ token: 'stale', message: '成功' }); await pending
  expect(useUserStore().token).toBe('exam-token'); expect(push).not.toHaveBeenCalled(); expect(ElMessage.success).not.toHaveBeenCalled()
})
it('请求失败解除锁，保留原令牌以便重试', async () => {
  vi.mocked(exitExam).mockRejectedValueOnce(new Error('network'))
  const vm = await mountPage(); await vm.performExit()
  expect(useUserStore().token).toBe('exam-token'); expect(vm.exiting).toBe(false); expect(ElMessage.error).toHaveBeenCalledWith('退出考试失败')
  await vm.performExit(); expect(useUserStore().token).toBe('practice-token')
})
