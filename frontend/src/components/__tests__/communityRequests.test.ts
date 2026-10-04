import type { TagResponse, SolutionListItemResponse } from '@/types/community'
import { isRecord } from '@/types/http'
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'

const originalAdapter = request.defaults.adapter
let urls: string[]
let wrapper: ReturnType<typeof shallowMount> | undefined
let calls: [string | undefined, string][]
let writes: Record<string, unknown>[]
function mountedWrapper() {
  if (!wrapper) throw new Error('社区面板未挂载')
  return wrapper
}
// 部分样例刻意只携带该行为会读取的字段，保留原测试的历史响应兼容场景。
type TestSolution = Pick<SolutionListItemResponse, 'id'> & Partial<SolutionListItemResponse>
function tagState() {
  return mountedWrapper().vm as unknown as {
    isTeacher: boolean; selectedTagId: number | null; openAttach(): void; confirmAttach(): Promise<void>;
    detach(tag: Pick<TagResponse, 'id' | 'name'>): Promise<void>;
  }
}
function solutionState() {
  return mountedWrapper().vm as unknown as {
    isTeacher: boolean; userInfo: { id?: number }; solutions: SolutionListItemResponse[];
    form: { title: string; content: string; language: string }; newComment: string;
    toggleLike(item: TestSolution): Promise<void>; toggleFavorite(item: TestSolution): Promise<void>;
    openComments(item: TestSolution): Promise<void>; openWrite(item?: TestSolution): void;
    submitSolution(): Promise<void>; hideSolution(item: TestSolution): Promise<void>;
    submitComment(): Promise<void>; deleteComment(id: number): Promise<void>;
  }
}
const mountOptions = {
  props: { problemId: 42 },
  global: { stubs: Object.fromEntries([
    'el-tag', 'el-icon', 'el-button', 'el-option', 'el-select', 'el-form-item',
    'el-form', 'el-dialog', 'el-checkbox', 'el-card', 'el-empty', 'el-input',
    'el-skeleton', 'el-pagination', 'Plus',
  ].map(name => [name, true])) },
}

