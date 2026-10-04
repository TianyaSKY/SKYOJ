import type { AxiosRequestConfig } from 'axios'
import type { ComponentPublicInstance } from 'vue'
import type { TagResponse, SolutionListItemResponse, CommentResponse } from '@/types/community'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
const mocks = vi.hoisted(() => ({ request: vi.fn<(config: AxiosRequestConfig<Record<string, unknown>>) => Promise<unknown>>() }))
vi.mock('@/utils/request', () => ({ default: mocks.request }))
vi.mock('@/stores/user', () => ({ useUserStore: () => ({ user: { role: 'teacher' } }) }))
vi.mock('element-plus', () => ({
  ElMessage: { error: vi.fn(), success: vi.fn(), warning: vi.fn() },
  ElMessageBox: { confirm: vi.fn() },
}))
import TagPanel from '../TagPanel.vue'
import request from '@/utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
let wrapper: ReturnType<typeof mountPage> | undefined
function mountedWrapper() {
  if (!wrapper) throw new Error('面板未挂载')
  return wrapper
}
// Vue 公共组件类型不公开 setup 状态，声明测试所需字段。
function setupState() {
  return mountedWrapper().vm as unknown as { attached: TagResponse[]; loading: boolean; selectedTagId: number | null;
    attachDialogVisible: boolean; submittingAttach: boolean;
    detach(tag: Pick<TagResponse, 'id' | 'name'>): Promise<void>; openAttach(): void; confirmAttach(): Promise<void>; }
}
function deferred<T = unknown>() {
  let resolve!: (value: T) => void, reject!: (reason: unknown) => void
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
function mountPage() {
  const mounted = shallowMount(TagPanel, { props: { problemId: 1 }, global: {
    stubs: Object.fromEntries(['el-tag','el-icon','el-button','el-dialog','el-form','el-form-item','el-select','el-option'].map(name => [name,true])),
  } })
  wrapper = mounted
  return mounted
}
beforeEach(() => { vi.resetAllMocks(); mocks.request.mockResolvedValue([]) })
afterEach(() => { wrapper?.unmount(); wrapper = undefined })
it('旧题目标签响应不能覆盖新题目的标签', async () => {
  const old = deferred()
  mocks.request.mockImplementation(({ url }) => url === '/tags/problems/1' ? old.promise : Promise.resolve([{ id: 2, name: 'new' }]))
  mountPage()
  await mountedWrapper().setProps({ problemId: 2 }); await flushPromises()
  old.resolve([{ id: 1, name: 'old' }]); await flushPromises()
  expect(setupState().attached).toEqual([{ id: 2, name: 'new' }])
})
it('旧请求失败不能结束新请求的加载状态或显示错误', async () => {
  const old = deferred(), current = deferred()
  mocks.request.mockImplementation(({ url }) => url === '/tags' ? Promise.resolve([]) : url?.endsWith('/1') ? old.promise : current.promise)
  mountPage()
  await mountedWrapper().setProps({ problemId: 2 })
  old.reject(new Error('old')); await flushPromises()
  expect(setupState().loading).toBe(true)
  expect(ElMessage.error).not.toHaveBeenCalled()
  current.resolve([]); await flushPromises()
  expect(setupState().loading).toBe(false)
})
it('移除确认期间切换题目不能向新题目发送删除请求', async () => {
  const confirmation = deferred<Awaited<ReturnType<typeof ElMessageBox.confirm>>>()
  vi.mocked(ElMessageBox.confirm).mockReturnValue(confirmation.promise)
  mountPage(); await flushPromises()
  const removal = setupState().detach({ id: 3, name: 'old tag' })
  await mountedWrapper().setProps({ problemId: 2 }); await flushPromises()
  confirmation.resolve('confirm' as Awaited<ReturnType<typeof ElMessageBox.confirm>>); await removal
  expect(mocks.request.mock.calls.some(([config]) => config.method === 'delete')).toBe(false)
  expect(ElMessage.success).not.toHaveBeenCalled()
})
it('旧挂标签请求完成不能关闭新题目的添加窗口', async () => {
  const attach = deferred()
  mocks.request.mockImplementation(config => config.method === 'post' ? attach.promise : Promise.resolve([]))
  mountPage(); await flushPromises()
  setupState().openAttach()
  setupState().selectedTagId = 3
  const mutation = setupState().confirmAttach()
  await mountedWrapper().setProps({ problemId: 2 }); await flushPromises()
  setupState().openAttach()
  setupState().selectedTagId = 4
  attach.resolve({}); await mutation
  expect(setupState().attachDialogVisible).toBe(true)
  expect(setupState().selectedTagId).toBe(4)
  expect(ElMessage.success).not.toHaveBeenCalled()
  expect(mocks.request.mock.calls.filter(([config]) => config.url === '/tags/problems/2')).toHaveLength(1)
})
it('卸载后标签请求失败不弹出错误', async () => {
  const response = deferred()
  mocks.request.mockReturnValue(response.promise)
  mountPage()
  mountedWrapper().unmount(); wrapper = undefined
  response.reject(new Error('gone')); await flushPromises()
  expect(ElMessage.error).not.toHaveBeenCalled()
})

it('标签提交期间重复点击只发送一次请求', async () => {
  const attach = deferred()
  mocks.request.mockImplementation(config => config.method === 'post' ? attach.promise : Promise.resolve([]))
  mountPage(); await flushPromises()
  setupState().openAttach(); setupState().selectedTagId = 3
  const first = setupState().confirmAttach(), second = setupState().confirmAttach()
  expect(setupState().submittingAttach).toBe(true)
  expect(mocks.request.mock.calls.filter(([config]) => config.method === 'post')).toHaveLength(1)
  attach.resolve({}); await Promise.all([first, second])
  expect(setupState().submittingAttach).toBe(false)
  expect(setupState().attachDialogVisible).toBe(false)
})
it('同一题目的旧提交成功不能关闭新添加窗口', async () => {
  const attach = deferred()
  mocks.request.mockImplementation(config => config.method === 'post' ? attach.promise : Promise.resolve([]))
  mountPage(); await flushPromises()
  setupState().openAttach(); setupState().selectedTagId = 3
  const first = setupState().confirmAttach()
  setupState().attachDialogVisible = false
  setupState().openAttach(); setupState().selectedTagId = 4
  attach.resolve({}); await first
  expect(setupState().attachDialogVisible).toBe(true)
  expect(setupState().selectedTagId).toBe(4)
  expect(ElMessage.success).not.toHaveBeenCalled()
  expect(mocks.request.mock.calls.filter(([config]) => config.url === '/tags/problems/1')).toHaveLength(2)
})
it('旧提交失败不能解除新窗口提交状态或显示错误', async () => {
  const old = deferred(), current = deferred()
  mocks.request.mockImplementation(config => config.method === 'post' ? (config.data?.tag_id === 3 ? old.promise : current.promise) : Promise.resolve([]))
  mountPage(); await flushPromises()
  setupState().openAttach(); setupState().selectedTagId = 3
  const first = setupState().confirmAttach()
  setupState().attachDialogVisible = false
  setupState().openAttach(); setupState().selectedTagId = 4
  const second = setupState().confirmAttach()
  old.reject(new Error('old failed')); await first
  expect(setupState().submittingAttach).toBe(true)
  expect(ElMessage.error).not.toHaveBeenCalled()
  current.resolve({}); await second
  expect(setupState().submittingAttach).toBe(false)
  expect(setupState().attachDialogVisible).toBe(false)
})
it('当前提交失败保留选择并允许重试，关闭窗口后不发送请求', async () => {
  mountPage(); await flushPromises()
  mocks.request.mockRejectedValueOnce(new Error('failed')).mockResolvedValue([])
  setupState().openAttach(); setupState().selectedTagId = 3
  await setupState().confirmAttach()
  expect(setupState().selectedTagId).toBe(3)
  expect(setupState().submittingAttach).toBe(false)
  expect(setupState().attachDialogVisible).toBe(true)
  await setupState().confirmAttach()
  await setupState().confirmAttach()
  expect(mocks.request.mock.calls.filter(([config]) => config.method === 'post')).toHaveLength(2)
})
