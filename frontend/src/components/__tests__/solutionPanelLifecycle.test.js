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
function mountPage(renderSlots = false) {
  wrapper = shallowMount(SolutionPanel, { props: { problemId: 1 }, global: {
    renderStubDefaultSlot: renderSlots,
    stubs: Object.fromEntries(['el-pagination','el-card','el-tag','el-icon','el-button','el-dialog','el-form','el-form-item','el-input','el-skeleton','el-empty'].map(name => [name,true])),
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
it('评论发送期间重复点击只创建一次评论', async () => {
  const post = deferred()
  request.mockImplementation(config => config.method === 'post' ? post.promise : Promise.resolve({ items: [], total: 0 }))
  mountPage(); await flushPromises()
  await wrapper.vm.openComments(solution(1))
  wrapper.vm.newComment = 'comment'
  const first = wrapper.vm.submitComment(), second = wrapper.vm.submitComment()
  post.resolve({}); await Promise.all([first, second])
  expect(request.mock.calls.filter(([config]) => config.method === 'post')).toHaveLength(1)
  expect(wrapper.vm.currentSolution.comment_count).toBe(1)
})
it('旧评论请求结束不能解除新题解评论的发送锁', async () => {
  const old = deferred(), current = deferred()
  request.mockImplementation(config => config.method === 'post' ? (config.url.includes('/1/') ? old.promise : current.promise) : Promise.resolve({ items: [], total: 0 }))
  mountPage(); await flushPromises()
  await wrapper.vm.openComments(solution(1))
  wrapper.vm.newComment = 'first'
  const first = wrapper.vm.submitComment()
  await wrapper.vm.openComments(solution(2))
  wrapper.vm.newComment = 'second'
  const second = wrapper.vm.submitComment()
  old.resolve({}); await first
  expect(wrapper.vm.submittingComment).toBe(true)
  current.resolve({}); await second
  expect(wrapper.vm.submittingComment).toBe(false)
})
it('评论发送失败解除发送锁，允许使用保留的输入重试', async () => {
  let fails = true
  request.mockImplementation(config => config.method === 'post' ? (fails ? Promise.reject(new Error('send failed')) : Promise.resolve({})) : Promise.resolve({ items: [], total: 0 }))
  mountPage(); await flushPromises()
  await wrapper.vm.openComments(solution(1))
  wrapper.vm.newComment = 'retry this'
  await wrapper.vm.submitComment()
  expect(wrapper.vm.submittingComment).toBe(false)
  expect(wrapper.vm.newComment).toBe('retry this')
  fails = false
  await wrapper.vm.submitComment()
  expect(wrapper.vm.currentSolution.comment_count).toBe(1)
  expect(wrapper.vm.newComment).toBe('')
})

it.each([
  ['toggleLike', 'pendingLikes', { liked: true, vote_count: 1 }, 'liked_by_me'],
  ['toggleFavorite', 'pendingFavorites', { favorited: true }, 'favorited_by_me'],
])('%s 在同一题解请求完成前阻止重复切换，完成后允许再次操作', async (method, pending, response, field) => {
  const post = deferred()
  mountPage(); await flushPromises()
  request.mockImplementation(config => config.method === 'post' ? post.promise : Promise.resolve({ items: [], total: 0 }))
  const item = solution(1)
  const first = wrapper.vm[method](item)
  await wrapper.vm[method]({ ...item })
  expect(request.mock.calls.filter(([config]) => config.method === 'post')).toHaveLength(1)
  expect(wrapper.vm[pending].has(1)).toBe(true)
  post.resolve(response); await first
  expect(item[field]).toBe(true)
  expect(wrapper.vm[pending].has(1)).toBe(false)
  await wrapper.vm[method](item)
  expect(request.mock.calls.filter(([config]) => config.method === 'post')).toHaveLength(2)
})
it.each(['toggleLike', 'toggleFavorite'])('%s 失败后允许重试', async method => {
  mountPage(); await flushPromises()
  request.mockRejectedValueOnce(new Error('failed')).mockResolvedValueOnce({ liked: true, favorited: true, vote_count: 1 })
  const item = solution(1)
  await wrapper.vm[method](item)
  await wrapper.vm[method](item)
  expect(request.mock.calls.filter(([config]) => config.method === 'post')).toHaveLength(2)
  expect(ElMessage.error).toHaveBeenCalledWith('failed')
})
it('不同题解和不同关系的请求互不阻塞', async () => {
  const post = deferred()
  mountPage(); await flushPromises()
  request.mockReturnValue(post.promise)
  const first = wrapper.vm.toggleLike(solution(1))
  const second = wrapper.vm.toggleLike(solution(2))
  const favorite = wrapper.vm.toggleFavorite(solution(1))
  expect(request.mock.calls.filter(([config]) => config.method === 'post')).toHaveLength(3)
  post.resolve({ liked: true, favorited: true, vote_count: 1 })
  await Promise.all([first, second, favorite])
})
it.each([
  ['toggleLike', 'pendingLikes'],
  ['toggleFavorite', 'pendingFavorites'],
])('%s 旧题目请求结束不能解除新题目的等待状态', async (method, pending) => {
  const old = deferred(), current = deferred()
  mountPage(); await flushPromises()
  request.mockImplementation(config => config.method === 'post' ? old.promise : Promise.resolve({ items: [], total: 0 }))
  const first = wrapper.vm[method](solution(1))
  await wrapper.setProps({ problemId: 2 }); await flushPromises()
  request.mockImplementation(config => config.method === 'post' ? current.promise : Promise.resolve({ items: [], total: 0 }))
  const second = wrapper.vm[method](solution(1))
  old.reject(new Error('old failed')); await first
  expect(wrapper.vm[pending].has(1)).toBe(true)
  expect(ElMessage.error).not.toHaveBeenCalled()
  current.resolve({ liked: true, favorited: true, vote_count: 1 }); await second
  expect(wrapper.vm[pending].has(1)).toBe(false)
})

it.each([
  ['toggleLike', { liked: true, vote_count: 3 }, { liked_by_me: true, vote_count: 3 }],
  ['toggleFavorite', { favorited: true }, { favorited_by_me: true }],
])('%s 与列表刷新交错时保留操作结果', async (method, response, expected) => {
  for (const reactionFirst of [true, false]) {
    wrapper?.unmount()
    request.mockResolvedValue({ items: [{ ...solution(1), liked_by_me: false, vote_count: 0, favorited_by_me: false }], total: 1 })
    mountPage(); await flushPromises()
    const original = wrapper.vm.solutions[0]
    const post = deferred(), listing = deferred()
    request.mockImplementation(config => config.method === 'post' ? post.promise : listing.promise)
    const mutation = wrapper.vm[method](original)
    const refresh = wrapper.vm.load()
    const resolveReaction = async () => { post.resolve(response); await mutation }
    const resolveList = async () => {
      listing.resolve({ items: [{ ...solution(1), title: 'updated', liked_by_me: false, vote_count: 0, favorited_by_me: false }], total: 1 })
      await refresh
    }
    if (reactionFirst) { await resolveReaction(); await resolveList() }
    else { await resolveList(); await resolveReaction() }
    expect(wrapper.vm.solutions[0]).toMatchObject({ title: 'updated', ...expected })
    expect(original).toMatchObject(expected)
  }
})
it('后续发起的刷新仍可更新其他用户增加的点赞数', async () => {
  request.mockResolvedValue({ items: [{ ...solution(1), liked_by_me: false, vote_count: 0 }], total: 1 })
  mountPage(); await flushPromises()
  request.mockResolvedValueOnce({ liked: true, vote_count: 1 })
  await wrapper.vm.toggleLike(wrapper.vm.solutions[0])
  request.mockResolvedValueOnce({ items: [{ ...solution(1), liked_by_me: true, vote_count: 5 }], total: 1 })
  await wrapper.vm.load()
  expect(wrapper.vm.solutions[0].vote_count).toBe(5)
})

it('题解与评论分页控件可以读取后续记录', async () => {
  request.mockImplementation(config => Promise.resolve({ items: [solution(config.params?.page || 1)], total: config.url.endsWith('/comments') ? 51 : 21 }))
  mountPage(true); await flushPromises()
  await wrapper.vm.openComments(wrapper.vm.solutions[0]); await nextTick()
  const pagers = wrapper.findAllComponents('el-pagination-stub')
  expect(pagers).toHaveLength(2)
  pagers[0].vm.$emit('current-change', 2)
  pagers[1].vm.$emit('current-change', 2)
  await flushPromises()
  expect(wrapper.vm.page).toBe(2)
  expect(wrapper.vm.commentsPage).toBe(2)
  expect(wrapper.vm.solutions[0].id).toBe(2)
  expect(wrapper.vm.comments[0].id).toBe(2)
  expect(request.mock.calls).toContainEqual([{ url: '/problems/1/solutions', method: 'get', params: { page: 2, page_size: 20 } }])
  expect(request.mock.calls).toContainEqual([{ url: '/problems/solutions/1/comments', method: 'get', params: { page: 2, page_size: 50 } }])
})
it.each([
  ['load', 'page', 'solutions', 20],
  ['loadComments', 'commentsPage', 'comments', 50],
])('%s 最后一页变空时回退到仍有记录的页面', async (method, pageField, itemsField, total) => {
  mountPage(); await flushPromises()
  await wrapper.vm.openComments(solution(1))
  wrapper.vm[pageField] = 2
  request.mockImplementation(config => Promise.resolve({ items: config.params.page === 1 ? [solution(10)] : [], total }))
  await wrapper.vm[method]()
  expect(wrapper.vm[pageField]).toBe(1)
  expect(wrapper.vm[itemsField][0].id).toBe(10)
})
it.each([
  ['load', 'page', 'loading'],
  ['loadComments', 'commentsPage', 'loadingComments'],
])('%s 翻页失败保留当前页并结束等待状态', async (method, pageField, loadingField) => {
  mountPage(); await flushPromises()
  await wrapper.vm.openComments(solution(1))
  request.mockRejectedValueOnce(new Error('page failed'))
  await wrapper.vm[method](2)
  expect(wrapper.vm[pageField]).toBe(1)
  expect(wrapper.vm[loadingField]).toBe(false)
})

it.each([50, 101])('发布评论后根据最新总数定位末页（已有 %i 条评论）', async count => {
  let posted = false
  request.mockImplementation(config => {
    if (config.method === 'post') { posted = true; return Promise.resolve({ id: count + 1 }) }
    if (!config.url.endsWith('/comments')) return Promise.resolve({ items: [], total: 0 })
    const total = posted ? count + 1 : 50
    const lastPage = Math.ceil(total / 50)
    return Promise.resolve({ items: [{ id: config.params.page === lastPage ? total : 1 }], total })
  })
  mountPage(); await flushPromises()
  await wrapper.vm.openComments(solution(1))
  wrapper.vm.newComment = 'new comment'
  await wrapper.vm.submitComment()
  expect(wrapper.vm.commentsPage).toBe(Math.ceil((count + 1) / 50))
  expect(wrapper.vm.comments[0].id).toBe(count + 1)
  expect(wrapper.vm.commentsTotal).toBe(count + 1)
})
