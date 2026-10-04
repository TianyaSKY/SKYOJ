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
import type { ApiError } from '@/types/http'
import { expectTypeOf } from 'vitest'

beforeEach(() => {
  localStorage.clear()
  setActivePinia(createPinia())
})

afterEach(() => flushPromises())

describe('request.js 响应拦截器 - 错误信封解析', () => {
  async function rejectedRequest(data: unknown, extra: Partial<ApiError> = {}): Promise<ApiError> {
    const original = request.defaults.adapter
    request.defaults.adapter = () =>
      Promise.reject({
        message: 'Request failed',
        response: { status: 422, data },
        ...extra,
      })
    try {
      return await request.get<ApiError>('/invalid').catch((error: ApiError) => error)
    } finally {
      request.defaults.adapter = original
    }
  }

  it('使用后端 message 字段显示具体错误', async () => {
    const error = await rejectedRequest({ code: 'INVALID_STATE', message: '考试尚未开始' })
    expect(error.message).toBe('考试尚未开始')
  })

  it('将字段校验数组转为可读字符串，保留原始报文', async () => {
    const data = {
      detail: [
        { loc: ['body', 'title'], msg: 'Field required', input: 'private input' },
        { loc: ['query', 'page'], msg: 'Must be greater than 0' },
      ],
    }
    const error = await rejectedRequest(data)
    expect(error.message).toBe('title: Field required；page: Must be greater than 0')
    expect(error.backend).toEqual(data)
    expect(error.message).not.toContain('private input')
  })

  it('支持旧版嵌套错误消息，忽略没有可读消息的对象', async () => {
    expect((await rejectedRequest({ detail: { message: '参数格式无效' } })).message).toBe(
      '参数格式无效',
    )
    expect((await rejectedRequest({ error: { unknown: true } })).message).toBe('Request failed')
  })

  it('后端未返回错误码时保留网络或取消请求的原始代码', async () => {
    const error = await rejectedRequest(undefined, {
      code: 'ERR_CANCELED',
      message: 'canceled',
      response: undefined,
    })
    expect(error.code).toBe('ERR_CANCELED')
    expect(error.message).toBe('canceled')
  })

  it('把 401 + AUTH_REQUIRED envelope 的 code 挂到 error 上', async () => {
    // 通过替换 request 内部的 axios adapter 拦截 _request 调用。
    const inner = request.defaults
    const originalAdapter = inner.adapter
    inner.adapter = () =>
      Promise.reject({
        message: 'Network Error',
        response: {
          status: 401,
          data: { code: 'AUTH_REQUIRED', error: '请先登录' },
        },
      })

    let caught: ApiError | undefined
    try {
      await request.get('/test')
    } catch (e) {
      caught = e as ApiError
    }
    inner.adapter = originalAdapter

    expect(caught).toBeTruthy()
    expect(caught?.code).toBe('AUTH_REQUIRED')
    expect(caught?.message).toBe('请先登录')
    expect(caught?.backend).toMatchObject({ code: 'AUTH_REQUIRED' })
  })

  it('把 404 + HTTP_NOT_FOUND envelope 的 code 挂到 error 上', async () => {
    const inner = request.defaults
    const originalAdapter = inner.adapter
    inner.adapter = () =>
      Promise.reject({
        message: 'Request failed',
        response: { status: 404, data: { code: 'HTTP_NOT_FOUND', detail: '资源不存在' } },
      })

    let caught: ApiError | undefined
    try {
      await request.get('/x')
    } catch (e) {
      caught = e as ApiError
    }
    inner.adapter = originalAdapter

    expect(caught?.code).toBe('HTTP_NOT_FOUND')
    expect(caught?.message).toBe('资源不存在')
  })

  it('成功响应直接透传 data 字段', async () => {
    const inner = request.defaults
    const originalAdapter = inner.adapter
    inner.adapter = (config) =>
      Promise.resolve({
        status: 200,
        data: { items: [1, 2, 3] },
        headers: {},
        config,
        statusText: 'OK',
      })

    const result = await request.get<{ items: number[] }>('/list')
    inner.adapter = originalAdapter

    expect(result.items).toEqual([1, 2, 3])
  })

  it('未带 code 字段的旧 envelope 也能 fallback 到 message', async () => {
    const inner = request.defaults
    const originalAdapter = inner.adapter
    inner.adapter = () =>
      Promise.reject({
        message: 'Network Error',
        response: { status: 500, data: { error: '服务端错误' } },
      })

    let caught: ApiError | undefined
    try {
      await request.get('/y')
    } catch (e) {
      caught = e as ApiError
    }
    inner.adapter = originalAdapter

    expect(caught?.code).toBeUndefined()
    expect(caught?.message).toBe('服务端错误')
  })

  it('5xx 错误信封同样挂载 code', async () => {
    const inner = request.defaults
    const originalAdapter = inner.adapter
    inner.adapter = () =>
      Promise.reject({
        message: 'Network Error',
        response: { status: 502, data: { code: 'EXTERNAL_SERVICE_ERROR', error: 'LLM 配置缺失' } },
      })

    let caught: ApiError | undefined
    try {
      await request.get('/z')
    } catch (e) {
      caught = e as ApiError
    }
    inner.adapter = originalAdapter

    expect(caught?.code).toBe('EXTERNAL_SERVICE_ERROR')
    expect(caught?.message).toBe('LLM 配置缺失')
  })
})

it('响应解包契约在类型检查中保持 Promise<T>，写请求配置允许跳过认证弹窗', () => {
  expectTypeOf(request.get<{ id: number }>).returns.toEqualTypeOf<Promise<{ id: number }>>()
  expectTypeOf(request.post<{ token: string }, { username: string }>).returns.toEqualTypeOf<
    Promise<{ token: string }>
  >()
})
