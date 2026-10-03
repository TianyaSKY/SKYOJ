// 验证真实请求拦截器与用户 Store 在登录失效时保持一致。
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises } from '@vue/test-utils'

vi.mock('element-plus', () => ({
  ElMessageBox: { confirm: vi.fn() },
  ElMessage: { error: vi.fn() },
}))
vi.mock('@/router', () => ({
  default: { currentRoute: { value: { name: 'home' } }, push: vi.fn() },
}))

import { ElMessageBox } from 'element-plus'
import router from '@/router'
import request from '@/utils/request'
import { useUserStore } from '@/stores/user'

const originalAdapter = request.defaults.adapter
let store

beforeEach(() => {
  vi.clearAllMocks()
  setActivePinia(createPinia())
  localStorage.setItem('token', 'expired-token')
  localStorage.setItem('user', JSON.stringify({ id: 1, role: 'teacher' }))
  store = useUserStore()
  router.currentRoute.value.name = 'home'
  router.push.mockResolvedValue(undefined)
  ElMessageBox.confirm.mockResolvedValue('confirm')
  request.defaults.adapter = config => Promise.reject({
    config,
    response: { status: 401, data: { code: 'AUTH_TOKEN_EXPIRED', error: '登录已过期' } },
  })
})

afterEach(async () => {
  await flushPromises()
  request.defaults.adapter = originalAdapter
  localStorage.clear()
  vi.restoreAllMocks()
})

async function expiredRequest(config) {
  await expect(request.get('/private', config)).rejects.toMatchObject({ code: 'AUTH_TOKEN_EXPIRED' })
}

describe('登录失效后的恢复流程', () => {
  it('确认重新登录时同时清除持久化和响应式状态', async () => {
    await expiredRequest()
    await flushPromises()

    expect(localStorage.getItem('token')).toBeNull()
    expect(localStorage.getItem('user')).toBeNull()
    expect(store.token).toBe('')
    expect(store.user).toBeNull()
    expect(router.push).toHaveBeenCalledWith('/login')
  })

  it.each(['cancel', 'close'])('弹窗 %s 不产生未处理拒绝，也不清除登录状态', async action => {
    ElMessageBox.confirm.mockRejectedValue(action)
    await expiredRequest()
    await flushPromises()

    expect(store.token).toBe('expired-token')
    expect(localStorage.getItem('token')).toBe('expired-token')
    expect(router.push).not.toHaveBeenCalled()
  })

  it('并发失效请求只显示一个弹窗，关闭后允许再次提示', async () => {
    let dismiss
    ElMessageBox.confirm.mockImplementationOnce(() => new Promise((resolve, reject) => { dismiss = reject }))
    await Promise.all([expiredRequest(), expiredRequest()])
    expect(ElMessageBox.confirm).toHaveBeenCalledTimes(1)

    dismiss('cancel')
    await flushPromises()
    await expiredRequest()
    await flushPromises()
    expect(ElMessageBox.confirm).toHaveBeenCalledTimes(2)
  })

  it('登录接口跳过恢复弹窗', async () => {
    await expiredRequest({ skipAuthErrorHandler: true })
    expect(ElMessageBox.confirm).not.toHaveBeenCalled()
    expect(store.token).toBe('expired-token')
  })

  it('已在登录页时清除旧状态且不重复跳转', async () => {
    router.currentRoute.value.name = 'login'
    await expiredRequest()
    await flushPromises()
    expect(store.token).toBe('')
    expect(router.push).not.toHaveBeenCalled()
  })

  it('跳转失败记录原因并释放弹窗锁，允许再次提示', async () => {
    const error = new Error('路由加载失败')
    const log = vi.spyOn(console, 'error').mockImplementation(() => {})
    router.push.mockRejectedValueOnce(error)
    await expiredRequest()
    await flushPromises()

    expect(log).toHaveBeenCalledWith('登录失效恢复失败', error)
    expect(store.token).toBe('')
    await expiredRequest()
    await flushPromises()
    expect(ElMessageBox.confirm).toHaveBeenCalledTimes(2)
  })
})
