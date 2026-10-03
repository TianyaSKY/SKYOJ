import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))
vi.mock('@/api/submission', () => ({ getSubmissions: vi.fn() }))
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn() } }))

import SubmissionAdminView from '../admin/SubmissionAdminView.vue'
import { getSubmissions } from '@/api/submission'
import { ElMessage } from 'element-plus'

let wrapper
beforeEach(() => {
  localStorage.clear()
  vi.clearAllMocks()
  getSubmissions.mockReset()
  getSubmissions.mockResolvedValue({ items: [], total: 0 })
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined; vi.restoreAllMocks() })

function mountPage(renderFilter = false) {
  wrapper = shallowMount(SubmissionAdminView, {
    global: {
      directives: { loading: () => {} },
      stubs: { ...Object.fromEntries([
        'el-button', 'el-page-header', 'el-input', 'el-form-item', 'el-option', 'el-select',
        'el-form', 'el-card', 'el-table-column', 'el-link', 'el-tag', 'el-table', 'el-pagination',
      ].map(name => [name, true])),
        ...(renderFilter ? Object.fromEntries(['el-card', 'el-form', 'el-form-item', 'el-select']
          .map(name => [name, { template: '<div><slot /></div>' }])) : {}),
      },
    },
  })
  return wrapper
}

function deferred() {
  let resolve, reject
  const promise = new Promise((res, rej) => { resolve = res; reject = rej })
  return { promise, resolve, reject }
}

describe('提交管理的筛选恢复与请求顺序', () => {
  it('编译失败筛选使用判题后端的 Compile Error 状态', async () => {
    mountPage(true)
    const option = wrapper.find('el-option-stub[value="Compile Error"]')
    expect(option.exists()).toBe(true)
    wrapper.vm.filterForm.status = option.attributes('value')
    wrapper.vm.handleFilter()
    await flushPromises()
    expect(getSubmissions).toHaveBeenLastCalledWith({ status: 'Compile Error', page: 1, per_page: 20 })
  })

  it('恢复旧版编译失败缓存时转换为后端状态', async () => {
    localStorage.setItem('skyoj_submission_filter', JSON.stringify({ status: 'Compilation Error' }))
    mountPage()
    await flushPromises()
    expect(getSubmissions).toHaveBeenCalledWith({ status: 'Compile Error', page: 1, per_page: 20 })
    expect(wrapper.vm.filterForm.status).toBe('Compile Error')
  })
  it.each(['{broken', 'null', '[]', '"text"', '42'])('损坏的筛选缓存 %s 不阻止页面加载', async (cached) => {
    vi.spyOn(console, 'warn').mockImplementation(() => {})
    localStorage.setItem('skyoj_submission_filter', cached)
    mountPage()
    await flushPromises()
    expect(getSubmissions).toHaveBeenCalledWith({ page: 1, per_page: 20 })
    expect(localStorage.getItem('skyoj_submission_filter')).toBeNull()
    expect(console.warn).toHaveBeenCalled()
  })

  it('恢复有效字段，忽略非字符串字段和额外字段', async () => {
    localStorage.setItem('skyoj_submission_filter', JSON.stringify({
      problem_id: '12', username: 'alice', user_id: { id: 3 }, status: ['Accepted'], extra: 'ignored',
    }))
    mountPage()
    await flushPromises()
    expect(getSubmissions).toHaveBeenCalledWith({ problem_id: '12', username: 'alice', page: 1, per_page: 20 })
  })

  it('较早请求迟到时不能覆盖最新筛选结果或提前关闭加载状态', async () => {
    const first = deferred(), second = deferred()
    getSubmissions.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)
    mountPage()
    wrapper.vm.filterForm.username = 'alice'
    wrapper.vm.handleFilter()
    first.resolve({ items: [{ id: 1 }], total: 1 })
    await flushPromises()
    expect(wrapper.vm.loading).toBe(true)
    expect(wrapper.vm.submissions).toEqual([])
    second.resolve({ items: [{ id: 2 }], total: 2 })
    await flushPromises()
    expect(wrapper.vm.submissions).toEqual([{ id: 2 }])
    expect(wrapper.vm.pagination.total).toBe(2)
    expect(wrapper.vm.loading).toBe(false)
  })

  it('最新请求完成后，过期请求失败不弹出错误或替换结果', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const first = deferred(), second = deferred()
    getSubmissions.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)
    mountPage()
    wrapper.vm.handleFilter()
    second.resolve({ items: [{ id: 2 }], total: 2 })
    await flushPromises()
    first.reject(new Error('过期请求失败'))
    await flushPromises()
    expect(ElMessage.error).not.toHaveBeenCalled()
    expect(wrapper.vm.submissions).toEqual([{ id: 2 }])
  })

  it('较早请求在最新结果之后返回也不能覆盖结果', async () => {
    const first = deferred(), second = deferred()
    getSubmissions.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)
    mountPage()
    wrapper.vm.handleCurrentChange(2)
    second.resolve({ items: [{ id: 2 }], total: 40 })
    await flushPromises()
    first.resolve({ items: [{ id: 1 }], total: 20 })
    await flushPromises()
    expect(wrapper.vm.submissions).toEqual([{ id: 2 }])
    expect(wrapper.vm.pagination.total).toBe(40)
    expect(wrapper.vm.pagination.page).toBe(2)
  })

  it('当前请求失败时仍显示错误并结束加载', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    getSubmissions.mockRejectedValueOnce(new Error('当前请求失败'))
    mountPage()
    await flushPromises()
    expect(ElMessage.error).toHaveBeenCalledWith('获取提交记录失败')
    expect(wrapper.vm.loading).toBe(false)
  })
})
