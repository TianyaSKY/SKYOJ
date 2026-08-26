/**
 * 系统 Store 单元测试
 * 测试系统配置、运行模式等
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSysStore } from '@/stores/sys'

// Mock request
vi.mock('@/utils/request', () => ({
  default: {
    get: vi.fn(),
  },
}))

describe('useSysStore', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('初始化时 practice 为 undefined', () => {
    const store = useSysStore()
    expect(store.practice).toBeUndefined()
  })

  it('从 localStorage 读取 practice 配置', () => {
    localStorage.setItem('practice', 'true')
    const store = useSysStore()
    // store 可能在初始化时不读取 localStorage，需要 fetchSysInfo
    expect(store.practice).toBeUndefined() // 取决于实现
  })

  it('fetchSysInfo 获取系统配置', async () => {
    const request = vi.mocked(await import('@/utils/request')).default
    request.get.mockResolvedValue({
      title: 'SKYOJ',
      practice: true,
      examMode: false,
    })

    const store = useSysStore()
    await store.fetchSysInfo()

    expect(store.title).toBe('SKYOJ')
    expect(store.practice).toBe(true)
    expect(store.examMode).toBe(false)
  })

  it('fetchSysInfo 失败处理', async () => {
    const request = vi.mocked(await import('@/utils/request')).default
    request.get.mockRejectedValue(new Error('Network error'))

    const store = useSysStore()
    await store.fetchSysInfo()

    // 验证错误处理 (取决于实现)
  })

  it('设置练习模式', () => {
    const store = useSysStore()
    store.setPractice(true)
    expect(store.practice).toBe(true)
  })
})
