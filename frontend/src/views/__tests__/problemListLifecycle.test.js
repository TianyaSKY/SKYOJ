import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { nextTick } from 'vue'
vi.mock('@/api/problem', () => ({ getProblemList: vi.fn(), searchProblems: vi.fn() }))
vi.mock('@/utils/request', () => ({ default: vi.fn() }))
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn() } }))
import ProblemListView from '../ProblemListView.vue'
import { getProblemList, searchProblems } from '@/api/problem'
import request from '@/utils/request'
import { ElMessage } from 'element-plus'
let wrapper
function deferred() {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
function mountPage() {
  wrapper = shallowMount(ProblemListView, { global: {
    directives: { loading: () => {} },
    stubs: Object.fromEntries(['el-card','el-input','el-select','el-option','el-table','el-table-column','el-link','el-tag','el-icon','el-button','el-pagination'].map(name => [name,true])),
  } })
}
beforeEach(() => {
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
  vi.resetAllMocks()
  getProblemList.mockResolvedValue({ problems: [{ id: 1 }], total: 1 })
  searchProblems.mockResolvedValue([])
  request.mockResolvedValue([])
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined; vi.clearAllTimers(); vi.useRealTimers() })
async function search(query) {
  wrapper.vm.searchQuery = query
  await nextTick()
  await vi.advanceTimersByTimeAsync(500)
}
it('修改关键词立即清除旧结果，旧搜索响应不能覆盖新搜索', async () => {
  const old = deferred(), current = deferred()
  searchProblems.mockReturnValueOnce(old.promise).mockReturnValueOnce(current.promise)
  mountPage(); await flushPromises()
  await search('old')
  wrapper.vm.searchResults = [{ id: 9 }]
  wrapper.vm.searchQuery = 'new'; await nextTick()
  expect(wrapper.vm.filteredProblems).toEqual([])
  old.resolve([{ id: 2 }]); await flushPromises()
  expect(wrapper.vm.total).toBe(0)
  expect(wrapper.vm.loading).toBe(true)
  await vi.advanceTimersByTimeAsync(500)
  current.resolve([{ id: 3 }]); await flushPromises()
  expect(wrapper.vm.filteredProblems).toEqual([{ id: 3 }])
  expect(wrapper.vm.total).toBe(1)
})
it('初始列表迟到不能覆盖搜索的总数或结束搜索等待状态', async () => {
  const list = deferred(), result = deferred()
  getProblemList.mockReturnValueOnce(list.promise)
  searchProblems.mockReturnValueOnce(result.promise)
  mountPage(); await search('query')
  list.resolve({ problems: [{ id: 1 }], total: 99 }); await flushPromises()
  expect(wrapper.vm.total).toBe(0)
  expect(wrapper.vm.loading).toBe(true)
  result.resolve([{ id: 2 }]); await flushPromises()
  expect(wrapper.vm.total).toBe(1)
})
it('清空关键词后等待列表完成，旧搜索失败不弹出错误', async () => {
  const old = deferred(), list = deferred()
  searchProblems.mockReturnValueOnce(old.promise)
  mountPage(); await flushPromises(); await search('old')
  getProblemList.mockReturnValueOnce(list.promise)
  wrapper.vm.searchQuery = ''; await nextTick()
  old.reject(new Error('old failed')); await flushPromises()
  expect(wrapper.vm.loading).toBe(true)
  expect(ElMessage.error).not.toHaveBeenCalled()
  list.resolve({ problems: [{ id: 4 }], total: 4 }); await flushPromises()
  expect(wrapper.vm.loading).toBe(false)
  expect(wrapper.vm.filteredProblems).toEqual([{ id: 4 }])
})
it('快速修改关键词只发起最后一个延迟搜索，卸载后取消尚未触发的搜索', async () => {
  mountPage(); await flushPromises()
  wrapper.vm.searchQuery = 'first'; await nextTick()
  wrapper.vm.searchQuery = 'second'; await nextTick()
  await vi.advanceTimersByTimeAsync(500)
  expect(searchProblems).toHaveBeenCalledExactlyOnceWith({ query: 'second', top_k: 50 })
  wrapper.vm.searchQuery = 'third'; await nextTick()
  wrapper.unmount(); wrapper = undefined
  await vi.advanceTimersByTimeAsync(1000)
  expect(searchProblems).toHaveBeenCalledOnce()
})
it('旧标签列表请求不能覆盖新筛选结果', async () => {
  const old = deferred()
  mountPage(); await flushPromises()
  getProblemList.mockReturnValueOnce(old.promise).mockResolvedValueOnce({ problems: [{ id: 3 }], total: 3 })
  wrapper.vm.tagFilter = 1; wrapper.vm.handleTagChange()
  wrapper.vm.tagFilter = 2; wrapper.vm.handleTagChange()
  await flushPromises()
  old.resolve({ problems: [{ id: 2 }], total: 2 }); await flushPromises()
  expect(wrapper.vm.filteredProblems).toEqual([{ id: 3 }])
  expect(wrapper.vm.total).toBe(3)
})
