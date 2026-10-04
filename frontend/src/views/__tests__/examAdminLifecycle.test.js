import { beforeEach, afterEach, expect, it, vi } from 'vitest'
import { shallowMount, flushPromises } from '@vue/test-utils'
vi.mock('@/api/exam', () => ({ getExamDetail: vi.fn(), getExamList: vi.fn(), updateExam: vi.fn(), createExam: vi.fn(), addExamProblem: vi.fn(), removeExamProblem: vi.fn(), deleteExam: vi.fn(), exportExamScores: vi.fn() }))
vi.mock('@/api/problem', () => ({ getProblemList: vi.fn() }))
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn(), success: vi.fn(), warning: vi.fn() } }))
import ExamAdminView from '../admin/ExamAdminView.vue'
import { getExamDetail, getExamList, updateExam, createExam, addExamProblem, removeExamProblem } from '@/api/exam'
import { getProblemList } from '@/api/problem'
import { ElMessage } from 'element-plus'
let wrapper
const exam = id => ({ id, title: `考试${id}`, description: '', start_time: '2090-06-15T10:00:00', end_time: '2090-06-15T11:00:00', is_visible: true, problems: [{ problem_id: 1 }] })
function deferred() {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
function mountPage() {
  wrapper = shallowMount(ExamAdminView, { global: { directives: { loading: () => {} }, stubs: Object.fromEntries(['el-icon','el-row','el-col','el-card','el-tag','el-link','el-table','el-table-column','el-button','el-divider','el-input','el-dialog','el-form','el-form-item','el-date-picker','el-switch','el-transfer','el-tooltip','el-popconfirm'].map(name => [name,true])) } })
  return wrapper.vm
}
beforeEach(() => {
  vi.resetAllMocks(); getExamList.mockResolvedValue([]); getProblemList.mockResolvedValue([])
  getExamDetail.mockImplementation(id => Promise.resolve(exam(id)))
  updateExam.mockResolvedValue({}); createExam.mockResolvedValue({ id: 3 }); addExamProblem.mockResolvedValue({}); removeExamProblem.mockResolvedValue({})
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined })
it.each(['resolve', 'reject'])('旧详情 %s 不能覆盖新窗口或解除新详情的加载状态', async outcome => {
  const old = deferred(), current = deferred(); getExamDetail.mockReturnValueOnce(old.promise).mockReturnValueOnce(current.promise)
  const vm = mountPage(); const first = vm.handleEdit({ id: 1 }); const second = vm.handleEdit({ id: 2 })
  old[outcome](outcome === 'resolve' ? exam(1) : new Error('old')); await first
  expect(vm.currentExamId).toBe(2); expect(vm.dialogLoading).toBe(true); expect(vm.form.title).toBe('')
  expect(vm.dialogVisible).toBe(true); expect(ElMessage.error).not.toHaveBeenCalled()
  current.resolve(exam(2)); await second; expect(vm.form.title).toBe('考试2'); expect(vm.dialogLoading).toBe(false)
})
it('关闭后重开创建窗口，旧详情不能填入创建表单', async () => {
  const old = deferred(); getExamDetail.mockReturnValueOnce(old.promise)
  const vm = mountPage(); const pending = vm.handleEdit({ id: 1 }); vm.dialogVisible = false; vm.handleCreate()
  old.resolve(exam(1)); await pending
  expect(vm.isEdit).toBe(false); expect(vm.currentExamId).toBeNull(); expect(vm.form.title).toBe(''); expect(vm.selectedProblemIds).toEqual([])
})
it('详情未加载和保存过程中重复点击不发送额外写请求', async () => {
  const detail = deferred(); getExamDetail.mockReturnValueOnce(detail.promise)
  const vm = mountPage(); const loading = vm.handleEdit({ id: 1 }); await vm.handleSubmit(); expect(updateExam).not.toHaveBeenCalled()
  detail.resolve(exam(1)); await loading
  const response = deferred(); updateExam.mockReturnValueOnce(response.promise)
  const pending = vm.handleSubmit(); await vm.handleSubmit(); expect(updateExam).toHaveBeenCalledOnce()
  response.resolve({}); await pending
})
it('旧保存完成使用提交时的选题，不读取新窗口并不会关闭它', async () => {
  const vm = mountPage(); await vm.handleEdit({ id: 1 }); vm.selectedProblemIds = [2]
  const response = deferred(); updateExam.mockReturnValueOnce(response.promise)
  const pending = vm.handleSubmit(); vm.dialogVisible = false; await vm.handleEdit({ id: 2 }); vm.selectedProblemIds = [3]
  response.resolve({}); await pending
  expect(addExamProblem).toHaveBeenCalledExactlyOnceWith(1, { problem_id: 2, score: 100 })
  expect(removeExamProblem).toHaveBeenCalledExactlyOnceWith(1, 1)
  expect(vm.dialogVisible).toBe(true); expect(vm.currentExamId).toBe(2); expect(vm.form.title).toBe('考试2')
  expect(vm.selectedProblemIds).toEqual([3]); expect(ElMessage.success).not.toHaveBeenCalled()
})
it('旧保存失败不能解除新保存的锁或提示旧错误', async () => {
  const vm = mountPage(); await vm.handleEdit({ id: 1 })
  const old = deferred(), current = deferred(); updateExam.mockReturnValueOnce(old.promise).mockReturnValueOnce(current.promise)
  const first = vm.handleSubmit(); vm.dialogVisible = false; await vm.handleEdit({ id: 2 }); const second = vm.handleSubmit()
  old.reject(new Error('old')); await first; expect(vm.submitting).toBe(true); expect(ElMessage.error).not.toHaveBeenCalled()
  current.resolve({}); await second; expect(vm.dialogVisible).toBe(false)
})
it('迟到列表不能覆盖保存后的新列表', async () => {
  const old = deferred(); getExamList.mockReturnValueOnce(old.promise)
  const vm = mountPage(); await vm.handleEdit({ id: 1 })
  getExamList.mockResolvedValueOnce([exam(1)]); await vm.handleSubmit(); await flushPromises()
  old.resolve([]); await flushPromises(); expect(vm.exams).toEqual([exam(1)])
})
it('离开页面后旧详情和写请求不再关闭窗口、提示或刷新', async () => {
  const response = deferred(); updateExam.mockReturnValueOnce(response.promise)
  const vm = mountPage(); await vm.handleEdit({ id: 1 }); const pending = vm.handleSubmit()
  wrapper.unmount(); wrapper = undefined; response.resolve({}); await pending
  expect(ElMessage.success).not.toHaveBeenCalled(); expect(getExamList).toHaveBeenCalledOnce()
})
it('创建请求携带所选题目快照，创建成功后关闭窗口', async () => {
  const vm = mountPage(); vm.handleCreate()
  Object.assign(vm.form, { title: '新考试', start_time: '2090-06-15T10:00:00Z', end_time: '2090-06-15T11:00:00Z' })
  vm.selectedProblemIds = [2, 1]
  const response = deferred(); createExam.mockReturnValueOnce(response.promise)
  const pending = vm.handleSubmit(); vm.selectedProblemIds = [3]
  expect(createExam.mock.calls[0][0].problem_ids).toEqual([2, 1])
  response.resolve({ id: 3 }); await pending
  expect(vm.dialogVisible).toBe(false); expect(addExamProblem).not.toHaveBeenCalled()
})
it('创建失败保留所选题目与表单供重试', async () => {
  const vm = mountPage(); vm.handleCreate()
  Object.assign(vm.form, { title: '新考试', start_time: '2090-06-15T10:00:00Z', end_time: '2090-06-15T11:00:00Z' })
  vm.selectedProblemIds = [2, 1]; createExam.mockRejectedValueOnce(new Error('failed'))
  await vm.handleSubmit()
  expect(vm.dialogVisible).toBe(true); expect(vm.selectedProblemIds).toEqual([2, 1]); expect(vm.submitting).toBe(false)
  await vm.handleSubmit(); expect(createExam.mock.calls[1][0].problem_ids).toEqual([2, 1])
})
