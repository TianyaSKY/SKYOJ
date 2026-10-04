/**
 * 用户 Store 单元测试
 * 测试登录、登出、状态管理等
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '@/stores/user'

// Mock request
vi.mock('@/utils/request', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
}))

// Mock element-plus
vi.mock('element-plus', () => ({
  ElMessage: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

describe('useUserStore', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  afterEach(() => vi.restoreAllMocks())

  it.each(['{broken', '[]', '"teacher"', '42', 'true', '', '{"id":"1"}', '{"role":123}', '{"username":null}'])('无效用户缓存 %s 不阻断初始化', cached => {
    localStorage.setItem('token', 'existing-token')
    localStorage.setItem('user', cached)
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})

    const store = useUserStore()

    expect(store.user).toBeNull()
    expect(store.token).toBe('existing-token')
    expect(localStorage.getItem('token')).toBe('existing-token')
    expect(localStorage.getItem('user')).toBeNull()
    expect(warn).toHaveBeenCalled()
  })

  it('缓存中的 null 表示无用户资料', () => {
    localStorage.setItem('user', 'null')
    expect(useUserStore().user).toBeNull()
  })

  it('初始化时应从 localStorage 读取 token', () => {
    localStorage.setItem('token', 'test_token_123')
    localStorage.setItem('user', JSON.stringify({ id: 1, username: 'testuser' }))

    const store = useUserStore()
    expect(store.token).toBe('test_token_123')
    expect(store.user).toEqual({ id: 1, username: 'testuser' })
  })

  it('初始化时无 token', () => {
    const store = useUserStore()
    expect(store.token).toBe('')
    expect(store.user).toBeNull()
  })

  it('login 成功后设置 token 和 user', async () => {
    const request = vi.mocked(await import('@/utils/request')).default
    vi.mocked(request.post).mockResolvedValue({
      token: 'new_token_456',
      user: { id: 2, username: 'newuser', role: 'student' },
    })

    const store = useUserStore()
    const result = await store.login({ username: 'newuser', password: 'password' })

    expect(result).toBe(true)
    expect(store.token).toBe('new_token_456')
    expect(store.user).toEqual({ id: 2, username: 'newuser', role: 'student' })
    expect(localStorage.getItem('token')).toBe('new_token_456')
  })

  it('login 失败时返回 false 并抛出错误', async () => {
    const request = vi.mocked(await import('@/utils/request')).default
    vi.mocked(request.post).mockRejectedValue(new Error('Invalid credentials'))

    const store = useUserStore()

    await expect(store.login({ username: 'wrong', password: 'wrong' })).rejects.toThrow('Invalid credentials')
    expect(store.token).toBe('')
  })

  it('会话令牌更新同步缓存并保留用户资料', () => {
    const store = useUserStore()
    store.user = { id: 1, role: 'student' }
    store.setToken('exam-token')
    expect(store.token).toBe('exam-token')
    expect(localStorage.getItem('token')).toBe('exam-token')
    expect(store.user).toEqual({ id: 1, role: 'student' })
  })

  it('logout 清除 token 和 user', () => {
    const store = useUserStore()

    // 先设置状态
    store.token = 'some_token'
    store.user = { id: 1, username: 'test' }

    store.logout()

    expect(store.token).toBe('')
    expect(store.user).toBeNull()
    expect(localStorage.getItem('token')).toBeNull()
  })

  it('logout 清除 localStorage 中的用户数据', () => {
    localStorage.setItem('token', 'token_to_remove')
    localStorage.setItem('user', JSON.stringify({ id: 1 }))

    const store = useUserStore()
    store.logout()

    expect(localStorage.getItem('token')).toBeNull()
    expect(localStorage.getItem('user')).toBeNull()
  })
})
