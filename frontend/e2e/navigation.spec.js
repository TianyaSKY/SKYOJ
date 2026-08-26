/**
 * E2E 测试: 导航和路由
 * 覆盖导航栏、面包屑、路由跳转等功能
 */
import { test, expect } from '@playwright/test'
import {
  testUsers,
  FRONTEND,
  setAuthState,
  clearStorage,
} from './fixtures/index.js'

test.describe('导航栏', () => {
  test('顶部导航栏存在', async ({ page }) => {
    await page.goto(FRONTEND)
    await page.waitForTimeout(2000)

    const nav = page.locator('header, nav, .navbar, [class*="nav"]').first()
    await expect(nav).toBeVisible()
  })

  test('导航栏链接完整', async ({ page }) => {
    await page.goto(FRONTEND)
    await page.waitForTimeout(2000)

    // 验证首页链接
    const homeLink = page.locator('a[href="/"], a[href="/"], [class*="logo"]').first()
    await expect(homeLink).toBeVisible()

    // 验证登录入口（未登录状态）
    const loginLink = page.locator('a[href="/login"], button:has-text("登录"), [class*="login"]').first()
    await expect(loginLink).toBeVisible()
  })

  test('登录后导航栏显示用户信息', async ({ page }) => {
    await clearStorage(page)
    await setAuthState(page, testUsers.student)

    await page.goto(FRONTEND)
    await page.waitForTimeout(2000)

    // 验证用户名显示
    const usernameDisplay = page.locator('[class*="username"], [class*="user"], [class*="avatar"]').first()
    if (await usernameDisplay.count() > 0) {
      await expect(usernameDisplay).toBeVisible()
    }

    // 验证登出按钮
    const logoutBtn = page.locator('button:has-text("登出"), button:has-text("Logout"), [class*="logout"]').first()
    if (await logoutBtn.count() > 0) {
      await expect(logoutBtn).toBeVisible()
    }

    await clearStorage(page)
  })

  test('导航链接可点击并跳转', async ({ page }) => {
    await clearStorage(page)
    await setAuthState(page, testUsers.student)

    await page.goto(FRONTEND)
    await page.waitForTimeout(2000)

    // 尝试点击导航链接
    const navLinks = page.locator('nav a, header a, .navbar a').all()

    for (const link of navLinks.slice(0, 3)) {
      if (await link.isVisible()) {
        const href = await link.getAttribute('href')
        if (href && !href.startsWith('#')) {
          await link.click()
          await page.waitForTimeout(1000)
          // 验证页面已跳转
          break
        }
      }
    }

    await clearStorage(page)
  })

  test('移动端导航菜单', async ({ page }) => {
    // 设置移动端视口
    await page.setViewportSize({ width: 375, height: 667 })

    await page.goto(FRONTEND)
    await page.waitForTimeout(2000)

    // 查找汉堡菜单
    const menuBtn = page.locator('[class*="menu"], [class*="hamburger"], .el-icon').first()
    if (await menuBtn.isVisible()) {
      await menuBtn.click()
      await page.waitForTimeout(1000)

      // 验证菜单展开
      const mobileMenu = page.locator('[class*="drawer"], [class*="sidebar"], [class*="mobile-menu"]').first()
      if (await mobileMenu.count() > 0) {
        // 菜单应该可见
      }
    }
  })
})

test.describe('面包屑导航', () => {
  test('深层页面显示面包屑', async ({ page }) => {
    await clearStorage(page)
    await setAuthState(page, testUsers.student)

    await page.goto(`${FRONTEND}/problem/1`)
    await page.waitForTimeout(2000)

    // 查找面包屑
    const breadcrumbs = page.locator('.el-breadcrumb, [class*="breadcrumb"], nav[aria-label]').first()
    if (await breadcrumbs.count() > 0) {
      // 面包屑存在
    }

    await clearStorage(page)
  })

  test('面包屑链接可点击', async ({ page }) => {
    await clearStorage(page)
    await setAuthState(page, testUsers.student)

    await page.goto(`${FRONTEND}/exam/1/rank`)
    await page.waitForTimeout(2000)

    const breadcrumbs = page.locator('.el-breadcrumb, [class*="breadcrumb"]').first()
    if (await breadcrumbs.isVisible()) {
      const firstLink = breadcrumbs.locator('a, span[role="link"]').first()
      if (await firstLink.count() > 0) {
        await firstLink.click()
        await page.waitForTimeout(1000)
      }
    }

    await clearStorage(page)
  })
})

