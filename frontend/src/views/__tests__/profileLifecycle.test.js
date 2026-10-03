import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { nextTick, reactive } from 'vue'
const state = vi.hoisted(() => ({ route: null, user: null, sys: null }))
vi.mock('vue-router', () => ({ useRoute: () => state.route }))
vi.mock('@/stores/user', () => ({ useUserStore: () => state.user }))
vi.mock('@/stores/sys', () => ({ useSysStore: () => state.sys }))
vi.mock('@/api/user', () => ({ getUserProfile: vi.fn(), getUserSubmissions: vi.fn(), uploadAvatar: vi.fn() }))
vi.mock('@/utils/request', () => ({ default: vi.fn() }))
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn(), success: vi.fn() } }))
import ProfileView from '../ProfileView.vue'
import { getUserProfile, getUserSubmissions, uploadAvatar } from '@/api/user'
import request from '@/utils/request'
import { ElMessage } from 'element-plus'
let wrapper
function deferred() {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
function mountPage(renderCards = false) {
  wrapper = shallowMount(ProfileView, { global: {
    directives: { loading: () => {} },
    stubs: Object.fromEntries(['el-pagination','el-card','el-avatar','el-upload','el-icon','el-tag','el-table','el-table-column','el-button','el-link','el-empty'].map(name => [name, name === 'el-card' && renderCards ? { template: '<div><slot /></div>' } : true])),
  } })
}
beforeEach(() => {
  vi.resetAllMocks()
  localStorage.clear()
  state.route = reactive({ params: { id: '2' } })
  state.user = reactive({ user: { id: 1, username: 'self', role: 'student', avatar: 'self-avatar' } })
  state.sys = reactive({ practice: true })
  getUserProfile.mockImplementation(id => Promise.resolve({ id: Number(id), username: String(id), avatar: `avatar-${id}` }))
  getUserSubmissions.mockResolvedValue([])
  request.mockResolvedValue({ items: [], total: 0, accepted: 0, unresolved: 0, reviewed: 0 })
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined })
it('旧用户资料不能覆盖新用户资料或继续读取旧用户提交', async () => {
  const old = deferred()
  getUserProfile.mockReturnValueOnce(old.promise)
  mountPage()
  state.route.params.id = '3'; await nextTick(); await flushPromises()
  old.resolve({ id: 2, username: 'old' }); await flushPromises()
  expect(wrapper.vm.targetUser.id).toBe(3)
  expect(getUserSubmissions).toHaveBeenCalledExactlyOnceWith('3')
})
it('旧用户提交失败不能显示错误或结束新请求的等待状态', async () => {
  const old = deferred(), current = deferred()
  getUserSubmissions.mockReturnValueOnce(old.promise).mockReturnValueOnce(current.promise)
  mountPage(); await flushPromises()
  state.route.params.id = '3'; await nextTick(); await flushPromises()
  expect(wrapper.vm.submissions).toEqual([])
  old.reject(new Error('old failed')); await flushPromises()
  expect(wrapper.vm.loading).toBe(true)
  expect(ElMessage.error).not.toHaveBeenCalled()
  current.resolve([{ id: 3 }]); await flushPromises()
  expect(wrapper.vm.submissions).toEqual([{ id: 3 }])
  expect(wrapper.vm.loading).toBe(false)
})
it('考试模式仍加载资料，模式变化后重新按权限加载提交历史', async () => {
  state.sys.practice = false
  mountPage(); await flushPromises()
  expect(wrapper.vm.targetUser.id).toBe(2)
  expect(getUserSubmissions).not.toHaveBeenCalled()
  state.sys.practice = true; await nextTick(); await flushPromises()
  expect(getUserSubmissions).toHaveBeenCalledExactlyOnceWith('2')
})
it('切换为考试模式后旧历史响应不能恢复已隐藏的提交记录', async () => {
  const old = deferred()
  getUserSubmissions.mockReturnValueOnce(old.promise)
  mountPage(); await flushPromises()
  state.sys.practice = false; await nextTick(); await flushPromises()
  old.resolve([{ id: 1 }]); await flushPromises()
  expect(wrapper.vm.submissions).toEqual([])
  expect(wrapper.vm.targetUser.id).toBe(2)
})
it('头像上传后切换用户不改写新用户头像，但更新上传账户缓存', async () => {
  delete state.route.params.id
  const upload = deferred()
  uploadAvatar.mockReturnValue(upload.promise)
  mountPage(); await flushPromises()
  const options = { file: new File(['avatar'], 'avatar.png', { type: 'image/png' }) }
  const first = wrapper.vm.handleAvatarUpload(options)
  await wrapper.vm.handleAvatarUpload(options)
  expect(uploadAvatar).toHaveBeenCalledOnce()
  state.route.params.id = '2'; await nextTick(); await flushPromises()
  upload.resolve({ avatar: 'new-avatar' }); await first
  expect(wrapper.vm.targetUser.avatar).toBe('avatar-2')
  expect(state.user.user.avatar).toBe('new-avatar')
  expect(JSON.parse(localStorage.getItem('user')).avatar).toBe('new-avatar')
  expect(ElMessage.success).not.toHaveBeenCalled()
  expect(wrapper.vm.uploadingAvatar).toBe(false)
})
it('头像请求返回前切换账户不能更新新账户缓存', async () => {
  delete state.route.params.id
  const upload = deferred()
  uploadAvatar.mockReturnValue(upload.promise)
  mountPage(); await flushPromises()
  const first = wrapper.vm.handleAvatarUpload({ file: new File(['avatar'], 'avatar.png') })
  state.user.user = { id: 4, username: 'new account', role: 'student', avatar: 'account-4' }
  await nextTick(); await flushPromises()
  upload.resolve({ avatar: 'account-1' }); await first
  expect(state.user.user.avatar).toBe('account-4')
  expect(wrapper.vm.targetUser.avatar).toBe('account-4')
  expect(localStorage.getItem('user')).toBeNull()
})
it('卸载后资料失败不弹出旧错误', async () => {
  const old = deferred()
  getUserProfile.mockReturnValueOnce(old.promise)
  mountPage(); wrapper.unmount(); wrapper = undefined
  old.reject(new Error('gone')); await flushPromises()
  expect(ElMessage.error).not.toHaveBeenCalled()
  expect(getUserSubmissions).not.toHaveBeenCalled()
})

it('其他用户资料页不展示或查询当前用户错题本，返回自己资料时才加载', async () => {
  mountPage(); await flushPromises()
  expect(wrapper.find('.wrongbook-card').exists()).toBe(false)
  expect(request).not.toHaveBeenCalled()
  delete state.route.params.id; await nextTick(); await flushPromises()
  expect(wrapper.find('.wrongbook-card').exists()).toBe(true)
  expect(request.mock.calls.map(([config]) => config.url)).toEqual(['/wrong-book/stats', '/wrong-book/'])
})
it('错题本分页控件能读取十条以后的记录', async () => {
  delete state.route.params.id
  request.mockImplementation(config => Promise.resolve(config.url.endsWith('/stats')
    ? { total: 11, unresolved: 11, reviewed: 0, accepted: 0 }
    : { total: 11, items: [{ id: config.params.page }] }))
  mountPage(true); await flushPromises()
  wrapper.findComponent('el-pagination-stub').vm.$emit('current-change', 2)
  await flushPromises()
  expect(wrapper.vm.wbPage).toBe(2)
  expect(wrapper.vm.wbItems).toEqual([{ id: 2 }])
  expect(request.mock.calls).toContainEqual([{ url: '/wrong-book/', method: 'get', params: { page: 2, page_size: 10 } }])
})
it('离开自己资料页后旧错题本响应不能重新填入数据', async () => {
  delete state.route.params.id
  const old = deferred()
  request.mockReturnValue(old.promise)
  mountPage()
  state.route.params.id = '2'; await nextTick(); await flushPromises()
  old.resolve({ total: 1, reviewed: 1, items: [{ id: 1 }] }); await flushPromises()
  expect(wrapper.vm.wbItems).toEqual([])
  expect(wrapper.vm.wbStats.total).toBe(0)
  expect(wrapper.vm.wbLoading).toBe(false)
})
it('当前错题本加载失败会显示错误且允许重试', async () => {
  delete state.route.params.id
  request.mockRejectedValueOnce(new Error('wrong book failed'))
  mountPage(); await flushPromises()
  expect(ElMessage.error).toHaveBeenCalledWith('wrong book failed')
  expect(wrapper.vm.wbLoading).toBe(false)
  await wrapper.vm.fetchWrongBook()
  expect(request.mock.calls.filter(([config]) => config.url === '/wrong-book/')).toHaveLength(2)
})
it('重复复习点击只发送一次，统计按实际状态变化更新', async () => {
  delete state.route.params.id
  mountPage(); await flushPromises()
  const post = deferred()
  request.mockReturnValue(post.promise)
  const item = { id: 1, reviewed: false, accepted: false }
  const first = wrapper.vm.toggleReview(item)
  await wrapper.vm.toggleReview({ ...item })
  expect(request.mock.calls.filter(([config]) => config.method === 'post')).toHaveLength(1)
  post.resolve({ reviewed: false }); await first
  expect(wrapper.vm.wbStats.reviewed).toBe(0)
  expect(wrapper.vm.pendingReviews.has(1)).toBe(false)
  request.mockResolvedValue({ reviewed: true })
  await wrapper.vm.toggleReview(item)
  expect(wrapper.vm.wbStats.reviewed).toBe(1)
})
it('切换账户后旧复习请求不修改新账户统计或解除其等待状态', async () => {
  delete state.route.params.id
  mountPage(); await flushPromises()
  const old = deferred(), current = deferred()
  request.mockImplementation(config => config.method === 'post' ? old.promise : Promise.resolve({ items: [], total: 0, reviewed: 0 }))
  const first = wrapper.vm.toggleReview({ id: 1, reviewed: false })
  state.user.user = { id: 3, username: 'new', role: 'student' }
  await nextTick(); await flushPromises()
  request.mockImplementation(config => config.method === 'post' ? current.promise : Promise.resolve({ items: [], total: 0, reviewed: 0 }))
  const second = wrapper.vm.toggleReview({ id: 1, reviewed: false })
  old.resolve({ reviewed: true }); await first
  expect(wrapper.vm.wbStats.reviewed).toBe(0)
  expect(wrapper.vm.pendingReviews.has(1)).toBe(true)
  current.resolve({ reviewed: true }); await second
  expect(wrapper.vm.wbStats.reviewed).toBe(1)
})
