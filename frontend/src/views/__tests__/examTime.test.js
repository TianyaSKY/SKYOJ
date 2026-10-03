vi.mock('@/utils/request', () => ({ default: { post: vi.fn() } }))
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
import dayjs from 'dayjs'
vi.mock('vue-router', () => ({ useRoute: () => ({ params: { id: 1 } }), useRouter: () => ({ push: vi.fn() }) }))
vi.mock('@/api/exam', () => ({ getExamList: vi.fn(), getExamDetail: vi.fn(), getMyExamStatus: vi.fn(), enterExam: vi.fn(), exitExam: vi.fn(), createExam: vi.fn(), updateExam: vi.fn(), deleteExam: vi.fn(), exportExamScores: vi.fn(), addExamProblem: vi.fn(), removeExamProblem: vi.fn() }))
vi.mock('@/api/problem', () => ({ getProblemList: vi.fn() }))
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn(), success: vi.fn(), warning: vi.fn() }, ElMessageBox: { alert: vi.fn(), confirm: vi.fn() } }))
import ExamView from '../ExamView.vue'
import ExamDetailView from '../ExamDetailView.vue'
import ExamAdminView from '../admin/ExamAdminView.vue'
import { getExamList, getExamDetail, getMyExamStatus, updateExam } from '@/api/exam'
import { getProblemList } from '@/api/problem'
import { ElMessageBox } from 'element-plus'
let wrapper
const exam = { id: 1, title: '考试', description: '', start_time: '2026-06-15T10:00:01', end_time: '2026-06-15T10:00:03', problems: [], is_visible: true, contest_type: 'icpc' }
function mountPage(component) {
  wrapper = shallowMount(component, { global: { directives: { loading: () => {} }, stubs: Object.fromEntries(['el-icon','el-tag','el-table','el-table-column','el-link','el-button','el-card','el-col','el-row','el-progress','el-divider','el-alert','el-input','el-dialog','el-form','el-form-item','el-date-picker','el-switch','el-transfer','el-tooltip','el-popconfirm'].map(name => [name, true])) } })
  return wrapper.vm
}
beforeEach(() => {
  setActivePinia(createPinia())
  vi.resetAllMocks()
  vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval', 'Date'] })
  vi.setSystemTime(new Date('2026-06-15T10:00:00Z'))
  getExamList.mockResolvedValue([exam]); getExamDetail.mockResolvedValue(exam)
  getMyExamStatus.mockResolvedValue([]); getProblemList.mockResolvedValue([]); updateExam.mockResolvedValue({})
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined; vi.clearAllTimers(); vi.useRealTimers() })
it('详情按 UTC 倒计时，开考和结束时更新标签，结束只提示一次', async () => {
  const vm = mountPage(ExamDetailView); await flushPromises()
  expect(vm.remainingTimeStr).toBe('00:00:01'); expect(vm.timerStatus.label).toBe('距离开始')
  await vi.advanceTimersByTimeAsync(1000)
  expect(vm.timerStatus.label).toBe('剩余时间'); expect(vm.remainingTimeStr).toBe('00:00:02')
  await vi.advanceTimersByTimeAsync(2000)
  expect(vm.timerStatus.label).toBe('已结束'); expect(vm.remainingTimeStr).toBe('00:00:00')
  expect(ElMessageBox.alert).toHaveBeenCalledOnce()
  await vi.advanceTimersByTimeAsync(2000); expect(ElMessageBox.alert).toHaveBeenCalledOnce()
  wrapper.unmount(); wrapper = undefined; expect(vi.getTimerCount()).toBe(0)
})
it('列表随时间更新，结束瞬间移除过期考试', async () => {
  const vm = mountPage(ExamView); await flushPromises()
  expect(vm.getExamStatus(exam).text).toBe('未开始'); expect(vm.filteredExams).toHaveLength(1)
  await vi.advanceTimersByTimeAsync(1000); expect(vm.getExamStatus(exam).text).toBe('进行中')
  await vi.advanceTimersByTimeAsync(2000)
  expect(vm.getExamStatus(exam).text).toBe('已结束'); expect(vm.filteredExams).toEqual([])
})
it('已结束考试首次加载也提示退出', async () => {
  vi.setSystemTime(new Date('2026-06-15T10:00:04Z'))
  mountPage(ExamDetailView); await flushPromises(); expect(ElMessageBox.alert).toHaveBeenCalledOnce()
})
it('离开详情后迟到响应不能启动时钟或结束提示', async () => {
  let resolve
  getExamDetail.mockReturnValue(new Promise(done => { resolve = done }))
  mountPage(ExamDetailView); wrapper.unmount(); wrapper = undefined
  resolve(exam); await flushPromises(); await vi.advanceTimersByTimeAsync(5000)
  expect(vi.getTimerCount()).toBe(0); expect(ElMessageBox.alert).not.toHaveBeenCalled(); expect(getMyExamStatus).not.toHaveBeenCalled()
})
it('列表、详情和管理页按本地时间展示同一 UTC 时刻', async () => {
  for (const component of [ExamView, ExamDetailView, ExamAdminView]) {
    const vm = mountPage(component); await flushPromises()
    const pattern = component === ExamView ? 'YYYY-MM-DD HH:mm' : component === ExamDetailView ? 'YYYY-MM-DD HH:mm:ss' : 'MM-DD HH:mm'
    expect((vm.formatTime || vm.formatTimeShort)(exam.start_time)).toBe(dayjs(new Date(`${exam.start_time}Z`)).format(pattern))
    wrapper.unmount(); wrapper = undefined
  }
})
it('编辑直接保存保留时刻，日期选择器发送带时区时间，管理状态实时更新', async () => {
  const vm = mountPage(ExamAdminView); await flushPromises(); await vm.handleEdit(exam)
  expect(vm.timeRange.map(date => date.toISOString())).toEqual(['2026-06-15T10:00:01.000Z', '2026-06-15T10:00:03.000Z'])
  await vm.handleSubmit()
  expect(updateExam.mock.calls[0][1]).toMatchObject({ start_time: '2026-06-15T10:00:01.000Z', end_time: '2026-06-15T10:00:03.000Z' })
  const start = new Date(2026, 5, 16, 18, 30), end = new Date(2026, 5, 16, 19, 30)
  vm.handleTimeChange([start, end]); expect(vm.form.start_time).toBe(start.toISOString()); expect(vm.form.end_time).toBe(end.toISOString())
  expect(vm.getExamStatus(exam).label).toBe('未开始')
  await vi.advanceTimersByTimeAsync(1000); expect(vm.getExamStatus(exam).label).toBe('进行中')
  await vi.advanceTimersByTimeAsync(2000); expect(vm.getExamStatus(exam).label).toBe('已结束')
})
