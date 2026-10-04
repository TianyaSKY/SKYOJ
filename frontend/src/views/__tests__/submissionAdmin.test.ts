import { deferred } from './fixtures'
import type { LegacySubmissionsResponse, SubmissionListResponse } from '@/types/submission'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))
vi.mock('@/api/submission', () => ({ getSubmissions: vi.fn() }))
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn() } }))

import SubmissionAdminView from '../admin/SubmissionAdminView.vue'
import { getSubmissions } from '@/api/submission'
import { ElMessage } from 'element-plus'

let wrapper: ReturnType<typeof mountPage> | undefined
const result = (id: number): SubmissionListResponse => ({
  id,
  user_id: 1,
  username: 'student',
  problem_id: 1,
  exam_id: null,
  status: 'Accepted',
  score: 100,
  language: 'python',
  created_at: null,
})
function mountedWrapper() {
  if (!wrapper) throw new Error('提交管理页未挂载')
  return wrapper
}
// 测试读取 setup 内部状态，公共组件类型只暴露对外接口。
function setupState() {
  return mountedWrapper().vm as unknown as {
    filterForm: { status: string; username: string }
    loading: boolean
    submissions: SubmissionListResponse[]
    pagination: { total: number; page: number }
    handleFilter(): void
    handleCurrentChange(page: number): void
  }
}
beforeEach(() => {
  localStorage.clear()
  vi.clearAllMocks()
  vi.mocked(getSubmissions).mockReset()
  vi.mocked(getSubmissions).mockResolvedValue({ items: [], total: 0 })
})
afterEach(() => {
  wrapper?.unmount()
  wrapper = undefined
  vi.restoreAllMocks()
})

function mountPage(renderFilter = false) {
  const mounted = shallowMount(SubmissionAdminView, {
    global: {
      directives: { loading: () => {} },
      stubs: {
        ...Object.fromEntries(
          [
            'el-button',
            'el-page-header',
            'el-input',
            'el-form-item',
            'el-option',
            'el-select',
            'el-form',
            'el-card',
            'el-table-column',
            'el-link',
            'el-tag',
            'el-table',
            'el-pagination',
          ].map((name) => [name, true]),
        ),
        ...(renderFilter
          ? Object.fromEntries(
              ['el-card', 'el-form', 'el-form-item', 'el-select'].map((name) => [
                name,
                { template: '<div><slot /></div>' },
              ]),
            )
          : {}),
      },
    },
  })
  wrapper = mounted
  return mounted
}

describe('提交管理的筛选恢复与请求顺序', () => {
  it.each(['Compile Error', 'System Error'])('错误筛选使用后端状态 %s', async (status) => {
    mountPage(true)
    const option = mountedWrapper().find(`el-option-stub[value="${status}"]`)
    expect(option.exists()).toBe(true)
    const value = option.attributes('value')
    if (!value) throw new Error('状态选项缺少 value')
    setupState().filterForm.status = value
    setupState().handleFilter()
    await flushPromises()
    expect(getSubmissions).toHaveBeenLastCalledWith({ status, page: 1, per_page: 20 })
  })

  it('恢复旧版编译失败缓存时转换为后端状态', async () => {
    localStorage.setItem('skyoj_submission_filter', JSON.stringify({ status: 'Compilation Error' }))
    mountPage()
    await flushPromises()
    expect(getSubmissions).toHaveBeenCalledWith({ status: 'Compile Error', page: 1, per_page: 20 })
    expect(setupState().filterForm.status).toBe('Compile Error')
  })
  it.each(['{broken', 'null', '[]', '"text"', '42'])(
    '损坏的筛选缓存 %s 不阻止页面加载',
    async (cached) => {
      vi.spyOn(console, 'warn').mockImplementation(() => {})
      localStorage.setItem('skyoj_submission_filter', cached)
      mountPage()
      await flushPromises()
      expect(getSubmissions).toHaveBeenCalledWith({ page: 1, per_page: 20 })
      expect(localStorage.getItem('skyoj_submission_filter')).toBeNull()
      expect(console.warn).toHaveBeenCalled()
    },
  )

  it('恢复有效字段，忽略非字符串字段和额外字段', async () => {
    localStorage.setItem(
      'skyoj_submission_filter',
      JSON.stringify({
        problem_id: '12',
        username: 'alice',
        user_id: result(3),
        status: ['Accepted'],
        extra: 'ignored',
      }),
    )
    mountPage()
    await flushPromises()
    expect(getSubmissions).toHaveBeenCalledWith({
      problem_id: 12,
      username: 'alice',
      page: 1,
      per_page: 20,
    })
  })

  it('较早请求迟到时不能覆盖最新筛选结果或提前关闭加载状态', async () => {
    const first = deferred<LegacySubmissionsResponse>(),
      second = deferred<LegacySubmissionsResponse>()
    vi.mocked(getSubmissions).mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)
    mountPage()
    setupState().filterForm.username = 'alice'
    setupState().handleFilter()
    first.resolve({ items: [result(1)], total: 1 })
    await flushPromises()
    expect(setupState().loading).toBe(true)
    expect(setupState().submissions).toEqual([])
    second.resolve({ items: [result(2)], total: 2 })
    await flushPromises()
    expect(setupState().submissions).toEqual([result(2)])
    expect(setupState().pagination.total).toBe(2)
    expect(setupState().loading).toBe(false)
  })

  it('最新请求完成后，过期请求失败不弹出错误或替换结果', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const first = deferred<LegacySubmissionsResponse>(),
      second = deferred<LegacySubmissionsResponse>()
    vi.mocked(getSubmissions).mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)
    mountPage()
    setupState().handleFilter()
    second.resolve({ items: [result(2)], total: 2 })
    await flushPromises()
    first.reject(new Error('过期请求失败'))
    await flushPromises()
    expect(ElMessage.error).not.toHaveBeenCalled()
    expect(setupState().submissions).toEqual([result(2)])
  })

  it('较早请求在最新结果之后返回也不能覆盖结果', async () => {
    const first = deferred<LegacySubmissionsResponse>(),
      second = deferred<LegacySubmissionsResponse>()
    vi.mocked(getSubmissions).mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)
    mountPage()
    setupState().handleCurrentChange(2)
    second.resolve({ items: [result(2)], total: 40 })
    await flushPromises()
    first.resolve({ items: [result(1)], total: 20 })
    await flushPromises()
    expect(setupState().submissions).toEqual([result(2)])
    expect(setupState().pagination.total).toBe(40)
    expect(setupState().pagination.page).toBe(2)
  })

  it('当前请求失败时仍显示错误并结束加载', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    vi.mocked(getSubmissions).mockRejectedValueOnce(new Error('当前请求失败'))
    mountPage()
    await flushPromises()
    expect(ElMessage.error).toHaveBeenCalledWith('获取提交记录失败')
    expect(setupState().loading).toBe(false)
  })
})
