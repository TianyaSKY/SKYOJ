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
function mountPage() {
  wrapper = shallowMount(ProfileView, { global: {
    directives: { loading: () => {} },
    stubs: Object.fromEntries(['el-card','el-avatar','el-upload','el-icon','el-tag','el-table','el-table-column','el-button','el-link','el-empty'].map(name => [name,true])),
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
