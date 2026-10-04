import type { ProblemListResponse, SearchProblemResponse, PaginatedProblemsResponse } from '@/types/problem'
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
let wrapper: ReturnType<typeof mountPage> | undefined
const problem = (value: Partial<ProblemListResponse>): ProblemListResponse => ({
  id: 1, title: '题目', type: 'acm', language: 'python', time_limit: 1000, memory_limit: 128,
  test_case_status: 'ready', test_case_count: 1, test_case_valid_count: 1, ...value,
})
const searchResult = (value: Partial<SearchProblemResponse>): SearchProblemResponse => ({
  id: 1, title: '题目', content: '内容', type: 'acm', language: 'python', time_limit: 1000, memory_limit: 128, ...value,
})
const page = (value: { problems: ProblemListResponse[]; total: number }): PaginatedProblemsResponse => ({ page: 1, page_size: 20, ...value })
function current() {
  if (!wrapper) throw new Error('题目列表未挂载')
  return wrapper
}
// Vue 公共组件类型不公开 setup 内部状态；这里只声明实际被测试的字段。
function setupState() {
  return current().vm as unknown as {
    searchQuery: string; searchResults: SearchProblemResponse[]; filteredProblems: (ProblemListResponse | SearchProblemResponse)[];
    problems: ProblemListResponse[]; total: number; loading: boolean; currentPage: number; pageSize: number;
    tagFilter: number | ''; typeFilter: '' | 'acm' | 'oop' | 'kaggle';
    handleTagChange(): Promise<void>; handleTypeChange(): Promise<void>;
    handleCurrentChange(page: number): Promise<void>; handleSizeChange(size: number): Promise<void>;
  }
}
function deferred<T>() {
  let resolve!: (value: T) => void, reject!: (reason: unknown) => void
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
function mountPage() {
  const mounted = shallowMount(ProblemListView, { global: {
    directives: { loading: () => {} },
    stubs: Object.fromEntries(['el-card','el-input','el-select','el-option','el-table','el-table-column','el-link','el-tag','el-icon','el-button','el-pagination'].map(name => [name,true])),
  } })
  wrapper = mounted
  return mounted
}
beforeEach(() => {
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
  vi.resetAllMocks()
  vi.mocked(getProblemList).mockResolvedValue(page({ problems: [problem({ id: 1 })], total: 1 }))
  vi.mocked(searchProblems).mockResolvedValue([])
  vi.mocked(request).mockResolvedValue([])
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined; vi.clearAllTimers(); vi.useRealTimers() })
async function search(query: string) {
  setupState().searchQuery = query
  await nextTick()
  await vi.advanceTimersByTimeAsync(500)
}
it('修改关键词立即清除旧结果，旧搜索响应不能覆盖新搜索', async () => {
  const old = deferred<SearchProblemResponse[]>(), current = deferred<SearchProblemResponse[]>()
  vi.mocked(searchProblems).mockReturnValueOnce(old.promise).mockReturnValueOnce(current.promise)
  mountPage(); await flushPromises()
  await search('old')
  setupState().searchResults = [searchResult({ id: 9 })]
  setupState().searchQuery = 'new'; await nextTick()
  expect(setupState().filteredProblems).toEqual([])
  old.resolve([searchResult({ id: 2 })]); await flushPromises()
  expect(setupState().total).toBe(0)
  expect(setupState().loading).toBe(true)
  await vi.advanceTimersByTimeAsync(500)
  current.resolve([searchResult({ id: 3 })]); await flushPromises()
  expect(setupState().filteredProblems).toEqual([searchResult({ id: 3 })])
  expect(setupState().total).toBe(1)
})
it('初始列表迟到不能覆盖搜索的总数或结束搜索等待状态', async () => {
  const list = deferred<PaginatedProblemsResponse>(), result = deferred<SearchProblemResponse[]>()
  vi.mocked(getProblemList).mockReturnValueOnce(list.promise)
  vi.mocked(searchProblems).mockReturnValueOnce(result.promise)
  mountPage(); await search('query')
  list.resolve(page({ problems: [problem({ id: 1 })], total: 99 })); await flushPromises()
  expect(setupState().total).toBe(0)
  expect(setupState().loading).toBe(true)
  result.resolve([searchResult({ id: 2 })]); await flushPromises()
  expect(setupState().total).toBe(1)
})
it('清空关键词后等待列表完成，旧搜索失败不弹出错误', async () => {
  const old = deferred<SearchProblemResponse[]>(), list = deferred<PaginatedProblemsResponse>()
  vi.mocked(searchProblems).mockReturnValueOnce(old.promise)
  mountPage(); await flushPromises(); await search('old')
  vi.mocked(getProblemList).mockReturnValueOnce(list.promise)
  setupState().searchQuery = ''; await nextTick()
  old.reject(new Error('old failed')); await flushPromises()
  expect(setupState().loading).toBe(true)
  expect(ElMessage.error).not.toHaveBeenCalled()
  list.resolve(page({ problems: [problem({ id: 4 })], total: 4 })); await flushPromises()
  expect(setupState().loading).toBe(false)
  expect(setupState().filteredProblems).toEqual([problem({ id: 4 })])
})
it('快速修改关键词只发起最后一个延迟搜索，卸载后取消尚未触发的搜索', async () => {
  mountPage(); await flushPromises()
  setupState().searchQuery = 'first'; await nextTick()
  setupState().searchQuery = 'second'; await nextTick()
  await vi.advanceTimersByTimeAsync(500)
  expect(searchProblems).toHaveBeenCalledExactlyOnceWith({ query: 'second', top_k: 50 })
  setupState().searchQuery = 'third'; await nextTick()
  current().unmount(); wrapper = undefined
  await vi.advanceTimersByTimeAsync(1000)
  expect(searchProblems).toHaveBeenCalledOnce()
})
it('旧标签列表请求不能覆盖新筛选结果', async () => {
  const old = deferred<PaginatedProblemsResponse>()
  mountPage(); await flushPromises()
  vi.mocked(getProblemList).mockReturnValueOnce(old.promise).mockResolvedValueOnce(page({ problems: [problem({ id: 3 })], total: 3 }))
  setupState().tagFilter = 1; setupState().handleTagChange()
  setupState().tagFilter = 2; setupState().handleTagChange()
  await flushPromises()
  old.resolve(page({ problems: [problem({ id: 2 })], total: 2 })); await flushPromises()
  expect(setupState().filteredProblems).toEqual([problem({ id: 3 })])
  expect(setupState().total).toBe(3)
})
it('关键词搜索携带当前类型和知识点，筛选变化后重新搜索', async () => {
  mountPage(); await flushPromises()
  setupState().tagFilter = 7
  setupState().typeFilter = 'oop'
  await search('query')
  expect(searchProblems).toHaveBeenLastCalledWith({ query: 'query', top_k: 50, tag_id: 7, problem_type: 'oop' })
  setupState().tagFilter = 8
  await setupState().handleTagChange()
  expect(searchProblems).toHaveBeenLastCalledWith({ query: 'query', top_k: 50, tag_id: 8, problem_type: 'oop' })
  setupState().typeFilter = 'acm'
  await setupState().handleTypeChange()
  expect(searchProblems).toHaveBeenLastCalledWith({ query: 'query', top_k: 50, tag_id: 8, problem_type: 'acm' })
  setupState().tagFilter = ''; setupState().typeFilter = ''
  await setupState().handleTagChange()
  expect(searchProblems).toHaveBeenLastCalledWith({ query: 'query', top_k: 50 })
  expect(getProblemList).toHaveBeenCalledOnce()
})
it('旧筛选搜索响应不能覆盖新筛选结果', async () => {
  const old = deferred<SearchProblemResponse[]>()
  mountPage(); await flushPromises()
  vi.mocked(searchProblems).mockReturnValueOnce(old.promise).mockResolvedValueOnce([searchResult({ id: 3, type: 'oop' })])
  await search('query')
  setupState().typeFilter = 'oop'; await setupState().handleTypeChange()
  old.resolve([searchResult({ id: 2, type: 'acm' })]); await flushPromises()
  expect(setupState().searchResults).toEqual([searchResult({ id: 3, type: 'oop' })])
  expect(setupState().total).toBe(1)
})

it('列表类型筛选从第一页重新请求，翻页和知识点变化保留类型条件', async () => {
  mountPage(); await flushPromises()
  setupState().currentPage = 3
  setupState().typeFilter = 'oop'
  vi.mocked(getProblemList).mockResolvedValue(page({ problems: [problem({ id: 8, type: 'oop' })], total: 21 }))
  await setupState().handleTypeChange()
  expect(getProblemList).toHaveBeenLastCalledWith({ page: 1, page_size: 20, problem_type: 'oop' })
  expect(setupState().total).toBe(21)
  setupState().handleCurrentChange(2); await flushPromises()
  expect(getProblemList).toHaveBeenLastCalledWith({ page: 2, page_size: 20, problem_type: 'oop' })
  setupState().tagFilter = 7; await setupState().handleTagChange()
  expect(getProblemList).toHaveBeenLastCalledWith({ page: 1, page_size: 20, tag_id: 7, problem_type: 'oop' })
  setupState().typeFilter = ''; await setupState().handleTypeChange()
  expect(getProblemList).toHaveBeenLastCalledWith({ page: 1, page_size: 20, tag_id: 7 })
})
it('翻页和每页数量变更失败后保留已加载页面的分页参数', async () => {
  const diagnostic = vi.spyOn(console, 'error').mockImplementation(() => {})
  vi.mocked(getProblemList).mockResolvedValueOnce(page({ problems: [problem({ id: 1 })], total: 21 }))
  mountPage(); await flushPromises()
  vi.mocked(getProblemList).mockRejectedValueOnce(new Error('page failed'))
  await setupState().handleCurrentChange(2)
  expect(setupState().currentPage).toBe(1)
  expect(setupState().problems).toEqual([problem({ id: 1 })])
  vi.mocked(getProblemList).mockRejectedValueOnce(new Error('size failed'))
  await setupState().handleSizeChange(50)
  expect(setupState().pageSize).toBe(20)
  expect(setupState().currentPage).toBe(1)
  expect(setupState().loading).toBe(false)
  diagnostic.mockRestore()
})
it('末页记录被移除时重新读取有效页', async () => {
  vi.mocked(getProblemList).mockResolvedValueOnce(page({ problems: [problem({ id: 1 })], total: 21 }))
  mountPage(); await flushPromises()
  vi.mocked(getProblemList).mockResolvedValueOnce(page({ problems: [], total: 20 })).mockResolvedValueOnce(page({ problems: [problem({ id: 2 })], total: 20 }))
  await setupState().handleCurrentChange(2)
  expect(setupState().currentPage).toBe(1)
  expect(setupState().problems).toEqual([problem({ id: 2 })])
  expect(getProblemList).toHaveBeenLastCalledWith({ page: 1, page_size: 20 })
})
it('类型筛选失败后不保留不符合新条件的旧题目', async () => {
  const diagnostic = vi.spyOn(console, 'error').mockImplementation(() => {})
  mountPage(); await flushPromises()
  setupState().typeFilter = 'oop'
  vi.mocked(getProblemList).mockRejectedValueOnce(new Error('filter failed'))
  await setupState().handleTypeChange()
  expect(setupState().filteredProblems).toEqual([])
  expect(setupState().total).toBe(0)
  diagnostic.mockRestore()
})
it('搜索筛选失败后不保留上一组条件的搜索结果', async () => {
  const diagnostic = vi.spyOn(console, 'error').mockImplementation(() => {})
  mountPage(); await flushPromises()
  vi.mocked(searchProblems).mockResolvedValueOnce([searchResult({ id: 1, type: 'acm' })])
  await search('query')
  setupState().typeFilter = 'oop'
  vi.mocked(searchProblems).mockRejectedValueOnce(new Error('filter failed'))
  await setupState().handleTypeChange()
  expect(setupState().filteredProblems).toEqual([])
  expect(setupState().total).toBe(0)
  diagnostic.mockRestore()
})
