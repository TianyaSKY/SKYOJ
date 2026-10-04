import { describe, expect, it } from 'vitest'
import { backendErrorMessage, errorMessage } from '../error'

describe('未知异常的用户提示', () => {
  it('只采用非空字符串 message', () => {
    expect(errorMessage(new Error('网络错误'), '重试')).toBe('网络错误')
    expect(errorMessage({ message: '服务不可用' }, '重试')).toBe('服务不可用')
  })
  it.each([null, undefined, 'failure', 42, [], {}, { message: '' }, { message: 404 }])(
    '异常值 %j 使用默认消息',
    (value) => {
      expect(errorMessage(value, '请重试')).toBe('请重试')
    },
  )
  it('后端 message 优先，兼容 error 字段', () => {
    expect(
      backendErrorMessage({ response: { data: { message: '密码错误', error: '旧格式' } } }, '重试'),
    ).toBe('密码错误')
    expect(backendErrorMessage({ response: { data: { error: '访问被拒绝' } } }, '重试')).toBe(
      '访问被拒绝',
    )
  })
  it.each([
    null,
    'error',
    { response: null },
    { response: { data: '失败' } },
    { response: { data: [] } },
    { response: { data: { message: 500 } } },
  ])('不可信后端报文 %j 不直接展示', (value) => {
    expect(backendErrorMessage(value, '请求失败')).toBe('请求失败')
  })
})
