import { deferred } from './fixtures'
import type { AxiosRequestConfig } from 'axios'
import type { ComponentPublicInstance } from 'vue'
import type { CachedUser } from '@/schemas/user'
import type {
  UserProfileResponse,
  UserSubmissionResponse,
  UploadAvatarResponse,
} from '@/types/user'
import type { WrongBookItemResponse, WrongBookStatsResponse } from '@/types/wrongBook'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { nextTick, reactive } from 'vue'
const state = vi.hoisted(() => ({
  route: { params: { id: '2' } as { id?: string | string[] } },
  user: { user: {} as CachedUser },
  sys: { practice: true },
}))
vi.mock('vue-router', () => ({ useRoute: () => state.route }))
vi.mock('@/stores/user', () => ({ useUserStore: () => state.user }))
vi.mock('@/stores/sys', () => ({ useSysStore: () => state.sys }))
vi.mock('@/api/user', () => ({
  getUserProfile: vi.fn(),
  getUserSubmissions: vi.fn(),
  uploadAvatar: vi.fn(),
}))
const mocks = vi.hoisted(() => ({
  request: vi.fn<(config: AxiosRequestConfig<Record<string, unknown>>) => Promise<unknown>>(),
}))
vi.mock('@/utils/request', () => ({ default: mocks.request }))
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn(), success: vi.fn() } }))
import ProfileView from '../ProfileView.vue'
import { getUserProfile, getUserSubmissions, uploadAvatar } from '@/api/user'
import request from '@/utils/request'
import { ElMessage } from 'element-plus'
let wrapper: ReturnType<typeof mountPage> | undefined
const submission = (id: number): UserSubmissionResponse => ({
  id,
  problem_id: 1,
  problem_title: '题目',
  status: 'Accepted',
  score: 100,
  language: 'python',
  created_at: null,
  exam_id: null,
})
function mountedWrapper() {
  if (!wrapper) throw new Error('资料页面未挂载')
  return wrapper
}
// 测试工具可访问 setup 字段，组件公共类型不公开这些状态。
function setupState() {
  return mountedWrapper().vm as unknown as {
    targetUser: Partial<UserProfileResponse>
    submissions: UserSubmissionResponse[]
    loading: boolean
    uploadingAvatar: boolean
    wbPage: number
    wbItems: WrongBookItemResponse[]
    wbStats: WrongBookStatsResponse
    wbLoading: boolean
    pendingReviews: Set<number>
    handleAvatarUpload(options: { file: File }): Promise<void>
    fetchWrongBook(page?: number): Promise<void>
    toggleReview(
      item: Pick<WrongBookItemResponse, 'id' | 'reviewed'> & Partial<WrongBookItemResponse>,
    ): Promise<void>
  }
}

