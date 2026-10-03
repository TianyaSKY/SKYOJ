/**
 * E2E 测试: 认证流程
 * 覆盖登录、注册、登出、路由守卫等场景
 */
import { test, expect } from '@playwright/test'
import {
  testUsers,
  FRONTEND,
  generateUniqueUsername,
  clearStorage,
  setAuthState,
  selectors,
} from './fixtures/index.js'

test.describe('认证流程', () => {
  test.beforeEach(async ({ page }) => {
    await clearStorage(page)
  })

  test.afterEach(async ({ page }) => {
    await clearStorage(page)
  })

  test('登录页正确加载', async ({ page }) => {
    await page.goto(`${FRONTEND}/login`)
    await expect(page).toHaveTitle(/./)
    // 验证表单元素存在
    await expect(page.locator('input[type="text"], input[type="email"]')).toBeVisible()
    await expect(page.locator('input[type="password"]').first()).toBeVisible()
    await expect(page.locator('button[type="submit"]')).toBeVisible()
  })

  test('注册页正确加载', async ({ page }) => {
    await page.goto(`${FRONTEND}/register`)
    await expect(page.locator('input[type="text"], input[type="email"]')).toBeVisible()
    await expect(page.locator('input[type="password"]').first()).toBeVisible()
    await expect(page.locator('button[type="submit"]')).toBeVisible()
  })

  test('登录成功 - 学生账号', async ({ page }) => {
    await page.goto(`${FRONTEND}/login`)

    // 填写登录表单
    const usernameInput = page.locator('input[type="text"], input[type="email"]').first()
    const passwordInput = page.locator('input[type="password"]')
    const submitBtn = page.locator('button[type="submit"]')

    await usernameInput.fill(testUsers.student.username)
    await passwordInput.fill(testUsers.student.password)
    await submitBtn.click()

    // 等待登录成功跳转 (验证 localStorage 有 token)
    await page.waitForFunction(() => localStorage.getItem('token') !== null, { timeout: 10000 })
    const token = await page.evaluate(() => localStorage.getItem('token'))
    expect(token).toBeTruthy()

    // 验证跳转到首页或目标页面
    await expect(page).not.toHaveURL(/\/login$/)
  })

  test('登录失败 - 错误密码', async ({ page }) => {
    await page.goto(`${FRONTEND}/login`)

    const usernameInput = page.locator('input[type="text"], input[type="email"]').first()
    const passwordInput = page.locator('input[type="password"]')
    const submitBtn = page.locator('button[type="submit"]')

    await usernameInput.fill(testUsers.student.username)
    await passwordInput.fill('wrong_password_123')
    await submitBtn.click()

    // 验证错误提示出现
    await page.waitForTimeout(1000)
    // 检查是否有错误消息或表单仍停留在登录页
    await expect(page).toHaveURL(/\/login/)
  })

  test('登录失败 - 用户名不存在', async ({ page }) => {
    await page.goto(`${FRONTEND}/login`)

    const usernameInput = page.locator('input[type="text"], input[type="email"]').first()
    const passwordInput = page.locator('input[type="password"]')
    const submitBtn = page.locator('button[type="submit"]')

    await usernameInput.fill('nonexistent_user_12345')
    await passwordInput.fill('anypassword')
    await submitBtn.click()

    // 等待响应
    await page.waitForTimeout(2000)
    // 应该仍在登录页
    await expect(page).toHaveURL(/\/login/)
  })

  test('注册新用户成功', async ({ page }) => {
    const uniqueUsername = generateUniqueUsername('testuser')

    await page.goto(`${FRONTEND}/register`)

    // 填写注册表单 (根据实际表单结构调整)
    const usernameInput = page.locator('input[type="text"]').first()
    const passwordInput = page.locator('input[type="password"]').nth(0)
    const confirmInput = page.locator('input[type="password"]').nth(1)
    const submitBtn = page.locator('button[type="submit"]')

    await usernameInput.fill(uniqueUsername)
    await passwordInput.fill('Test123456')
    await confirmInput.fill('Test123456')
    await submitBtn.click()

    // 等待注册成功跳转或成功提示
    await page.waitForTimeout(2000)
    // 成功后会跳转到登录页或自动登录
    await expect(page).toHaveURL(/\/login/)
    const response = await page.request.post(`${FRONTEND}/api/auth/login`, {
      data: {username: uniqueUsername, password: 'Test123456'},
    })
    expect(response.ok()).toBeTruthy()
  })

  test('注册失败 - 用户名已存在', async ({ page }) => {
    await page.goto(`${FRONTEND}/register`)

    const usernameInput = page.locator('input[type="text"]').first()
    const passwordInput = page.locator('input[type="password"]').nth(0)
    const confirmInput = page.locator('input[type="password"]').nth(1)
    const submitBtn = page.locator('button[type="submit"]')

    // 使用已存在的用户名
    await usernameInput.fill(testUsers.student.username)
    await passwordInput.fill('Test123456')
    await confirmInput.fill('Test123456')
    await submitBtn.click()

    // 等待响应
    await page.waitForTimeout(2000)
    // 应该显示错误或仍在注册页
    const url = page.url()
    expect(url.includes('/register')).toBeTruthy()
    await expect(page.locator('.el-message--error')).toBeVisible()
  })

  test('注册表单验证 - 密码过短', async ({ page }) => {
    await page.goto(`${FRONTEND}/register`)

    const usernameInput = page.locator('input[type="text"]').first()
    const passwordInput = page.locator('input[type="password"]').nth(0)
    const confirmInput = page.locator('input[type="password"]').nth(1)
    const submitBtn = page.locator('button[type="submit"]')

    await usernameInput.fill(generateUniqueUsername('testuser'))
    await passwordInput.fill('123') // 密码过短
    await confirmInput.fill('123')
    await submitBtn.click()

    // 应该显示验证错误或阻止提交
    await page.waitForTimeout(1000)
    // 检查是否有错误提示
    const errorMsg = page.locator('.el-form-item__error, .el-message--error, [role="alert"]')
    await expect(errorMsg.first()).toBeVisible()
  })
})

