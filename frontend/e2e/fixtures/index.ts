import type { Page } from '@playwright/test'
import { z } from 'zod'
import { cachedUserSchema } from '../../src/schemas/user'

export interface TestUser { username: string; password: string; role: string; email: string }
const loginResponseSchema = z.object({ token: z.string().min(1), user: cachedUserSchema })
/**
 * Playwright 测试 Fixtures
 * 定义测试用户和共享测试数据
 */

const FRONTEND = process.env.E2E_BASE_URL || 'http://localhost:80'

/**
 * 测试用户账号
 * 注意：实际测试时需要确保这些账号存在于后端数据库中
 */
export const testUsers: Record<'student' | 'teacher' | 'admin', TestUser> = {
  student: {
    username: 'test_student',
    password: 'Test123456',
    role: 'student',
    email: 'student@test.com',
  },
  teacher: {
    username: 'test_teacher',
    password: 'Test123456',
    role: 'teacher',
    email: 'teacher@test.com',
  },
  admin: {
    username: 'test_admin',
    password: 'Test123456',
    role: 'admin',
    email: 'admin@test.com',
  },
}

/**
 * 测试题目数据
 */
export const testProblems = [
  {
    id: 1000,
    title: 'A+B Problem',
    difficulty: 'Easy',
    tags: ['入门', '基础'],
  },
  {
    id: 1001,
    title: 'Prime Number',
    difficulty: 'Medium',
    tags: ['数学', '数论'],
  },
  {
    id: 1002,
    title: 'Binary Search',
    difficulty: 'Medium',
    tags: ['算法', '二分'],
  },
]

/**
 * 测试竞赛数据
 */
export const testExams = [
  {
    id: 1,
    title: 'Weekly Contest 1',
    startTime: '2026-08-01T10:00:00Z',
    endTime: '2026-08-01T14:00:00Z',
    password: 'contest123',
  },
  {
    id: 2,
    title: 'Mid-term Exam',
    startTime: '2026-09-01T09:00:00Z',
    endTime: '2026-09-01T12:00:00Z',
    password: 'exam456',
  },
]

/**
 * 常用选择器
 */
export const selectors = {
  // 导航
  navLogin: '[data-testid="nav-login"]',
  navRegister: '[data-testid="nav-register"]',
  navLogout: '[data-testid="nav-logout"]',
  navUsername: '[data-testid="nav-username"]',

  // 表单
  usernameInput: 'input[type="text"]',
  passwordInput: 'input[type="password"]',
  submitButton: 'button[type="submit"]',

  // 通用
  loadingSpinner: '.el-loading-spinner',
  errorMessage: '.el-message--error',
  successMessage: '.el-message--success',
}

/**
 * 生成唯一测试用户名
 * @param {string} prefix - 前缀
 * @returns {string} 唯一的用户名
 */
export function generateUniqueUsername(prefix = 'user') {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).substring(7)}`
}

/**
 * 等待元素加载
 * @param {import('@playwright/test').Page} page
 * @param {string} selector - CSS 选择器
 * @param {number} timeout - 超时时间(ms)
 */
export async function waitForElement(page: Page, selector: string, timeout = 10000) {
  await page.waitForSelector(selector, { state: 'visible', timeout })
}

/**
 * 清除 localStorage
 * @param {import('@playwright/test').Page} page
 */
export async function clearStorage(page: Page) {
  // 新建页面为 about:blank，必须先进入应用来源才能访问存储。
  if (!page.url().startsWith(FRONTEND)) await page.goto(FRONTEND)
  await page.evaluate(() => localStorage.clear())
}

/**
 * 设置登录状态
 * @param {import('@playwright/test').Page} page
 * @param {object} user - 用户信息
 */
export async function setAuthState(page: Page, user: Pick<TestUser, 'username' | 'password'>) {
  const response = await page.request.post(`${FRONTEND}/api/auth/login`, {
    data: {username: user.username, password: user.password},
  })
  if (!response.ok()) throw new Error(`测试用户登录失败：${response.status()} ${await response.text()}`)
  const raw: unknown = await response.json()
  const auth = loginResponseSchema.parse(raw)
  if (!page.url().startsWith(FRONTEND)) await page.goto(FRONTEND)
  await page.evaluate(
    ({token, user}) => {
      localStorage.setItem('token', token)
      localStorage.setItem('user', JSON.stringify(user))
    },
    auth
  )
}

export { FRONTEND }