beforeEach(() => {
  vi.clearAllMocks()
  localStorage.clear()
  setActivePinia(createPinia())
  urls = []
  calls = []
  writes = []
  vi.mocked(ElMessageBox.confirm).mockResolvedValue('confirm' as Awaited<ReturnType<typeof ElMessageBox.confirm>>)
  request.defaults.adapter = config => {
    urls.push(request.getUri(config))
    calls.push([config.method, request.getUri(config)])
    if (config.method === 'post') {
      const body: unknown = JSON.parse(config.data || '{}')
      if (!isRecord(body)) throw new Error('请求体应为对象')
      writes.push(body)
    }
    return Promise.resolve({
      data: config.url?.includes('solutions') ? { items: [], total: 0 } : [],
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
    tagState().openAttach()
    tagState().selectedTagId = 7
    await tagState().confirmAttach()
    await tagState().detach({id: 7, name: '数组'})
    await flushPromises()
    expect(calls).toContainEqual(['post', '/api/tags/problems/42/attach'])
    expect(calls).toContainEqual(['delete', '/api/tags/problems/42/7'])
    expect(urls.every(url => !url.startsWith('/api/api/'))).toBe(true)
  })

  it('题解点赞、收藏和评论读取使用后端真实路径', async () => {
    wrapper = shallowMount(SolutionPanel, mountOptions)
    await flushPromises()
    const item = {id: 7, comment_count: 0}
    await solutionState().toggleLike(item)
    await solutionState().toggleFavorite(item)
    await solutionState().openComments(item)
    await flushPromises()
    expect(calls).toContainEqual(['post', '/api/problems/solutions/7/like'])
    expect(calls).toContainEqual(['post', '/api/problems/solutions/7/favorite'])
    expect(calls).toContainEqual(['get', '/api/problems/solutions/7/comments?page=1&page_size=50'])
    expect(urls.every(url => !url.startsWith('/api/api/'))).toBe(true)
  })

  it('题解发布、修改、隐藏和评论写入使用后端真实路径', async () => {
    wrapper = shallowMount(SolutionPanel, mountOptions)
    await flushPromises()
    solutionState().openWrite()
    solutionState().form.title = '题解'
    solutionState().form.content = '解法'
    await solutionState().submitSolution()
    const item = {id: 7, title: '题解', content: '解法', comment_count: 1}
    solutionState().openWrite(item)
    await solutionState().submitSolution()
    await solutionState().hideSolution(item)
    await solutionState().openComments(item)
    solutionState().newComment = '评论'
    await solutionState().submitComment()
    await solutionState().deleteComment(8)
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
    expect(tagState().isTeacher).toBe(true)

    store.logout()
    await flushPromises()
    expect(tagState().isTeacher).toBe(false)
  })

  it('登出和切换用户时题解面板同步角色与作者身份', async () => {
    const store = useUserStore()
    store.user = {id: 1, role: 'teacher'}
    wrapper = shallowMount(SolutionPanel, mountOptions)
    await flushPromises()
    expect(solutionState().isTeacher).toBe(true)
    expect(solutionState().userInfo.id).toBe(1)

    store.logout()
    await flushPromises()
    expect(solutionState().isTeacher).toBe(false)
    expect(solutionState().userInfo.id).toBeUndefined()
    store.user = {id: 2, role: 'student'}
    await flushPromises()
    expect(solutionState().userInfo.id).toBe(2)
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

    expect(mountedWrapper().find('.solution-body').html()).toContain('<h2>解法</h2>')
    expect(solutionState().solutions[0].liked_by_me).toBe(true)
    expect(solutionState().solutions[0].favorited_by_me).toBe(true)
    solutionState().openWrite(solutionState().solutions[0])
    expect(solutionState().form.content).toBe('## 解法\n原文')
  })

  it.each([['teacher', true], ['student', false]] as const)('标签提交按当前 %s 身份设置审批状态', async (role, expected) => {
    useUserStore().user = {id: 1, role}
    wrapper = shallowMount(TagPanel, mountOptions)
    await flushPromises()
    tagState().openAttach()
    tagState().selectedTagId = 7
    await tagState().confirmAttach()
    expect(writes).toContainEqual({tag_id: 7, approved: expected})
  })

  it('标签对话框打开后角色变更，提交时不保留旧教师审批状态', async () => {
    const store = useUserStore()
    store.user = {id: 1, role: 'teacher'}
    wrapper = shallowMount(TagPanel, mountOptions)
    await flushPromises()
    tagState().openAttach()
    tagState().selectedTagId = 7
    store.user = {id: 2, role: 'student'}
    await tagState().confirmAttach()
    expect(writes).toContainEqual({tag_id: 7, approved: false})
  })

  it('学生没有教师认证标签的勾选项', async () => {
    useUserStore().user = {id: 1, role: 'student'}
    wrapper = shallowMount(TagPanel, {
      ...mountOptions,
      global: {...mountOptions.global, renderStubDefaultSlot: true},
    })
    await flushPromises()
    tagState().openAttach()
    await flushPromises()
    expect(mountedWrapper().find('el-checkbox-stub').exists()).toBe(false)
  })

  it.each([
    ['短标题', {title: '一'}], ['长标题', {title: 'x'.repeat(201)}],
    ['空白正文', {content: '  \n  '}], ['长正文', {content: 'x'.repeat(20001)}],
    ['长语言字段', {language: 'x'.repeat(51)}],
  ] as const)('题解无效字段在发请求前被拦截：%s', async (label, patch) => {
    wrapper = shallowMount(SolutionPanel, mountOptions)
    await flushPromises()
    solutionState().openWrite()
    solutionState().form = {title: '题解', content: '正文', language: '', ...patch}
    await solutionState().submitSolution()
    expect(writes).toEqual([])
    expect(ElMessage.warning).toHaveBeenCalled()
  })

  it('题解长度边界有效，Markdown 缩进不会被校验删除', async () => {
    wrapper = shallowMount(SolutionPanel, mountOptions)
    await flushPromises()
    const content = '    ' + 'x'.repeat(19995) + '\n'
    solutionState().openWrite()
    solutionState().form = {title: 'x'.repeat(200), content, language: 'x'.repeat(50)}
    await solutionState().submitSolution()
    expect(writes).toHaveLength(1)
    expect(writes[0]?.content).toBe(content)
    expect(ElMessage.warning).not.toHaveBeenCalled()
  })

  it('超长评论不发请求并保留输入', async () => {
    wrapper = shallowMount(SolutionPanel, mountOptions)
    await flushPromises()
    await solutionState().openComments({id: 7, comment_count: 0})
    solutionState().newComment = 'x'.repeat(1001)
    await solutionState().submitComment()
    expect(writes).toEqual([])
    expect(solutionState().newComment).toHaveLength(1001)
    expect(ElMessage.warning).toHaveBeenCalled()
  })
})
