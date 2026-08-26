// Test 3: Vue 组件示例 SampleButton
/**
 * 验证 Vue 组件的 props/events:
 * - props 显示 label；
 * - 切换 variant 类名；
 * - disabled 禁止点击；
 * - click 事件正常 emit。
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import SampleButton from './SampleButton.vue'

describe('SampleButton.vue', () => {
  it('默认渲染 label 为 "Click me"', () => {
    const wrapper = mount(SampleButton)
    expect(wrapper.text()).toBe('Click me')
    expect(wrapper.classes()).toContain('primary')
  })

  it('variant=success 时 class 包含 success', () => {
    const wrapper = mount(SampleButton, { props: { variant: 'success' } })
    expect(wrapper.classes()).toContain('success')
  })

  it('点击时 emit click 事件', async () => {
    const wrapper = mount(SampleButton, { props: { label: '提交' } })
    await wrapper.trigger('click')
    expect(wrapper.emitted('click')).toHaveLength(1)
  })

  it('disabled=true 时点击不 emit', async () => {
    const wrapper = mount(SampleButton, { props: { disabled: true, label: '提交' } })
    await wrapper.trigger('click')
    expect(wrapper.emitted('click')).toBeUndefined()
  })

  it('插槽优先级高于 label', () => {
    const wrapper = mount(SampleButton, {
      props: { label: '默认文字' },
      slots: { default: '自定义内容' },
    })
    expect(wrapper.text()).toBe('自定义内容')
  })
})
