// 使用真实 Axios 实例验证组件请求经过 baseURL 拼接后的地址。
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/router', () => ({ default: {} }))
vi.mock('element-plus', () => ({
  ElMessage: { error: vi.fn(), success: vi.fn(), warning: vi.fn() },
  ElMessageBox: { confirm: vi.fn() },
}))

import request from '@/utils/request'
import TagPanel from '../TagPanel.vue'
import SolutionPanel from '../SolutionPanel.vue'
import { ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'

const originalAdapter = request.defaults.adapter
let urls
let wrapper
let calls
const mountOptions = {
  props: { problemId: 42 },
  global: { stubs: Object.fromEntries([
    'el-tag', 'el-icon', 'el-button', 'el-option', 'el-select', 'el-form-item',
    'el-form', 'el-dialog', 'el-checkbox', 'el-card', 'el-empty', 'el-input',
    'el-skeleton', 'el-pagination', 'Plus',
  ].map(name => [name, true])) },
}

beforeEach(() => {
  localStorage.clear()
  setActivePinia(createPinia())
  urls = []
  calls = []
  ElMessageBox.confirm.mockResolvedValue('confirm')
  request.defaults.adapter = config => {
    urls.push(request.getUri(config))
    calls.push([config.method, request.getUri(config)])
    return Promise.resolve({
      data: config.url.includes('solutions') ? { items: [], total: 0 } : [],
      status: 200, statusText: 'OK', headers: {}, config,
    })
  }
})

afterEach(() => {
  wrapper?.unmount()
  request.defaults.adapter = originalAdapter
})

describe('社区组件的 API 请求路径', () => {
  it('标签面板只添加一次 API 前缀', async () => {
    wrapper = shallowMount(TagPanel, mountOptions)
    await flushPromises()
    expect(urls).toEqual(['/api/tags/problems/42', '/api/tags'])
  })

  it('题解面板只添加一次 API 前缀且保留分页参数', async () => {
    wrapper = shallowMount(SolutionPanel, mountOptions)
    await flushPromises()
    expect(urls).toEqual(['/api/problems/42/solutions?page=1&page_size=20'])
  })

  it('挂标签和移除标签也只添加一次 API 前缀', async () => {
    wrapper = shallowMount(TagPanel, mountOptions)
    await flushPromises()
    wrapper.vm.selectedTagId = 7
    await wrapper.vm.confirmAttach()
    await wrapper.vm.detach({id: 7, name: '数组'})
    await flushPromises()
    expect(calls).toContainEqual(['post', '/api/tags/problems/42/attach'])
    expect(calls).toContainEqual(['delete', '/api/tags/problems/42/7'])
    expect(urls.every(url => !url.startsWith('/api/api/'))).toBe(true)
  })

  it('题解点赞、收藏和评论读取使用后端真实路径', async () => {
    wrapper = shallowMount(SolutionPanel, mountOptions)
    await flushPromises()
    const item = {id: 7, comment_count: 0}
    await wrapper.vm.toggleLike(item)
    await wrapper.vm.toggleFavorite(item)
    await wrapper.vm.openComments(item)
    await flushPromises()
    expect(calls).toContainEqual(['post', '/api/problems/solutions/7/like'])
    expect(calls).toContainEqual(['post', '/api/problems/solutions/7/favorite'])
    expect(calls).toContainEqual(['get', '/api/problems/solutions/7/comments?page=1&page_size=50'])
    expect(urls.every(url => !url.startsWith('/api/api/'))).toBe(true)
  })

  it('题解发布、修改、隐藏和评论写入使用后端真实路径', async () => {
    wrapper = shallowMount(SolutionPanel, mountOptions)
    await flushPromises()
    wrapper.vm.openWrite()
    wrapper.vm.form.title = '题解'
    wrapper.vm.form.content = '解法'
    await wrapper.vm.submitSolution()
    const item = {id: 7, title: '题解', content: '解法', comment_count: 1}
    wrapper.vm.openWrite(item)
    await wrapper.vm.submitSolution()
    await wrapper.vm.hideSolution(item)
    await wrapper.vm.openComments(item)
    wrapper.vm.newComment = '评论'
    await wrapper.vm.submitComment()
    await wrapper.vm.deleteComment(8)
    await flushPromises()

    expect(calls).toContainEqual(['post', '/api/problems/42/solutions'])
    expect(calls).toContainEqual(['put', '/api/problems/solutions/7'])
    expect(calls).toContainEqual(['delete', '/api/problems/solutions/7'])
    expect(calls).toContainEqual(['post', '/api/problems/solutions/7/comments'])
    expect(calls).toContainEqual(['delete', '/api/problems/comments/8'])
    expect(urls.every(url => !url.startsWith('/api/api/'))).toBe(true)
  })

  it('教师登出后标签面板及时撤销教师状态', async () => {
    const store = useUserStore()
    store.user = {id: 1, role: 'teacher'}
    wrapper = shallowMount(TagPanel, mountOptions)
    await flushPromises()
    expect(wrapper.vm.isTeacher).toBe(true)

    store.logout()
    await flushPromises()
    expect(wrapper.vm.isTeacher).toBe(false)
  })

  it('登出和切换用户时题解面板同步角色与作者身份', async () => {
    const store = useUserStore()
    store.user = {id: 1, role: 'teacher'}
    wrapper = shallowMount(SolutionPanel, mountOptions)
    await flushPromises()
    expect(wrapper.vm.isTeacher).toBe(true)
    expect(wrapper.vm.userInfo.id).toBe(1)

    store.logout()
    await flushPromises()
    expect(wrapper.vm.isTeacher).toBe(false)
    expect(wrapper.vm.userInfo.id).toBeUndefined()
    store.user = {id: 2, role: 'student'}
    await flushPromises()
    expect(wrapper.vm.userInfo.id).toBe(2)
  })

  it('列表返回正文和交互状态后，题解可展示并保留原文编辑', async () => {
    const item = {
      id: 7, author_id: 1, title: '完整题解', content: '## 解法\n原文',
      liked_by_me: true, favorited_by_me: true, vote_count: 1, comment_count: 0,
    }
    request.defaults.adapter = config => Promise.resolve({
      data: {items: [item], total: 1}, status: 200, statusText: 'OK', headers: {}, config,
    })
    wrapper = shallowMount(SolutionPanel, {
      ...mountOptions,
      global: {
        stubs: {
          ...mountOptions.global.stubs,
          'el-card': {template: '<div><slot /></div>'},
        },
      },
    })
    await flushPromises()

    expect(wrapper.find('.solution-body').html()).toContain('<h2>解法</h2>')
    expect(wrapper.vm.solutions[0].liked_by_me).toBe(true)
    expect(wrapper.vm.solutions[0].favorited_by_me).toBe(true)
    wrapper.vm.openWrite(wrapper.vm.solutions[0])
    expect(wrapper.vm.form.content).toBe('## 解法\n原文')
  })
})
