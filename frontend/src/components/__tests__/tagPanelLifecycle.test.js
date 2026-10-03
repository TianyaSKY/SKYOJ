import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
vi.mock('@/utils/request', () => ({ default: vi.fn() }))
vi.mock('@/stores/user', () => ({ useUserStore: () => ({ user: { role: 'teacher' } }) }))
vi.mock('element-plus', () => ({
  ElMessage: { error: vi.fn(), success: vi.fn(), warning: vi.fn() },
  ElMessageBox: { confirm: vi.fn() },
}))
import TagPanel from '../TagPanel.vue'
import request from '@/utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
let wrapper
function deferred() {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
function mountPage() {
  wrapper = shallowMount(TagPanel, { props: { problemId: 1 }, global: {
    stubs: Object.fromEntries(['el-tag','el-icon','el-button','el-dialog','el-form','el-form-item','el-select','el-option'].map(name => [name,true])),
  } })
}
beforeEach(() => { vi.resetAllMocks(); request.mockResolvedValue([]) })
afterEach(() => { wrapper?.unmount(); wrapper = undefined })
it('旧题目标签响应不能覆盖新题目的标签', async () => {
  const old = deferred()
  request.mockImplementation(({ url }) => url === '/tags/problems/1' ? old.promise : Promise.resolve([{ id: 2, name: 'new' }]))
  mountPage()
  await wrapper.setProps({ problemId: 2 }); await flushPromises()
  old.resolve([{ id: 1, name: 'old' }]); await flushPromises()
  expect(wrapper.vm.attached).toEqual([{ id: 2, name: 'new' }])
})
it('旧请求失败不能结束新请求的加载状态或显示错误', async () => {
  const old = deferred(), current = deferred()
  request.mockImplementation(({ url }) => url === '/tags' ? Promise.resolve([]) : url.endsWith('/1') ? old.promise : current.promise)
  mountPage()
  await wrapper.setProps({ problemId: 2 })
  old.reject(new Error('old')); await flushPromises()
  expect(wrapper.vm.loading).toBe(true)
  expect(ElMessage.error).not.toHaveBeenCalled()
  current.resolve([]); await flushPromises()
  expect(wrapper.vm.loading).toBe(false)
})
it('移除确认期间切换题目不能向新题目发送删除请求', async () => {
  const confirmation = deferred()
  ElMessageBox.confirm.mockReturnValue(confirmation.promise)
  mountPage(); await flushPromises()
  const removal = wrapper.vm.detach({ id: 3, name: 'old tag' })
  await wrapper.setProps({ problemId: 2 }); await flushPromises()
  confirmation.resolve('confirm'); await removal
  expect(request.mock.calls.some(([config]) => config.method === 'delete')).toBe(false)
  expect(ElMessage.success).not.toHaveBeenCalled()
})
it('旧挂标签请求完成不能关闭新题目的添加窗口', async () => {
  const attach = deferred()
  request.mockImplementation(config => config.method === 'post' ? attach.promise : Promise.resolve([]))
  mountPage(); await flushPromises()
  wrapper.vm.selectedTagId = 3
  const mutation = wrapper.vm.confirmAttach()
  await wrapper.setProps({ problemId: 2 }); await flushPromises()
  wrapper.vm.openAttach()
  wrapper.vm.selectedTagId = 4
  attach.resolve({}); await mutation
  expect(wrapper.vm.attachDialogVisible).toBe(true)
  expect(wrapper.vm.selectedTagId).toBe(4)
  expect(ElMessage.success).not.toHaveBeenCalled()
  expect(request.mock.calls.filter(([config]) => config.url === '/tags/problems/2')).toHaveLength(1)
})
it('卸载后标签请求失败不弹出错误', async () => {
  const response = deferred()
  request.mockReturnValue(response.promise)
  mountPage()
  wrapper.unmount(); wrapper = undefined
  response.reject(new Error('gone')); await flushPromises()
  expect(ElMessage.error).not.toHaveBeenCalled()
})
