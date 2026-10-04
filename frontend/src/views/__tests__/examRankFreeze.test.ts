// 验证封榜中的提交显示为问号，解封后显示通过时间与既有错误次数。
import type { RankProblemStats } from '@/types/exam'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { h } from 'vue'

vi.mock('vue-router', () => ({ useRoute: () => ({ params: { id: '1' } }) }))
vi.mock('@/api/exam', () => ({ getExamRank: vi.fn() }))
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn() } }))

import ExamRankView from '../ExamRankView.vue'
import { getExamRank } from '@/api/exam'

beforeEach(() => localStorage.clear())

async function renderRank(stats: RankProblemStats) {
  const row = {
    user_id: 1,
    username: 'bob',
    solved: stats.solved ? 1 : 0,
    penalty: 0,
    problems: { 1: stats },
  }
  vi.mocked(getExamRank).mockResolvedValue({
    exam_title: '比赛',
    problems: [{ problem_id: 1, display_id: 'A' }],
    rank: [row],
  })
  const wrapper = shallowMount(ExamRankView, {
    global: {
      directives: { loading: () => {} },
      stubs: {
        'el-table': { template: '<div><slot /></div>' },
        'el-table-column': {
          setup(_, { slots }) {
            return () => h('div', slots.default?.({ row, $index: 0 }))
          },
        },
        'el-page-header': true,
        'el-card': { template: '<div><slot /></div>' },
        'el-switch': true,
        'el-button': true,
        'el-icon': true,
        'el-avatar': true,
        'el-tag': true,
      },
    },
  })
  await flushPromises()
  return wrapper
}

describe('排行榜封榜展示', () => {
  it('封榜提交显示问号和数量，不展示错误或通过结果', async () => {
    const wrapper = await renderRank({
      solved: false,
      failed_attempts: 1,
      time: 0,
      pending_attempts: 2,
    })
    try {
      expect(wrapper.find('.status-pending').text()).toBe('? 2')
      expect(wrapper.find('.status-wa').exists()).toBe(false)
      expect(wrapper.find('.status-ac').exists()).toBe(false)
    } finally {
      wrapper.unmount()
    }
  })

  it('解封后显示通过时间和此前错误次数', async () => {
    const wrapper = await renderRank({
      solved: true,
      failed_attempts: 1,
      time: 6000,
      pending_attempts: 0,
    })
    try {
      expect(wrapper.find('.status-ac').text()).toContain('1:40')
      expect(wrapper.find('.status-ac').text()).toContain('(+1)')
      expect(wrapper.find('.status-pending').exists()).toBe(false)
    } finally {
      wrapper.unmount()
    }
  })
})
