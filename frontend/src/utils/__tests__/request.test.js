// Test 1: request.js 错误码拦截器
/**
 * 验证 request.js 的响应拦截器能在 401 / 5xx 时把
 * 后端 envelope 中的 code 字段挂到 error.code 上。
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises } from '@vue/test-utils'

// Mock element-plus + router，避免弹窗副作用。
vi.mock('element-plus', () => ({
  ElMessageBox: { confirm: vi.fn().mockResolvedValue(undefined) },
}))
vi.mock('@/router', () => ({
  default: { currentRoute: { value: { name: 'home' } }, push: vi.fn() },
}))

import request from '@/utils/request'

beforeEach(() => {
  localStorage.clear()
  setActivePinia(createPinia())
})

afterEach(() => flushPromises())

describe('request.js 响应拦截器 - 错误信封解析', () => {
  it('把 401 + AUTH_REQUIRED envelope 的 code 挂到 error 上', async () => {
    // 通过替换 request 内部的 axios adapter 拦截 _request 调用。
    const inner = request.defaults
    const originalAdapter = inner.adapter
    inner.adapter = () => Promise.reject({
      message: 'Network Error',
      response: {
        status: 401,
        data: { code: 'AUTH_REQUIRED', error: '请先登录' },
      },
    })

    let caught = null
    try { await request.get('/test') } catch (e) { caught = e }
    inner.adapter = originalAdapter

    expect(caught).toBeTruthy()
    expect(caught.code).toBe('AUTH_REQUIRED')
    expect(caught.message).toBe('请先登录')
    expect(caught.backend).toMatchObject({ code: 'AUTH_REQUIRED' })
  })

  it('把 404 + HTTP_NOT_FOUND envelope 的 code 挂到 error 上', async () => {
    const inner = request.defaults
    const originalAdapter = inner.adapter
    inner.adapter = () => Promise.reject({
      message: 'Request failed',
      response: { status: 404, data: { code: 'HTTP_NOT_FOUND', detail: '资源不存在' } },
    })

    let caught = null
    try { await request.get('/x') } catch (e) { caught = e }
    inner.adapter = originalAdapter

    expect(caught.code).toBe('HTTP_NOT_FOUND')
    expect(caught.message).toBe('资源不存在')
  })

  it('成功响应直接透传 data 字段', async () => {
    const inner = request.defaults
    const originalAdapter = inner.adapter
    inner.adapter = (config) => Promise.resolve({
      status: 200,
      data: { items: [1, 2, 3] },
      headers: {},
      config,
      statusText: 'OK',
    })

    const result = await request.get('/list')
    inner.adapter = originalAdapter

    expect(result.items).toEqual([1, 2, 3])
  })

  it('未带 code 字段的旧 envelope 也能 fallback 到 message', async () => {
    const inner = request.defaults
    const originalAdapter = inner.adapter
    inner.adapter = () => Promise.reject({
      message: 'Network Error',
      response: { status: 500, data: { error: '服务端错误' } },
    })

    let caught = null
    try { await request.get('/y') } catch (e) { caught = e }
    inner.adapter = originalAdapter

    expect(caught.code).toBeUndefined()
    expect(caught.message).toBe('服务端错误')
  })

  it('5xx 错误信封同样挂载 code', async () => {
    const inner = request.defaults
    const originalAdapter = inner.adapter
    inner.adapter = () => Promise.reject({
      message: 'Network Error',
      response: { status: 502, data: { code: 'EXTERNAL_SERVICE_ERROR', error: 'LLM 配置缺失' } },
    })

    let caught = null
    try { await request.get('/z') } catch (e) { caught = e }
    inner.adapter = originalAdapter

    expect(caught.code).toBe('EXTERNAL_SERVICE_ERROR')
    expect(caught.message).toBe('LLM 配置缺失')
  })
})