function mountPage(renderCards = false) {
  const mounted = shallowMount(ProfileView, {
    global: {
      directives: { loading: () => {} },
      stubs: Object.fromEntries(
        [
          'el-pagination',
          'el-card',
          'el-avatar',
          'el-upload',
          'el-icon',
          'el-tag',
          'el-table',
          'el-table-column',
          'el-button',
          'el-link',
          'el-empty',
        ].map((name) => [
          name,
          name === 'el-card' && renderCards ? { template: '<div><slot /></div>' } : true,
        ]),
      ),
    },
  })
  wrapper = mounted
  return mounted
}
beforeEach(() => {
  vi.resetAllMocks()
  localStorage.clear()
  state.route = reactive({ params: { id: '2' } })
  state.user = reactive({
    user: { id: 1, username: 'self', role: 'student', avatar: 'self-avatar' },
  })
  state.sys = reactive({ practice: true })
  vi.mocked(getUserProfile).mockImplementation((id) =>
    Promise.resolve({
      id: Number(id),
      username: String(id),
      avatar: `avatar-${id}`,
      role: 'student',
    }),
  )
  vi.mocked(getUserSubmissions).mockResolvedValue([])
  mocks.request.mockResolvedValue({ items: [], total: 0, accepted: 0, unresolved: 0, reviewed: 0 })
})
afterEach(() => {
  wrapper?.unmount()
  wrapper = undefined
})
it('旧用户资料不能覆盖新用户资料或继续读取旧用户提交', async () => {
  const old = deferred<UserProfileResponse>()
  vi.mocked(getUserProfile).mockReturnValueOnce(old.promise)
  mountPage()
  state.route.params.id = '3'
  await nextTick()
  await flushPromises()
  old.resolve({ id: 2, username: 'old', role: 'student', avatar: null })
  await flushPromises()
  expect(setupState().targetUser.id).toBe(3)
  expect(getUserSubmissions).toHaveBeenCalledExactlyOnceWith(3)
})
it('旧用户提交失败不能显示错误或结束新请求的等待状态', async () => {
  const old = deferred<UserSubmissionResponse[]>(),
    current = deferred<UserSubmissionResponse[]>()
  vi.mocked(getUserSubmissions)
    .mockReturnValueOnce(old.promise)
    .mockReturnValueOnce(current.promise)
  mountPage()
  await flushPromises()
  state.route.params.id = '3'
  await nextTick()
  await flushPromises()
  expect(setupState().submissions).toEqual([])
  old.reject(new Error('old failed'))
  await flushPromises()
  expect(setupState().loading).toBe(true)
  expect(ElMessage.error).not.toHaveBeenCalled()
  current.resolve([submission(3)])
  await flushPromises()
  expect(setupState().submissions).toEqual([submission(3)])
  expect(setupState().loading).toBe(false)
})
it('考试模式仍加载资料，模式变化后重新按权限加载提交历史', async () => {
  state.sys.practice = false
  mountPage()
  await flushPromises()
  expect(setupState().targetUser.id).toBe(2)
  expect(getUserSubmissions).not.toHaveBeenCalled()
  state.sys.practice = true
  await nextTick()
  await flushPromises()
  expect(getUserSubmissions).toHaveBeenCalledExactlyOnceWith(2)
})
it('切换为考试模式后旧历史响应不能恢复已隐藏的提交记录', async () => {
  const old = deferred<UserSubmissionResponse[]>()
  vi.mocked(getUserSubmissions).mockReturnValueOnce(old.promise)
  mountPage()
  await flushPromises()
  state.sys.practice = false
  await nextTick()
  await flushPromises()
  old.resolve([submission(1)])
  await flushPromises()
  expect(setupState().submissions).toEqual([])
  expect(setupState().targetUser.id).toBe(2)
})
it('头像上传后切换用户不改写新用户头像，但更新上传账户缓存', async () => {
  delete state.route.params.id
  const upload = deferred<UploadAvatarResponse>()
  vi.mocked(uploadAvatar).mockReturnValue(upload.promise)
  mountPage()
  await flushPromises()
  const options = { file: new File(['avatar'], 'avatar.png', { type: 'image/png' }) }
  const first = setupState().handleAvatarUpload(options)
  await setupState().handleAvatarUpload(options)
  expect(uploadAvatar).toHaveBeenCalledOnce()
  state.route.params.id = '2'
  await nextTick()
  await flushPromises()
  upload.resolve({ avatar: 'new-avatar', message: '成功' })
  await first
  expect(setupState().targetUser.avatar).toBe('avatar-2')
  expect(state.user.user.avatar).toBe('new-avatar')
  expect(JSON.parse(localStorage.getItem('user') || '{}').avatar).toBe('new-avatar')
  expect(ElMessage.success).not.toHaveBeenCalled()
  expect(setupState().uploadingAvatar).toBe(false)
})
it('头像请求返回前切换账户不能更新新账户缓存', async () => {
  delete state.route.params.id
  const upload = deferred<UploadAvatarResponse>()
  vi.mocked(uploadAvatar).mockReturnValue(upload.promise)
  mountPage()
  await flushPromises()
  const first = setupState().handleAvatarUpload({ file: new File(['avatar'], 'avatar.png') })
  state.user.user = { id: 4, username: 'new account', role: 'student', avatar: 'account-4' }
  await nextTick()
  await flushPromises()
  upload.resolve({ avatar: 'account-1', message: '成功' })
  await first
  expect(state.user.user.avatar).toBe('account-4')
  expect(setupState().targetUser.avatar).toBe('account-4')
  expect(localStorage.getItem('user')).toBeNull()
})
it('卸载后资料失败不弹出旧错误', async () => {
  const old = deferred<UserProfileResponse>()
  vi.mocked(getUserProfile).mockReturnValueOnce(old.promise)
  mountPage()
  mountedWrapper().unmount()
  wrapper = undefined
  old.reject(new Error('gone'))
  await flushPromises()
  expect(ElMessage.error).not.toHaveBeenCalled()
  expect(getUserSubmissions).not.toHaveBeenCalled()
})

