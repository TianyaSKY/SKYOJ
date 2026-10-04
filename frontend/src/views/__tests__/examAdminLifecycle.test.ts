import { examResponse, examStatus, problemResponse, deferred } from './fixtures'
import type { ExamDetailResponse, ExamListResponse, ExamProblemStatusResponse, ExamResponse, ExamTokenResponse } from '@/types/exam'
import { beforeEach, afterEach, expect, it, vi } from 'vitest'
import { shallowMount, flushPromises } from '@vue/test-utils'
vi.mock('@/api/exam', () => ({ getExamDetail: vi.fn(), getExamList: vi.fn(), updateExam: vi.fn(), createExam: vi.fn(), addExamProblem: vi.fn(), removeExamProblem: vi.fn(), deleteExam: vi.fn(), exportExamScores: vi.fn() }))
vi.mock('@/api/problem', () => ({ getProblemList: vi.fn() }))
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn(), success: vi.fn(), warning: vi.fn() } }))
import ExamAdminView from '../admin/ExamAdminView.vue'
import { getExamDetail, getExamList, updateExam, createExam, addExamProblem, removeExamProblem } from '@/api/exam'
import { getProblemList } from '@/api/problem'
import { ElMessage } from 'element-plus'
interface PageState { currentExamId: number | null; dialogLoading: boolean; form: { title: string; start_time: string; end_time: string; password: string };
  dialogVisible: boolean; isEdit: boolean; selectedProblemIds: number[]; submitting: boolean; exams: ExamListResponse[];
  problemSearchQuery: string; removePassword: boolean;
  handleEdit(exam: { id: number }): Promise<void>; handleCreate(): void; handleSubmit(): Promise<void>; }
let wrapper: ReturnType<typeof shallowMount> | undefined
function mountedWrapper() {
  if (!wrapper) throw new Error('考试页面未挂载')
  return wrapper
}
const exam = (id: number) => examResponse(id, { problems: [{ problem_id: 1, display_id: null, score: 100, title: '题目' }] })

