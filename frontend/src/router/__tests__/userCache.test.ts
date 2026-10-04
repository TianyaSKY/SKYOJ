// 执行真实注册的路由守卫，验证用户资料为空或损坏时仍能给出导航结果。
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('vue-router', () => ({
  createWebHistory: vi.fn(),
  createRouter: vi.fn(() => ({ beforeEach: vi.fn() })),
}))
vi.mock('@/views/HomeView.vue', () => ({ default: {} }))
vi.mock('@/stores/sys', () => ({ useSysStore: () => ({ loaded: true, practice: true }) }))
vi.mock('@/utils/request', () => ({ default: {} }))

import type { RouteLocationNormalized } from 'vue-router'
import router from '../index'
import { useUserStore } from '@/stores/user'

const guard = vi.mocked(router.beforeEach).mock.calls[0]![0]
const emptyRoute = {} as RouteLocationNormalized

beforeEach(() => {
  localStorage.clear()
  setActivePinia(createPinia())
})

describe('路由守卫读取用户状态', () => {
  it('用户缓存为 null 时可进入公开页面', async () => {
    localStorage.setItem('user', 'null')
    const next = vi.fn()
    await guard.call(
      undefined,
      { name: 'home', meta: {} } as RouteLocationNormalized,
      emptyRoute,
      next,
    )
    expect(next).toHaveBeenCalledWith()
  })

  it('Store 初始化后缓存损坏，受保护页面仍可跳转到登录', async () => {
    useUserStore()
    localStorage.setItem('user', '{broken')
    const next = vi.fn()
    await guard.call(
      undefined,
      {
        name: 'profile',
        fullPath: '/profile',
        meta: { requiresAuth: true },
      } as RouteLocationNormalized,
      emptyRoute,
      next,
    )
    expect(next).toHaveBeenCalledWith({ name: 'login', query: { redirect: '/profile' } })
  })
})
