import type { AxiosRequestConfig } from 'axios'
import type { ComponentPublicInstance } from 'vue'
import type { TagResponse, SolutionListItemResponse, CommentResponse } from '@/types/community'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { nextTick } from 'vue'
const mocks = vi.hoisted(() => ({ request: vi.fn<(config: AxiosRequestConfig<Record<string, unknown>>) => Promise<unknown>>() }))
vi.mock('@/utils/request', () => ({ default: mocks.request }))
vi.mock('@/stores/user', () => ({ useUserStore: () => ({ user: { id: 1, role: 'teacher' } }) }))
vi.mock('element-plus', () => ({
  ElMessage: { error: vi.fn(), success: vi.fn(), warning: vi.fn() },
  ElMessageBox: { confirm: vi.fn() },
}))
import SolutionPanel from '../SolutionPanel.vue'
import request from '@/utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
let wrapper: ReturnType<typeof mountPage> | undefined
function mountedWrapper() {
  if (!wrapper) throw new Error('面板未挂载')
  return wrapper
}
// Vue 公共组件类型不公开 setup 状态，声明测试所需字段。
function setupState() {
  return mountedWrapper().vm as unknown as { solutions: SolutionListItemResponse[]; comments: CommentResponse[]; commentsTotal: number; total: number;
    currentSolution: SolutionListItemResponse | null; newComment: string; commentsDialog: boolean;
    editing: SolutionListItemResponse | null; form: { title: string; content: string; language: string };
    writeDialogVisible: boolean; savingSolution: boolean; submittingComment: boolean;
    pendingLikes: Set<number>; pendingFavorites: Set<number>; page: number; commentsPage: number;
    loading: boolean; loadingComments: boolean;
    openComments(item: SolutionListItemResponse): Promise<void>; openWrite(item?: SolutionListItemResponse): void;
    submitComment(): Promise<void>; deleteComment(id: number): Promise<void>; submitSolution(): Promise<void>;
    toggleLike(item: SolutionListItemResponse): Promise<void>; toggleFavorite(item: SolutionListItemResponse): Promise<void>;
    load(page?: number): Promise<void>; loadComments(page?: number): Promise<void>; }
}
const solution = (id: number): SolutionListItemResponse => ({
  id, title: String(id), content: 'content', comment_count: 0, problem_id: 1, author_id: 1,
  author_username: 'teacher', language: null, is_official: false, vote_count: 0,
  created_at: null, liked_by_me: false, favorited_by_me: false,
})
function deferred<T = unknown>() {
  let resolve!: (value: T) => void, reject!: (reason: unknown) => void
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
function mountPage(renderSlots = false) {
  const mounted = shallowMount(SolutionPanel, { props: { problemId: 1 }, global: {
    renderStubDefaultSlot: renderSlots,
    stubs: Object.fromEntries(['el-pagination','el-card','el-tag','el-icon','el-button','el-dialog','el-form','el-form-item','el-input','el-skeleton','el-empty'].map(name => [name,true])),
  } })
  wrapper = mounted
  return mounted
}
beforeEach(() => { vi.resetAllMocks(); mocks.request.mockResolvedValue({ items: [], total: 0 }) })
afterEach(() => { wrapper?.unmount(); wrapper = undefined })
it('切换题解后旧评论查询不能覆盖当前评论', async () => {
  const old = deferred()
  mocks.request.mockImplementation(({ url }) => url === '/problems/solutions/1/comments' ? old.promise : Promise.resolve({ items: [{ id: 2 }], total: 1 }))
  mountPage(); await flushPromises()
  const first = setupState().openComments(solution(1))
  await setupState().openComments(solution(2))
  old.resolve({ items: [{ id: 1 }], total: 10 }); await first
  expect(setupState().comments).toEqual([{ id: 2 }])
  expect(setupState().commentsTotal).toBe(1)
})
it('旧评论提交完成不能清空新题解输入或增加新题解评论数', async () => {
  const post = deferred()
  mocks.request.mockImplementation(config => config.method === 'post' ? post.promise : Promise.resolve({ items: [], total: 0 }))
  mountPage(); await flushPromises()
  await setupState().openComments(solution(1))
  const old = setupState().currentSolution
  setupState().newComment = 'old comment'
  const submission = setupState().submitComment()
  await setupState().openComments(solution(2))
  setupState().newComment = 'new comment'
  post.resolve({}); await submission
  expect(setupState().newComment).toBe('new comment')
  expect(setupState().currentSolution?.comment_count).toBe(0)
  expect(old?.comment_count).toBe(1)
  expect(mocks.request.mock.calls.filter(([config]) => config.url === '/problems/solutions/2/comments')).toHaveLength(1)
})
it('同一题解提交期间新写的草稿不会被清空', async () => {
  const post = deferred()
  mocks.request.mockImplementation(config => config.method === 'post' ? post.promise : Promise.resolve({ items: [], total: 0 }))
  mountPage(); await flushPromises()
  await setupState().openComments(solution(1))
  setupState().newComment = 'submitted'
  const submission = setupState().submitComment()
  setupState().newComment = 'next draft'
  post.resolve({}); await submission
  expect(setupState().newComment).toBe('next draft')
  expect(setupState().currentSolution?.comment_count).toBe(1)
})
it('删除确认期间切换题解不再发送旧评论删除请求', async () => {
  const confirmation = deferred<Awaited<ReturnType<typeof ElMessageBox.confirm>>>()
  vi.mocked(ElMessageBox.confirm).mockReturnValue(confirmation.promise)
  mountPage(); await flushPromises()
  await setupState().openComments(solution(1))
  const removal = setupState().deleteComment(10)
  await setupState().openComments(solution(2))
  confirmation.resolve('confirm' as Awaited<ReturnType<typeof ElMessageBox.confirm>>); await removal
  expect(mocks.request.mock.calls.some(([config]) => config.method === 'delete')).toBe(false)
})
it('切换题目清空旧窗口且旧题解列表不能覆盖新列表', async () => {
  const old = deferred()
  mocks.request.mockImplementation(({ url }) => url === '/problems/1/solutions' ? old.promise : Promise.resolve({ items: [solution(2)], total: 1 }))
  mountPage()
  setupState().openWrite(solution(1))
  await setupState().openComments(solution(1))
  await mountedWrapper().setProps({ problemId: 2 }); await flushPromises()
  old.resolve({ items: [solution(1)], total: 9 }); await flushPromises()
  expect(setupState().solutions[0].id).toBe(2)
  expect(setupState().total).toBe(1)
  expect(setupState().writeDialogVisible).toBe(false)
  expect(setupState().commentsDialog).toBe(false)
  expect(setupState().currentSolution).toBeNull()
})
it.each(['close','unmount'] as const)('评论请求在 %s 后失败不弹出旧错误', async action => {
  const comments = deferred()
  mocks.request.mockImplementation(({ url }) => url?.endsWith('/comments') ? comments.promise : Promise.resolve({ items: [], total: 0 }))
  mountPage(); await flushPromises()
  const loading = setupState().openComments(solution(1))
  if (action === 'close') { setupState().commentsDialog = false; await nextTick() }
  else { mountedWrapper().unmount(); wrapper = undefined }
  comments.reject(new Error('old error')); await loading
  expect(ElMessage.error).not.toHaveBeenCalled()
})
it('重复点击发布只发送一次写入请求', async () => {
  const post = deferred()
  mocks.request.mockImplementation(config => config.method === 'post' ? post.promise : Promise.resolve({ items: [], total: 0 }))
  mountPage(); await flushPromises()
  setupState().openWrite({ ...solution(1), title: 'valid title' })
  setupState().editing = null
  const first = setupState().submitSolution(), second = setupState().submitSolution()
  post.resolve({}); await Promise.all([first, second])
  expect(mocks.request.mock.calls.filter(([config]) => config.method === 'post')).toHaveLength(1)
})
it('旧保存完成不能关闭后来打开的编辑窗口', async () => {
  const put = deferred()
  mocks.request.mockImplementation(config => config.method === 'put' ? put.promise : Promise.resolve({ items: [], total: 0 }))
  mountPage(); await flushPromises()
  setupState().openWrite({ ...solution(1), title: 'valid title' })
  const first = setupState().submitSolution()
  setupState().openWrite(solution(2))
  put.resolve({}); await first
  expect(setupState().writeDialogVisible).toBe(true)
  expect(setupState().editing?.id).toBe(2)
  expect(setupState().form.title).toBe('2')
  expect(ElMessage.success).not.toHaveBeenCalled()
})
it('旧保存失败不能取消新窗口的保存状态或弹出旧错误', async () => {
  const old = deferred(), current = deferred()
  mocks.request.mockImplementation(config => config.method === 'put' ? (config.url?.endsWith('/1') ? old.promise : current.promise) : Promise.resolve({ items: [], total: 0 }))
  mountPage(); await flushPromises()
  setupState().openWrite({ ...solution(1), title: 'first title' })
  const first = setupState().submitSolution()
  setupState().openWrite({ ...solution(2), title: 'second title' })
  const second = setupState().submitSolution()
  old.reject(new Error('old save failed')); await first
  expect(setupState().savingSolution).toBe(true)
  expect(ElMessage.error).not.toHaveBeenCalled()
  current.resolve({}); await second
  expect(setupState().savingSolution).toBe(false)
  expect(setupState().writeDialogVisible).toBe(false)
})
it('当前保存失败后可重试且保留题解输入', async () => {
  mocks.request.mockImplementation(config => config.method === 'put' ? Promise.reject(new Error('save failed')) : Promise.resolve({ items: [], total: 0 }))
  mountPage(); await flushPromises()
  setupState().openWrite({ ...solution(1), title: 'valid title' })
  await setupState().submitSolution()
  expect(setupState().savingSolution).toBe(false)
  expect(setupState().writeDialogVisible).toBe(true)
  expect(setupState().form.title).toBe('valid title')
  expect(ElMessage.error).toHaveBeenCalledWith('save failed')
})
it('评论发送期间重复点击只创建一次评论', async () => {
  const post = deferred()
  mocks.request.mockImplementation(config => config.method === 'post' ? post.promise : Promise.resolve({ items: [], total: 0 }))
  mountPage(); await flushPromises()
  await setupState().openComments(solution(1))
  setupState().newComment = 'comment'
  const first = setupState().submitComment(), second = setupState().submitComment()
  post.resolve({}); await Promise.all([first, second])
  expect(mocks.request.mock.calls.filter(([config]) => config.method === 'post')).toHaveLength(1)
  expect(setupState().currentSolution?.comment_count).toBe(1)
})
it('旧评论请求结束不能解除新题解评论的发送锁', async () => {
  const old = deferred(), current = deferred()
  mocks.request.mockImplementation(config => config.method === 'post' ? (config.url?.includes('/1/') ? old.promise : current.promise) : Promise.resolve({ items: [], total: 0 }))
  mountPage(); await flushPromises()
  await setupState().openComments(solution(1))
  setupState().newComment = 'first'
  const first = setupState().submitComment()
  await setupState().openComments(solution(2))
  setupState().newComment = 'second'
  const second = setupState().submitComment()
  old.resolve({}); await first
  expect(setupState().submittingComment).toBe(true)
  current.resolve({}); await second
  expect(setupState().submittingComment).toBe(false)
})
it('评论发送失败解除发送锁，允许使用保留的输入重试', async () => {
  let fails = true
  mocks.request.mockImplementation(config => config.method === 'post' ? (fails ? Promise.reject(new Error('send failed')) : Promise.resolve({})) : Promise.resolve({ items: [], total: 0 }))
  mountPage(); await flushPromises()
  await setupState().openComments(solution(1))
  setupState().newComment = 'retry this'
  await setupState().submitComment()
  expect(setupState().submittingComment).toBe(false)
  expect(setupState().newComment).toBe('retry this')
  fails = false
  await setupState().submitComment()
  expect(setupState().currentSolution?.comment_count).toBe(1)
  expect(setupState().newComment).toBe('')
})

it.each([
  ['toggleLike', 'pendingLikes', { liked: true, vote_count: 1 }, 'liked_by_me'],
  ['toggleFavorite', 'pendingFavorites', { favorited: true }, 'favorited_by_me'],
] as const)('%s 在同一题解请求完成前阻止重复切换，完成后允许再次操作', async (method, pending, response, field) => {
  const post = deferred()
  mountPage(); await flushPromises()
  mocks.request.mockImplementation(config => config.method === 'post' ? post.promise : Promise.resolve({ items: [], total: 0 }))
  const item = solution(1)
  const first = setupState()[method](item)
  await setupState()[method]({ ...item })
  expect(mocks.request.mock.calls.filter(([config]) => config.method === 'post')).toHaveLength(1)
  expect(setupState()[pending].has(1)).toBe(true)
  post.resolve(response); await first
  expect(item[field]).toBe(true)
  expect(setupState()[pending].has(1)).toBe(false)
  await setupState()[method](item)
  expect(mocks.request.mock.calls.filter(([config]) => config.method === 'post')).toHaveLength(2)
})
it.each(['toggleLike', 'toggleFavorite'] as const)('%s 失败后允许重试', async method => {
  mountPage(); await flushPromises()
  mocks.request.mockRejectedValueOnce(new Error('failed')).mockResolvedValueOnce({ liked: true, favorited: true, vote_count: 1 })
  const item = solution(1)
  await setupState()[method](item)
  await setupState()[method](item)
  expect(mocks.request.mock.calls.filter(([config]) => config.method === 'post')).toHaveLength(2)
  expect(ElMessage.error).toHaveBeenCalledWith('failed')
})
it('不同题解和不同关系的请求互不阻塞', async () => {
  const post = deferred()
  mountPage(); await flushPromises()
  mocks.request.mockReturnValue(post.promise)
  const first = setupState().toggleLike(solution(1))
  const second = setupState().toggleLike(solution(2))
  const favorite = setupState().toggleFavorite(solution(1))
  expect(mocks.request.mock.calls.filter(([config]) => config.method === 'post')).toHaveLength(3)
  post.resolve({ liked: true, favorited: true, vote_count: 1 })
  await Promise.all([first, second, favorite])
})
it.each([
  ['toggleLike', 'pendingLikes'],
  ['toggleFavorite', 'pendingFavorites'],
] as const)('%s 旧题目请求结束不能解除新题目的等待状态', async (method, pending) => {
  const old = deferred(), current = deferred()
  mountPage(); await flushPromises()
  mocks.request.mockImplementation(config => config.method === 'post' ? old.promise : Promise.resolve({ items: [], total: 0 }))
  const first = setupState()[method](solution(1))
  await mountedWrapper().setProps({ problemId: 2 }); await flushPromises()
  mocks.request.mockImplementation(config => config.method === 'post' ? current.promise : Promise.resolve({ items: [], total: 0 }))
  const second = setupState()[method](solution(1))
  old.reject(new Error('old failed')); await first
  expect(setupState()[pending].has(1)).toBe(true)
  expect(ElMessage.error).not.toHaveBeenCalled()
  current.resolve({ liked: true, favorited: true, vote_count: 1 }); await second
  expect(setupState()[pending].has(1)).toBe(false)
})

it.each([
  ['toggleLike', { liked: true, vote_count: 3 }, { liked_by_me: true, vote_count: 3 }],
  ['toggleFavorite', { favorited: true }, { favorited_by_me: true }],
] as const)('%s 与列表刷新交错时保留操作结果', async (method, response, expected) => {
  for (const reactionFirst of [true, false]) {
    wrapper?.unmount()
    mocks.request.mockResolvedValue({ items: [{ ...solution(1), liked_by_me: false, vote_count: 0, favorited_by_me: false }], total: 1 })
    mountPage(); await flushPromises()
    const original = setupState().solutions[0]
    const post = deferred(), listing = deferred()
    mocks.request.mockImplementation(config => config.method === 'post' ? post.promise : listing.promise)
    const mutation = setupState()[method](original)
    const refresh = setupState().load()
    const resolveReaction = async () => { post.resolve(response); await mutation }
    const resolveList = async () => {
      listing.resolve({ items: [{ ...solution(1), title: 'updated', liked_by_me: false, vote_count: 0, favorited_by_me: false }], total: 1 })
      await refresh
    }
    if (reactionFirst) { await resolveReaction(); await resolveList() }
    else { await resolveList(); await resolveReaction() }
    expect(setupState().solutions[0]).toMatchObject({ title: 'updated', ...expected })
    expect(original).toMatchObject(expected)
  }
})
it('后续发起的刷新仍可更新其他用户增加的点赞数', async () => {
  mocks.request.mockResolvedValue({ items: [{ ...solution(1), liked_by_me: false, vote_count: 0 }], total: 1 })
  mountPage(); await flushPromises()
  mocks.request.mockResolvedValueOnce({ liked: true, vote_count: 1 })
  await setupState().toggleLike(setupState().solutions[0])
  mocks.request.mockResolvedValueOnce({ items: [{ ...solution(1), liked_by_me: true, vote_count: 5 }], total: 1 })
  await setupState().load()
  expect(setupState().solutions[0].vote_count).toBe(5)
})

it('题解与评论分页控件可以读取后续记录', async () => {
  mocks.request.mockImplementation(config => Promise.resolve({ items: [solution(config.params?.page || 1)], total: config.url?.endsWith('/comments') ? 51 : 21 }))
  mountPage(true); await flushPromises()
  await setupState().openComments(setupState().solutions[0]); await nextTick()
  const pagers = mountedWrapper().findAllComponents<ComponentPublicInstance>('el-pagination-stub')
  expect(pagers).toHaveLength(2)
  pagers[0].vm.$emit('current-change', 2)
  pagers[1].vm.$emit('current-change', 2)
  await flushPromises()
  expect(setupState().page).toBe(2)
  expect(setupState().commentsPage).toBe(2)
  expect(setupState().solutions[0].id).toBe(2)
  expect(setupState().comments[0].id).toBe(2)
  expect(mocks.request.mock.calls).toContainEqual([{ url: '/problems/1/solutions', method: 'get', params: { page: 2, page_size: 20 } }])
  expect(mocks.request.mock.calls).toContainEqual([{ url: '/problems/solutions/1/comments', method: 'get', params: { page: 2, page_size: 50 } }])
})
it.each([
  ['load', 'page', 'solutions', 20],
  ['loadComments', 'commentsPage', 'comments', 50],
] as const)('%s 最后一页变空时回退到仍有记录的页面', async (method, pageField, itemsField, total) => {
  mountPage(); await flushPromises()
  await setupState().openComments(solution(1))
  setupState()[pageField] = 2
  mocks.request.mockImplementation(config => Promise.resolve({ items: config.params.page === 1 ? [solution(10)] : [], total }))
  await setupState()[method]()
  expect(setupState()[pageField]).toBe(1)
  expect(setupState()[itemsField][0].id).toBe(10)
})
it.each([
  ['load', 'page', 'loading'],
  ['loadComments', 'commentsPage', 'loadingComments'],
] as const)('%s 翻页失败保留当前页并结束等待状态', async (method, pageField, loadingField) => {
  mountPage(); await flushPromises()
  await setupState().openComments(solution(1))
  mocks.request.mockRejectedValueOnce(new Error('page failed'))
  await setupState()[method](2)
  expect(setupState()[pageField]).toBe(1)
  expect(setupState()[loadingField]).toBe(false)
})

it.each([50, 101] as const)('发布评论后根据最新总数定位末页（已有 %i 条评论）', async count => {
  let posted = false
  mocks.request.mockImplementation(config => {
    if (config.method === 'post') { posted = true; return Promise.resolve({ id: count + 1 }) }
    if (!config.url?.endsWith('/comments')) return Promise.resolve({ items: [], total: 0 })
    const total = posted ? count + 1 : 50
    const lastPage = Math.ceil(total / 50)
    return Promise.resolve({ items: [{ id: config.params.page === lastPage ? total : 1 }], total })
  })
  mountPage(); await flushPromises()
  await setupState().openComments(solution(1))
  setupState().newComment = 'new comment'
  await setupState().submitComment()
  expect(setupState().commentsPage).toBe(Math.ceil((count + 1) / 50))
  expect(setupState().comments[0].id).toBe(count + 1)
  expect(setupState().commentsTotal).toBe(count + 1)
})