it('其他用户资料页不展示或查询当前用户错题本，返回自己资料时才加载', async () => {
  mountPage()
  await flushPromises()
  expect(mountedWrapper().find('.wrongbook-card').exists()).toBe(false)
  expect(request).not.toHaveBeenCalled()
  delete state.route.params.id
  await nextTick()
  await flushPromises()
  expect(mountedWrapper().find('.wrongbook-card').exists()).toBe(true)
  expect(mocks.request.mock.calls.map(([config]) => config.url)).toEqual([
    '/wrong-book/stats',
    '/wrong-book/',
  ])
})
it('错题本分页控件能读取十条以后的记录', async () => {
  delete state.route.params.id
  mocks.request.mockImplementation((config) =>
    Promise.resolve(
      config.url?.endsWith('/stats')
        ? { total: 11, unresolved: 11, reviewed: 0, accepted: 0 }
        : { total: 11, items: [{ id: config.params.page }] },
    ),
  )
  mountPage(true)
  await flushPromises()
  mountedWrapper()
    .findComponent<ComponentPublicInstance>('el-pagination-stub')
    .vm.$emit('current-change', 2)
  await flushPromises()
  expect(setupState().wbPage).toBe(2)
  expect(setupState().wbItems).toEqual([{ id: 2 }])
  expect(mocks.request.mock.calls).toContainEqual([
    { url: '/wrong-book/', method: 'get', params: { page: 2, page_size: 10 } },
  ])
})
it('离开自己资料页后旧错题本响应不能重新填入数据', async () => {
  delete state.route.params.id
  const old = deferred<unknown>()
  mocks.request.mockReturnValue(old.promise)
  mountPage()
  state.route.params.id = '2'
  await nextTick()
  await flushPromises()
  old.resolve({ total: 1, reviewed: 1, items: [{ id: 1 }] })
  await flushPromises()
  expect(setupState().wbItems).toEqual([])
  expect(setupState().wbStats.total).toBe(0)
  expect(setupState().wbLoading).toBe(false)
})
it('当前错题本加载失败会显示错误且允许重试', async () => {
  delete state.route.params.id
  mocks.request.mockRejectedValueOnce(new Error('wrong book failed'))
  mountPage()
  await flushPromises()
  expect(ElMessage.error).toHaveBeenCalledWith('wrong book failed')
  expect(setupState().wbLoading).toBe(false)
  await setupState().fetchWrongBook()
  expect(mocks.request.mock.calls.filter(([config]) => config.url === '/wrong-book/')).toHaveLength(
    2,
  )
})
it('重复复习点击只发送一次，统计取自服务端', async () => {
  delete state.route.params.id
  mountPage()
  await flushPromises()
  const post = deferred<unknown>()
  mocks.request.mockImplementation((config) =>
    config.method === 'post' ? post.promise : Promise.resolve({ items: [], total: 0, reviewed: 0 }),
  )
  const item = { id: 1, reviewed: false, accepted: false }
  const first = setupState().toggleReview(item)
  await setupState().toggleReview({ ...item })
  expect(mocks.request.mock.calls.filter(([config]) => config.method === 'post')).toHaveLength(1)
  post.resolve({ reviewed: false })
  await first
  expect(setupState().wbStats.reviewed).toBe(0)
  expect(setupState().pendingReviews.has(1)).toBe(false)
  mocks.request.mockImplementation((config) =>
    Promise.resolve(
      config.method === 'post' ? { reviewed: true } : { items: [], total: 1, reviewed: 1 },
    ),
  )
  await setupState().toggleReview(item)
  expect(setupState().wbStats.reviewed).toBe(1)
})
it('切换账户后旧复习请求不修改新账户统计或解除其等待状态', async () => {
  delete state.route.params.id
  mountPage()
  await flushPromises()
  const old = deferred<unknown>(),
    current = deferred<unknown>()
  mocks.request.mockImplementation((config) =>
    config.method === 'post' ? old.promise : Promise.resolve({ items: [], total: 0, reviewed: 0 }),
  )
  const first = setupState().toggleReview({ id: 1, reviewed: false })
  state.user.user = { id: 3, username: 'new', role: 'student' }
  await nextTick()
  await flushPromises()
  mocks.request.mockImplementation((config) =>
    config.method === 'post'
      ? current.promise
      : Promise.resolve({ items: [], total: 0, reviewed: 0 }),
  )
  const second = setupState().toggleReview({ id: 1, reviewed: false })
  old.resolve({ reviewed: true })
  await first
  expect(setupState().wbStats.reviewed).toBe(0)
  expect(setupState().pendingReviews.has(1)).toBe(true)
  mocks.request.mockImplementation((config) =>
    config.method === 'post'
      ? current.promise
      : Promise.resolve({ items: [], total: 1, reviewed: 1 }),
  )
  current.resolve({ reviewed: true })
  await second
  expect(setupState().wbStats.reviewed).toBe(1)
})