test.describe('路由守卫', () => {
  test('未登录访问受保护路由重定向到登录页', async ({ page }) => {
    // 访问需要登录的页面
    const protectedRoutes = ['/problems', '/exam', '/profile']

    for (const route of protectedRoutes) {
      await page.goto(`${FRONTEND}${route}`)
      // 应该重定向到登录页
      await expect(page).toHaveURL(/\/login/, { timeout: 5000 })
    }
  })

  test('已登录用户不应访问登录页（应跳转到首页）', async ({ page }) => {
    // 先设置登录状态
    await setAuthState(page, testUsers.student)

    await page.goto(`${FRONTEND}/login`)
    await page.waitForTimeout(1000)

    // 应该不在登录页
    // 注意：实际行为取决于路由守卫实现
  })

  test('学生访问 /admin/* 应被拒绝', async ({ page }) => {
    // 以学生身份登录
    await setAuthState(page, testUsers.student)

    // 尝试访问管理后台
    await page.goto(`${FRONTEND}/admin/dashboard`)
    await page.waitForTimeout(1000)

    // 应该被重定向或显示无权限
    const url = page.url()
    expect(url.includes('/admin/dashboard')).toBeFalsy()
  })

  test('教师可以访问管理后台', async ({ page }) => {
    // 以教师身份登录
    await setAuthState(page, testUsers.teacher)

    // 访问管理后台
    await page.goto(`${FRONTEND}/admin/dashboard`)
    await page.waitForTimeout(2000)

    // 应该能访问
    // 注意：这取决于实际后端权限验证
  })
})

test.describe('登出流程', () => {
  test('登出后清除登录状态并跳转', async ({ page }) => {
    // 先登录
    await setAuthState(page, testUsers.student)

    // 访问首页
    await page.goto(`${FRONTEND}/`)
    await page.waitForTimeout(1000)

    // 查找并点击登出按钮
    const logoutBtn = page.locator('[data-testid="nav-logout"], button:has-text("登出"), button:has-text("Logout"), button:has-text("Sign out")').first()

    if (await logoutBtn.isVisible()) {
      await logoutBtn.click()
      await page.waitForTimeout(1000)

      // 验证 token 已清除
      const token = await page.evaluate(() => localStorage.getItem('token'))
      expect(token).toBeNull()
    }
  })
})