function mountPage() {
  wrapper = shallowMount(ExamAdminView, { global: { directives: { loading: () => {} }, stubs: { ...Object.fromEntries(['el-icon','el-row','el-col','el-card','el-tag','el-link','el-table','el-table-column','el-button','el-divider','el-input','el-dialog','el-form','el-form-item','el-date-picker','el-switch','el-transfer','el-tooltip','el-popconfirm','el-checkbox'].map(name => [name,true])), ...Object.fromEntries(['el-dialog','el-form','el-row','el-col'].map(name => [name, { template: '<div><slot /></div>' }])), 'el-transfer': { name: 'TransferOptions', props: ['data'], template: '<div />' } } } })
  return wrapper.vm as unknown as PageState
}
beforeEach(() => {
  vi.resetAllMocks(); vi.mocked(getExamList).mockResolvedValue([]); vi.mocked(getProblemList).mockResolvedValue([])
  vi.mocked(getExamDetail).mockImplementation(id => Promise.resolve(exam(id)))
  vi.mocked(updateExam).mockResolvedValue(exam(1)); vi.mocked(createExam).mockResolvedValue(exam(3)); vi.mocked(addExamProblem).mockResolvedValue({ message: '添加成功' }); vi.mocked(removeExamProblem).mockResolvedValue({ message: '移除成功' })
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined })
it.each(['resolve', 'reject'])('旧详情 %s 不能覆盖新窗口或解除新详情的加载状态', async outcome => {
  const old = deferred<ExamDetailResponse>(), current = deferred<ExamDetailResponse>(); vi.mocked(getExamDetail).mockReturnValueOnce(old.promise).mockReturnValueOnce(current.promise)
  const vm = mountPage(); const first = vm.handleEdit({ id: 1 }); const second = vm.handleEdit({ id: 2 })
  if (outcome === 'resolve') old.resolve(exam(1)); else old.reject(new Error('old')); await first
  expect(vm.currentExamId).toBe(2); expect(vm.dialogLoading).toBe(true); expect(vm.form.title).toBe('')
  expect(vm.dialogVisible).toBe(true); expect(ElMessage.error).not.toHaveBeenCalled()
  current.resolve(exam(2)); await second; expect(vm.form.title).toBe('考试2'); expect(vm.dialogLoading).toBe(false)
})
it('关闭后重开创建窗口，旧详情不能填入创建表单', async () => {
  const old = deferred<ExamDetailResponse>(); vi.mocked(getExamDetail).mockReturnValueOnce(old.promise)
  const vm = mountPage(); const pending = vm.handleEdit({ id: 1 }); vm.dialogVisible = false; vm.handleCreate()
  old.resolve(exam(1)); await pending
  expect(vm.isEdit).toBe(false); expect(vm.currentExamId).toBeNull(); expect(vm.form.title).toBe(''); expect(vm.selectedProblemIds).toEqual([])
})
it('详情未加载和保存过程中重复点击不发送额外写请求', async () => {
  const detail = deferred<ExamDetailResponse>(); vi.mocked(getExamDetail).mockReturnValueOnce(detail.promise)
  const vm = mountPage(); const loading = vm.handleEdit({ id: 1 }); await vm.handleSubmit(); expect(updateExam).not.toHaveBeenCalled()
  detail.resolve(exam(1)); await loading
  const response = deferred<ExamResponse>(); vi.mocked(updateExam).mockReturnValueOnce(response.promise)
  const pending = vm.handleSubmit(); await vm.handleSubmit(); expect(updateExam).toHaveBeenCalledOnce()
  response.resolve(exam(1)); await pending
})
it('旧保存完成使用提交时的选题，不读取新窗口并不会关闭它', async () => {
  const vm = mountPage(); await vm.handleEdit({ id: 1 }); vm.selectedProblemIds = [2]
  const response = deferred<ExamResponse>(); vi.mocked(updateExam).mockReturnValueOnce(response.promise)
  const pending = vm.handleSubmit(); vm.dialogVisible = false; await vm.handleEdit({ id: 2 }); vm.selectedProblemIds = [3]
  response.resolve(exam(1)); await pending
  expect(vi.mocked(updateExam).mock.calls[0][1].problem_ids).toEqual([2])
  expect(addExamProblem).not.toHaveBeenCalled()
  expect(removeExamProblem).not.toHaveBeenCalled()
  expect(vm.dialogVisible).toBe(true); expect(vm.currentExamId).toBe(2); expect(vm.form.title).toBe('考试2')
  expect(vm.selectedProblemIds).toEqual([3]); expect(ElMessage.success).not.toHaveBeenCalled()
})
it('旧保存失败不能解除新保存的锁或提示旧错误', async () => {
  const vm = mountPage(); await vm.handleEdit({ id: 1 })
  const old = deferred<ExamResponse>(), current = deferred<ExamResponse>(); vi.mocked(updateExam).mockReturnValueOnce(old.promise).mockReturnValueOnce(current.promise)
  const first = vm.handleSubmit(); vm.dialogVisible = false; await vm.handleEdit({ id: 2 }); const second = vm.handleSubmit()
  old.reject(new Error('old')); await first; expect(vm.submitting).toBe(true); expect(ElMessage.error).not.toHaveBeenCalled()
  current.resolve(exam(2)); await second; expect(vm.dialogVisible).toBe(false)
})
it('迟到列表不能覆盖保存后的新列表', async () => {
  const old = deferred<ExamListResponse[]>(); vi.mocked(getExamList).mockReturnValueOnce(old.promise)
  const vm = mountPage(); await vm.handleEdit({ id: 1 })
  vi.mocked(getExamList).mockResolvedValueOnce([exam(1)]); await vm.handleSubmit(); await flushPromises()
  old.resolve([]); await flushPromises(); expect(vm.exams).toEqual([exam(1)])
})
it('离开页面后旧详情和写请求不再关闭窗口、提示或刷新', async () => {
  const response = deferred<ExamResponse>(); vi.mocked(updateExam).mockReturnValueOnce(response.promise)
  const vm = mountPage(); await vm.handleEdit({ id: 1 }); const pending = vm.handleSubmit()
  mountedWrapper().unmount(); wrapper = undefined; response.resolve(exam(1)); await pending
  expect(ElMessage.success).not.toHaveBeenCalled(); expect(getExamList).toHaveBeenCalledOnce()
})
it('创建请求携带所选题目快照，创建成功后关闭窗口', async () => {
  const vm = mountPage(); vm.handleCreate()
  Object.assign(vm.form, { title: '新考试', start_time: '2090-06-15T10:00:00Z', end_time: '2090-06-15T11:00:00Z' })
  vm.selectedProblemIds = [2, 1]
  const response = deferred<ExamResponse>(); vi.mocked(createExam).mockReturnValueOnce(response.promise)
  const pending = vm.handleSubmit(); vm.selectedProblemIds = [3]
  expect(vi.mocked(createExam).mock.calls[0][0].problem_ids).toEqual([2, 1])
  response.resolve(exam(3)); await pending
  expect(vm.dialogVisible).toBe(false); expect(addExamProblem).not.toHaveBeenCalled()
})
it('创建失败保留所选题目与表单供重试', async () => {
  const vm = mountPage(); vm.handleCreate()
  Object.assign(vm.form, { title: '新考试', start_time: '2090-06-15T10:00:00Z', end_time: '2090-06-15T11:00:00Z' })
  vm.selectedProblemIds = [2, 1]; vi.mocked(createExam).mockRejectedValueOnce(new Error('failed'))
  await vm.handleSubmit()
  expect(vm.dialogVisible).toBe(true); expect(vm.selectedProblemIds).toEqual([2, 1]); expect(vm.submitting).toBe(false)
  await vm.handleSubmit(); expect(vi.mocked(createExam).mock.calls[1][0].problem_ids).toEqual([2, 1])
})
it('顶部搜索按题目标题或 ID 筛选实际选题器，同时保留已选题目', async () => {
  vi.mocked(getProblemList).mockResolvedValueOnce([problemResponse({ id: 1, title: 'A+B' }), problemResponse({ id: 2, title: 'Graph PATH' }), problemResponse({ id: 3, title: '字符串' })])
  const vm = mountPage(); await flushPromises(); vm.handleCreate()
  vm.selectedProblemIds = [1]; vm.problemSearchQuery = ' path '; await flushPromises()
  const transfer = mountedWrapper().findComponent({ name: 'TransferOptions' })
  expect(transfer.props('data').map((item: { id: number }) => item.id)).toEqual([1, 2])
  expect(vm.selectedProblemIds).toEqual([1])
  vm.problemSearchQuery = '3'; await flushPromises()
  expect(transfer.props('data').map((item: { id: number }) => item.id)).toEqual([1, 3])
  vm.problemSearchQuery = '无匹配'; await flushPromises()
  expect(transfer.props('data').map((item: { id: number }) => item.id)).toEqual([1])
  vm.problemSearchQuery = ''; await flushPromises()
  expect(transfer.props('data')).toHaveLength(3)
})
it('新建或编辑另一场考试时清空旧搜索，恢复完整候选题库', async () => {
  vi.mocked(getProblemList).mockResolvedValueOnce([problemResponse({ id: 1, title: 'A+B' }), problemResponse({ id: 2, title: 'Graph' })])
  const vm = mountPage(); await flushPromises(); vm.handleCreate(); vm.problemSearchQuery = 'Graph'
  await vm.handleEdit({ id: 1 })
  expect(vm.problemSearchQuery).toBe('')
  expect(mountedWrapper().findComponent({ name: 'TransferOptions' }).props('data')).toHaveLength(2)
  vm.problemSearchQuery = '无匹配'; vm.dialogVisible = false; vm.handleCreate()
  expect(vm.problemSearchQuery).toBe('')
})
it('编辑有密码考试时留空保留，填写替换，明确勾选后移除', async () => {
  const vm = mountPage()
  const protectedExam = { ...exam(1), has_password: true }
  vi.mocked(getExamDetail).mockResolvedValueOnce(protectedExam); await vm.handleEdit({ id: 1 })
  expect(vm.form.password).toBe(''); vm.form.title = '仅改标题'
  await vm.handleSubmit(); expect(vi.mocked(updateExam).mock.calls[0][1]).not.toHaveProperty('password')
  vi.mocked(getExamDetail).mockResolvedValueOnce(protectedExam); await vm.handleEdit({ id: 1 })
  vm.form.password = 'replacement'; await vm.handleSubmit()
  expect(vi.mocked(updateExam).mock.calls[1][1].password).toBe('replacement')
  vi.mocked(getExamDetail).mockResolvedValueOnce(protectedExam); await vm.handleEdit({ id: 1 })
  vm.removePassword = true; await vm.handleSubmit()
  expect(vi.mocked(updateExam).mock.calls[2][1].password).toBe('')
})
it('取消移除密码选择、切换考试或重新创建不会沿用旧的移除标记', async () => {
  const vm = mountPage(); vi.mocked(getExamDetail).mockResolvedValueOnce({ ...exam(1), has_password: true })
  await vm.handleEdit({ id: 1 }); vm.removePassword = true; vm.removePassword = false
  await vm.handleSubmit(); expect(vi.mocked(updateExam).mock.calls[0][1]).not.toHaveProperty('password')
  vi.mocked(getExamDetail).mockResolvedValueOnce({ ...exam(1), has_password: true }); await vm.handleEdit({ id: 1 })
  vm.removePassword = true; await vm.handleEdit({ id: 2 }); expect(vm.removePassword).toBe(false)
  vm.removePassword = true; vm.dialogVisible = false; vm.handleCreate(); expect(vm.removePassword).toBe(false)
})
