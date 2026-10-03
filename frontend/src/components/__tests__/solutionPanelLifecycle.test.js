import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { nextTick } from 'vue'
vi.mock('@/utils/request', () => ({ default: vi.fn() }))
vi.mock('@/stores/user', () => ({ useUserStore: () => ({ user: { id: 1, role: 'teacher' } }) }))
vi.mock('element-plus', () => ({
  ElMessage: { error: vi.fn(), success: vi.fn(), warning: vi.fn() },
  ElMessageBox: { confirm: vi.fn() },
}))
import SolutionPanel from '../SolutionPanel.vue'
import request from '@/utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
let wrapper
const solution = id => ({ id, title: String(id), content: 'content', comment_count: 0 })
function deferred() {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
function mountPage() {
  wrapper = shallowMount(SolutionPanel, { props: { problemId: 1 }, global: {
    stubs: Object.fromEntries(['el-card','el-tag','el-icon','el-button','el-dialog','el-form','el-form-item','el-input','el-skeleton','el-empty'].map(name => [name,true])),
  } })
}
beforeEach(() => { vi.resetAllMocks(); request.mockResolvedValue({ items: [], total: 0 }) })
afterEach(() => { wrapper?.unmount(); wrapper = undefined })
it('切换题解后旧评论查询不能覆盖当前评论', async () => {
  const old = deferred()
  request.mockImplementation(({ url }) => url === '/problems/solutions/1/comments' ? old.promise : Promise.resolve({ items: [{ id: 2 }], total: 1 }))
  mountPage(); await flushPromises()
  const first = wrapper.vm.openComments(solution(1))
  await wrapper.vm.openComments(solution(2))
  old.resolve({ items: [{ id: 1 }], total: 10 }); await first
  expect(wrapper.vm.comments).toEqual([{ id: 2 }])
  expect(wrapper.vm.commentsTotal).toBe(1)
})
it('旧评论提交完成不能清空新题解输入或增加新题解评论数', async () => {
  const post = deferred()
  request.mockImplementation(config => config.method === 'post' ? post.promise : Promise.resolve({ items: [], total: 0 }))
  mountPage(); await flushPromises()
  await wrapper.vm.openComments(solution(1))
  const old = wrapper.vm.currentSolution
  wrapper.vm.newComment = 'old comment'
  const submission = wrapper.vm.submitComment()
  await wrapper.vm.openComments(solution(2))
  wrapper.vm.newComment = 'new comment'
  post.resolve({}); await submission
  expect(wrapper.vm.newComment).toBe('new comment')
  expect(wrapper.vm.currentSolution.comment_count).toBe(0)
  expect(old.comment_count).toBe(1)
  expect(request.mock.calls.filter(([config]) => config.url === '/problems/solutions/2/comments')).toHaveLength(1)
})
it('同一题解提交期间新写的草稿不会被清空', async () => {
  const post = deferred()
  request.mockImplementation(config => config.method === 'post' ? post.promise : Promise.resolve({ items: [], total: 0 }))
  mountPage(); await flushPromises()
  await wrapper.vm.openComments(solution(1))
  wrapper.vm.newComment = 'submitted'
  const submission = wrapper.vm.submitComment()
  wrapper.vm.newComment = 'next draft'
  post.resolve({}); await submission
  expect(wrapper.vm.newComment).toBe('next draft')
  expect(wrapper.vm.currentSolution.comment_count).toBe(1)
})
it('删除确认期间切换题解不再发送旧评论删除请求', async () => {
  const confirmation = deferred()
  ElMessageBox.confirm.mockReturnValue(confirmation.promise)
  mountPage(); await flushPromises()
  await wrapper.vm.openComments(solution(1))
  const removal = wrapper.vm.deleteComment(10)
  await wrapper.vm.openComments(solution(2))
  confirmation.resolve('confirm'); await removal
  expect(request.mock.calls.some(([config]) => config.method === 'delete')).toBe(false)
})
it('切换题目清空旧窗口且旧题解列表不能覆盖新列表', async () => {
  const old = deferred()
  request.mockImplementation(({ url }) => url === '/problems/1/solutions' ? old.promise : Promise.resolve({ items: [solution(2)], total: 1 }))
  mountPage()
  wrapper.vm.openWrite(solution(1))
  await wrapper.vm.openComments(solution(1))
  await wrapper.setProps({ problemId: 2 }); await flushPromises()
  old.resolve({ items: [solution(1)], total: 9 }); await flushPromises()
  expect(wrapper.vm.solutions[0].id).toBe(2)
  expect(wrapper.vm.total).toBe(1)
  expect(wrapper.vm.writeDialogVisible).toBe(false)
  expect(wrapper.vm.commentsDialog).toBe(false)
  expect(wrapper.vm.currentSolution).toBeNull()
})
it.each(['close','unmount'])('评论请求在 %s 后失败不弹出旧错误', async action => {
  const comments = deferred()
  request.mockImplementation(({ url }) => url.endsWith('/comments') ? comments.promise : Promise.resolve({ items: [], total: 0 }))
  mountPage(); await flushPromises()
  const loading = wrapper.vm.openComments(solution(1))
  if (action === 'close') { wrapper.vm.commentsDialog = false; await nextTick() }
  else { wrapper.unmount(); wrapper = undefined }
  comments.reject(new Error('old error')); await loading
  expect(ElMessage.error).not.toHaveBeenCalled()
})
it('重复点击发布只发送一次写入请求', async () => {
  const post = deferred()
  request.mockImplementation(config => config.method === 'post' ? post.promise : Promise.resolve({ items: [], total: 0 }))
  mountPage(); await flushPromises()
  wrapper.vm.openWrite({ ...solution(1), title: 'valid title' })
  wrapper.vm.editing = null
  const first = wrapper.vm.submitSolution(), second = wrapper.vm.submitSolution()
  post.resolve({}); await Promise.all([first, second])
  expect(request.mock.calls.filter(([config]) => config.method === 'post')).toHaveLength(1)
})
it('旧保存完成不能关闭后来打开的编辑窗口', async () => {
  const put = deferred()
  request.mockImplementation(config => config.method === 'put' ? put.promise : Promise.resolve({ items: [], total: 0 }))
  mountPage(); await flushPromises()
  wrapper.vm.openWrite({ ...solution(1), title: 'valid title' })
  const first = wrapper.vm.submitSolution()
  wrapper.vm.openWrite(solution(2))
  put.resolve({}); await first
  expect(wrapper.vm.writeDialogVisible).toBe(true)
  expect(wrapper.vm.editing.id).toBe(2)
  expect(wrapper.vm.form.title).toBe('2')
  expect(ElMessage.success).not.toHaveBeenCalled()
})
it('旧保存失败不能取消新窗口的保存状态或弹出旧错误', async () => {
  const old = deferred(), current = deferred()
  request.mockImplementation(config => config.method === 'put' ? (config.url.endsWith('/1') ? old.promise : current.promise) : Promise.resolve({ items: [], total: 0 }))
  mountPage(); await flushPromises()
  wrapper.vm.openWrite({ ...solution(1), title: 'first title' })
  const first = wrapper.vm.submitSolution()
  wrapper.vm.openWrite({ ...solution(2), title: 'second title' })
  const second = wrapper.vm.submitSolution()
  old.reject(new Error('old save failed')); await first
  expect(wrapper.vm.savingSolution).toBe(true)
  expect(ElMessage.error).not.toHaveBeenCalled()
  current.resolve({}); await second
  expect(wrapper.vm.savingSolution).toBe(false)
  expect(wrapper.vm.writeDialogVisible).toBe(false)
})
it('当前保存失败后可重试且保留题解输入', async () => {
  request.mockImplementation(config => config.method === 'put' ? Promise.reject(new Error('save failed')) : Promise.resolve({ items: [], total: 0 }))
  mountPage(); await flushPromises()
  wrapper.vm.openWrite({ ...solution(1), title: 'valid title' })
  await wrapper.vm.submitSolution()
  expect(wrapper.vm.savingSolution).toBe(false)
  expect(wrapper.vm.writeDialogVisible).toBe(true)
  expect(wrapper.vm.form.title).toBe('valid title')
  expect(ElMessage.error).toHaveBeenCalledWith('save failed')
})
