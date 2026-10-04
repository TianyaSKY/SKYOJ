/** 系统配置 Store 的真实接口与降级行为。 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSysStore } from '@/stores/sys'
import { getSysInfo } from '@/api/sys'

vi.mock('@/api/sys', () => ({ getSysInfo: vi.fn() }))

describe('useSysStore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('默认允许练习并且无警告', () => {
    const store = useSysStore()
    expect(store.practice).toBe(true)
    expect(store.warning).toBe(false)
    expect(store.loaded).toBe(false)
  })

  it('获取系统配置并更新文档标题', async () => {
    vi.mocked(getSysInfo).mockResolvedValue({
      title: '课堂 OJ',
      practice: false,
      warning: true,
      info: '通知',
    })
    const store = useSysStore()
    await store.fetchSysInfo()
    expect(getSysInfo).toHaveBeenCalledOnce()
    expect(store.title).toBe('课堂 OJ')
    expect(document.title).toBe('课堂 OJ')
    expect(store.practice).toBe(false)
    expect(store.warning).toBe(true)
    expect(store.info).toBe('通知')
    expect(store.loaded).toBe(true)
  })

  it('网络失败时保留当前配置并记录错误', async () => {
    const error = new Error('Network error')
    vi.mocked(getSysInfo).mockRejectedValue(error)
    const logged = vi.spyOn(console, 'error').mockImplementation(() => {})
    try {
      const store = useSysStore()
      await store.fetchSysInfo()
      expect(store.practice).toBe(true)
      expect(store.loaded).toBe(false)
      expect(logged).toHaveBeenCalledWith('Failed to fetch system info:', error)
    } finally {
      logged.mockRestore()
    }
  })
})
