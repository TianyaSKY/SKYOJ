import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import SubmissionHeatmap from '../SubmissionHeatmap.vue'
let wrapper
const submitted = date => ({ created_at: date.toISOString() })
beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(2026, 5, 15, 12))
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined; vi.useRealTimers() })
function mountActivity(submissions) {
  wrapper = mount(SubmissionHeatmap, { props: { submissions } })
}
it('近一年统计与格子一致，不包含旧记录、未来日期或无效日期', () => {
  mountActivity([
    submitted(new Date(2024, 0, 1)),
    submitted(new Date(2025, 5, 14, 12)),
    submitted(new Date(2025, 5, 15, 12)),
    submitted(new Date(2026, 5, 15, 1)),
    submitted(new Date(2026, 5, 16)),
    { created_at: null }, { created_at: 'invalid' },
  ])
  expect(wrapper.vm.totalSubmissions).toBe(2)
  expect(wrapper.vm.weeks.flat().reduce((sum, day) => sum + day.count, 0)).toBe(2)
  expect(wrapper.text()).toContain('2 submissions in the last year')
})
it('UTC 与带偏移时间按浏览器本地日历归到同一天', () => {
  const local = new Date(2026, 5, 15, 1)
  const utc = local.toISOString()
  mountActivity([{ created_at: utc }, { created_at: utc.slice(0, -1) }])
  const day = wrapper.vm.weeks.flat().find(day => day.date === '2026-06-15')
  expect(day.count).toBe(2)
})
it('跨夏令时的日历每周七天，日期连续且不会重复', () => {
  mountActivity([])
  expect(wrapper.vm.weeks.every(week => week.length === 7)).toBe(true)
  const days = wrapper.vm.weeks.flat()
  expect(new Set(days.map(day => day.date)).size).toBe(days.length)
  for (let index = 1; index < days.length; index++) {
    const [year, month, day] = days[index - 1].date.split('-').map(Number)
    const next = new Date(year, month - 1, day + 1, 12)
    const expected = `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, '0')}-${String(next.getDate()).padStart(2, '0')}`
    expect(days[index].date).toBe(expected)
  }
})
it('闰年日对应上一年二月末，首周补齐日期不计入一年内统计', () => {
  vi.setSystemTime(new Date(2024, 1, 29, 12))
  mountActivity([submitted(new Date(2023, 1, 27, 12)), submitted(new Date(2023, 1, 28, 12)), submitted(new Date(2024, 1, 29, 1))])
  expect(wrapper.vm.totalSubmissions).toBe(2)
  expect(wrapper.vm.weeks.flat().find(day => day.date === '2023-02-28').count).toBe(1)
})
it('提交数据更新后重新计算活跃度', async () => {
  mountActivity([])
  await wrapper.setProps({ submissions: [submitted(new Date(2026, 5, 15, 1))] })
  expect(wrapper.vm.totalSubmissions).toBe(1)
})
