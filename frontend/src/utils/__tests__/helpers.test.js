/**
 * 工具函数单元测试
 * 测试常用工具函数
 */
import { describe, it, expect } from 'vitest'
import { generateUniqueUsername } from '../../../e2e/fixtures/index.js'

describe('generateUniqueUsername', () => {
  it('生成带前缀的唯一用户名', () => {
    const username = generateUniqueUsername('testuser')
    expect(username).toMatch(/^testuser_/)
  })

  it('每次调用生成不同的用户名', () => {
    const username1 = generateUniqueUsername()
    const username2 = generateUniqueUsername()
    expect(username1).not.toBe(username2)
  })

  it('默认前缀为 user', () => {
    const username = generateUniqueUsername()
    expect(username).toMatch(/^user_/)
  })
})
