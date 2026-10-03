import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
const { push } = vi.hoisted(() => ({ push: vi.fn() }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))
vi.mock('@/api/exam', () => ({ getExamList: vi.fn(), enterExam: vi.fn() }))
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn(), warning: vi.fn() } }))
import ExamView from '../ExamView.vue'
import { enterExam, getExamList } from '@/api/exam'
import { ElMessage } from 'element-plus'
let wrapper
const exam = { id: 1, start_time: '2026-06-15T10:00:00', end_time: '2026-06-15T11:00:00' }
function deferred() {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
function forbidden(message) { return { response: { status: 403, data: { error: message } }, message } }
function mountPage() {
  wrapper = shallowMount(ExamView, { global: { directives: { loading: () => {} }, stubs: Object.fromEntries(['el-row','el-col','el-card','el-icon','el-button','el-empty','el-dialog','el-input'].map(name => [name, true])) } })
  return wrapper.vm
}
async function openPassword(vm) {
  enterExam.mockRejectedValueOnce(forbidden('考试密码错误'))
  await vm.handleEnterExam(exam)
  expect(vm.passwordDialogVisible).toBe(true)
  vm.passwordInput = 'secret'
}
beforeEach(() => {
  vi.resetAllMocks(); localStorage.clear(); localStorage.setItem('token', 'original')
  vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
  vi.setSystemTime(new Date('2026-06-15T10:30:00Z'))
  getExamList.mockResolvedValue([exam]); push.mockResolvedValue(undefined)
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined; vi.clearAllTimers(); vi.useRealTimers() })
it('重复点击同一或其他考试只发送一次进入请求，保留原考试', async () => {
  const response = deferred(); enterExam.mockReturnValue(response.promise)
  const vm = mountPage(); const pending = vm.handleEnterExam(exam)
  await vm.handleEnterExam(exam); await vm.handleEnterExam({ ...exam, id: 2 })
  expect(enterExam).toHaveBeenCalledExactlyOnceWith(1, '')
  expect(vm.currentExamId).toBe(1); expect(vm.entering).toBe(true)
  response.resolve({ token: 'exam-one' }); await pending
  expect(localStorage.getItem('token')).toBe('exam-one'); expect(push).toHaveBeenCalledExactlyOnceWith('/exam/1')
  expect(vm.entering).toBe(false)
})
it('密码弹窗保持原考试，提交期间禁止重复提交和关闭', async () => {
  const vm = mountPage(); await openPassword(vm)
  await vm.handleEnterExam({ ...exam, id: 2 }); expect(vm.currentExamId).toBe(1)
  const response = deferred(); enterExam.mockReturnValueOnce(response.promise)
  const pending = vm.handlePasswordSubmit(); await vm.handlePasswordSubmit()
  const close = vi.fn(); vm.handlePasswordClose(close)
  expect(close).not.toHaveBeenCalled(); expect(enterExam).toHaveBeenCalledTimes(2)
  expect(enterExam).toHaveBeenLastCalledWith(1, 'secret')
  response.resolve({ token: 'exam-one' }); await pending
  expect(vm.passwordDialogVisible).toBe(false); expect(push).toHaveBeenCalledExactlyOnceWith('/exam/1')
})
it('取消密码弹窗后旧确认操作不发送请求，新考试可以进入', async () => {
  const vm = mountPage(); await openPassword(vm)
  vm.passwordDialogVisible = false; await vm.handlePasswordSubmit()
  expect(enterExam).toHaveBeenCalledOnce()
  enterExam.mockResolvedValueOnce({ token: 'exam-two' }); await vm.handleEnterExam({ ...exam, id: 2 })
  expect(push).toHaveBeenCalledExactlyOnceWith('/exam/2')
})
it.each(['考试尚未开始', '考试已结束', '无权访问该考试'])('403 %s 不误开密码弹窗', async message => {
  enterExam.mockRejectedValueOnce(forbidden(message))
  const vm = mountPage(); await vm.handleEnterExam(exam)
  expect(vm.passwordDialogVisible).toBe(false); expect(ElMessage.error).toHaveBeenCalledWith(message)
  expect(vm.entering).toBe(false)
})
it('密码失败保留弹窗并解除提交锁，可以修改后重试', async () => {
  const vm = mountPage(); await openPassword(vm)
  enterExam.mockRejectedValueOnce(forbidden('考试密码错误')); await vm.handlePasswordSubmit()
  expect(vm.passwordDialogVisible).toBe(true); expect(vm.submittingPassword).toBe(false)
  vm.passwordInput = 'correct'; enterExam.mockResolvedValueOnce({ token: 'accepted' }); await vm.handlePasswordSubmit()
  expect(enterExam).toHaveBeenLastCalledWith(1, 'correct'); expect(push).toHaveBeenCalledOnce()
})
it('离开页面后成功响应不能覆盖令牌或导航', async () => {
  const response = deferred(); enterExam.mockReturnValue(response.promise)
  const vm = mountPage(); const pending = vm.handleEnterExam(exam)
  wrapper.unmount(); wrapper = undefined
  response.resolve({ token: 'stale' }); await pending
  expect(localStorage.getItem('token')).toBe('original'); expect(push).not.toHaveBeenCalled()
})
it('进入请求期间账号退出或令牌更新，旧响应不能恢复旧登录状态', async () => {
  const response = deferred(); enterExam.mockReturnValue(response.promise)
  const vm = mountPage(); const pending = vm.handleEnterExam(exam)
  localStorage.removeItem('token'); response.resolve({ token: 'stale' }); await pending
  expect(localStorage.getItem('token')).toBeNull(); expect(push).not.toHaveBeenCalled()
})
it('离开页面后失败响应不弹窗', async () => {
  const response = deferred(); enterExam.mockReturnValue(response.promise)
  const vm = mountPage(); const pending = vm.handleEnterExam(exam)
  wrapper.unmount(); wrapper = undefined
  response.reject(forbidden('考试密码错误')); await pending
  expect(vm.passwordDialogVisible).toBe(false); expect(ElMessage.error).not.toHaveBeenCalled()
})
it.each(['2026-06-15T09:59:59Z', '2026-06-15T11:00:00Z'])('未开始或结束 %s 时不能发送进入请求', async time => {
  vi.setSystemTime(new Date(time)); const vm = mountPage(); await vm.handleEnterExam(exam)
  expect(enterExam).not.toHaveBeenCalled(); expect(ElMessage.warning).toHaveBeenCalledOnce()
})
it('路由跳转完成前继续阻止新的进入请求', async () => {
  const navigation = deferred(); push.mockReturnValue(navigation.promise); enterExam.mockResolvedValue({ token: 'entered' })
  const vm = mountPage(); const pending = vm.handleEnterExam(exam); await flushPromises()
  await vm.handleEnterExam({ ...exam, id: 2 }); expect(enterExam).toHaveBeenCalledOnce()
  navigation.resolve(); await pending; expect(vm.entering).toBe(false)
})