it.each([true, false])(
  '复习请求和列表刷新交错时重新读取正确状态（刷新先完成：%s）',
  async (refreshFirst) => {
    delete state.route.params.id
    mocks.request.mockImplementation((config) =>
      Promise.resolve(
        config.url?.endsWith('/stats')
          ? { total: 1, reviewed: 0 }
          : { total: 1, items: [{ id: 1, reviewed: false }] },
      ),
    )
    mountPage()
    await flushPromises()
    const item = setupState().wbItems[0]
    const post = deferred<unknown>(),
      oldListing = deferred<unknown>(),
      oldStats = deferred<unknown>()
    mocks.request.mockImplementation((config) =>
      config.method === 'post'
        ? post.promise
        : config.url?.endsWith('/stats')
          ? oldStats.promise
          : oldListing.promise,
    )
    const mutation = setupState().toggleReview(item)
    const refresh = setupState().fetchWrongBook()
    const resolveOld = async () => {
      oldStats.resolve({ total: 1, reviewed: 0 })
      oldListing.resolve({ total: 1, items: [{ id: 1, reviewed: false }] })
      await refresh
    }
    if (refreshFirst) await resolveOld()
    mocks.request.mockImplementation((config) =>
      Promise.resolve(
        config.url?.endsWith('/stats')
          ? { total: 1, reviewed: 1 }
          : { total: 1, items: [{ id: 1, reviewed: true }] },
      ),
    )
    post.resolve({ reviewed: true })
    await mutation
    if (!refreshFirst) await resolveOld()
    expect(setupState().wbItems[0].reviewed).toBe(true)
    expect(setupState().wbStats.reviewed).toBe(1)
  },
)
it('复习完成后刷新用户正在请求的页，不强制返回此前页面', async () => {
  delete state.route.params.id
  mocks.request.mockImplementation((config) =>
    Promise.resolve(
      config.url?.endsWith('/stats')
        ? { total: 11, reviewed: 0 }
        : { total: 11, items: [{ id: 1, reviewed: false }] },
    ),
  )
  mountPage()
  await flushPromises()
  const post = deferred<unknown>(),
    old = deferred<unknown>()
  mocks.request.mockImplementation((config) =>
    config.method === 'post' ? post.promise : old.promise,
  )
  const mutation = setupState().toggleReview(setupState().wbItems[0])
  const navigation = setupState().fetchWrongBook(2)
  mocks.request.mockImplementation((config) =>
    Promise.resolve(
      config.url?.endsWith('/stats')
        ? { total: 11, reviewed: 1 }
        : { total: 11, items: [{ id: 11, reviewed: false }] },
    ),
  )
  post.resolve({ reviewed: true })
  await mutation
  old.resolve({ total: 11, reviewed: 0, items: [{ id: 2 }] })
  await navigation
  expect(setupState().wbPage).toBe(2)
  expect(setupState().wbItems[0].id).toBe(11)
  expect(setupState().wbStats.reviewed).toBe(1)
})

it.each(['invalid', '0', '-1', '1e3', ['2']])(
  '非法资料路由 ID %s 不请求其他用户或当前用户历史',
  async (id) => {
    state.route.params.id = id
    mountPage()
    await flushPromises()
    expect(getUserProfile).not.toHaveBeenCalled()
    expect(getUserSubmissions).not.toHaveBeenCalled()
    expect(request).not.toHaveBeenCalled()
    expect(ElMessage.error).toHaveBeenCalledWith('用户 ID 无效')
  },
)