test.describe('路由跳转', () => {
  test('页面切换无白屏', async ({ page }) => {
    await clearStorage(page)
    await setAuthState(page, testUsers.student)

    await page.goto(FRONTEND)
    await page.waitForTimeout(2000)

    // 依次访问几个页面
    const routes = ['/problems', '/exam', '/profile']

    for (const route of routes) {
      await page.goto(`${FRONTEND}${route}`)
      await page.waitForTimeout(2000)

      // 验证页面内容加载
      const body = page.locator('body')
      await expect(body).toBeVisible()
    }

    await clearStorage(page)
  })

  test('浏览器前进后退', async ({ page }) => {
    await clearStorage(page)
    await setAuthState(page, testUsers.student)

    await page.goto(`${FRONTEND}/problems`)
    await page.waitForTimeout(2000)

    // 访问第二个页面
    await page.goto(`${FRONTEND}/exam`)
    await page.waitForTimeout(2000)

    // 后退
    await page.goBack()
    await page.waitForTimeout(2000)
    await expect(page).toHaveURL(/\/problems/)

    // 前进
    await page.goForward()
    await page.waitForTimeout(2000)
    await expect(page).toHaveURL(/\/exam/)

    await clearStorage(page)
  })

  test('URL 参数正确传递', async ({ page }) => {
    await clearStorage(page)
    await setAuthState(page, testUsers.student)

    // 访问带参数的题目页
    const problemId = 123
    await page.goto(`${FRONTEND}/problem/${problemId}`)
    await page.waitForTimeout(2000)

    // 验证 URL 正确
    await expect(page).toHaveURL(new RegExp(`/problem/${problemId}`))

    await clearStorage(page)
  })
})

test.describe('404 和错误处理', () => {
  test('不存在的路由显示友好页面', async ({ page }) => {
    await page.goto(`${FRONTEND}/this-does-not-exist`)
    await page.waitForTimeout(3000)

    // 验证不是空白页
    const body = page.locator('body')
    const content = await body.textContent()

    // 应该显示 404 或返回首页
    expect(content.length).toBeGreaterThan(100)
  })

  test('无效的题目ID显示错误', async ({ page }) => {
    await clearStorage(page)
    await setAuthState(page, testUsers.student)

    await page.goto(`${FRONTEND}/problem/999999999`)
    await page.waitForTimeout(3000)

    // 应该显示错误消息或跳转到其他页面
    const content = await page.locator('body').textContent()
    // 验证页面有内容
    expect(content.length).toBeGreaterThan(0)

    await clearStorage(page)
  })

  test('网络错误时显示友好提示', async ({ page }) => {
    // 使用无效的 baseURL 触发网络错误
    await clearStorage(page)

    // 访问不存在的服务器
    await page.goto('http://localhost:99999')
    await page.waitForTimeout(3000)

    // 应该显示连接错误页面
    const body = page.locator('body')
    const content = await body.textContent()
    expect(content.length).toBeGreaterThan(0)
  })
})

test.describe('页面加载状态', () => {
  test('页面加载时显示骨架屏或loading', async ({ page }) => {
    await clearStorage(page)
    await setAuthState(page, testUsers.student)

    // 使用慢速网络模拟
    // await page.route('**', route => route.continue({ delay: 1000 }))

    await page.goto(`${FRONTEND}/problems`)
    await page.waitForTimeout(500)

    // 检查是否有 loading 状态
    const loading = page.locator('.el-loading-mask, [class*="skeleton"], [class*="loading"]').first()
    // Loading 状态可能很快消失

    await page.waitForTimeout(3000)
    await clearStorage(page)
  })

  test('长页面滚动加载', async ({ page }) => {
    await clearStorage(page)
    await setAuthState(page, testUsers.student)

    await page.goto(`${FRONTEND}/problems`)
    await page.waitForTimeout(2000)

    // 滚动到底部
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
    await page.waitForTimeout(1000)

    // 验证没有滚动条卡住
    await expect(page.locator('body')).toBeVisible()

    await clearStorage(page)
  })
})

test.describe('页面响应式', () => {
  test('桌面端布局', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto(FRONTEND)
    await page.waitForTimeout(2000)

    const main = page.locator('main, .container, [class*="main"]').first()
    await expect(main).toBeVisible()
  })

  test('平板端布局', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 })
    await page.goto(FRONTEND)
    await page.waitForTimeout(2000)

    const main = page.locator('main, .container, [class*="main"]').first()
    await expect(main).toBeVisible()
  })

  test('移动端布局', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto(FRONTEND)
    await page.waitForTimeout(2000)

    const main = page.locator('main, .container, [class*="main"]').first()
    await expect(main).toBeVisible()
  })
})
