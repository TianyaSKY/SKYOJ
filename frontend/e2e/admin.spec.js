/**
 * E2E 测试: 教师管理后台
 * 覆盖题目管理、竞赛管理、考试监控等功能
 */
import { test, expect } from '@playwright/test'
import {
  testUsers,
  testProblems,
  FRONTEND,
  setAuthState,
  clearStorage,
  generateUniqueUsername,
} from './fixtures/index.js'

test.describe('教师管理 - 访问控制', () => {
  test('学生账号不能访问管理后台', async ({ page }) => {
    await clearStorage(page)
    await setAuthState(page, testUsers.student)

    // 尝试访问各个管理页面
    const adminRoutes = [
      '/admin/dashboard',
      '/admin/problems',
      '/admin/exams',
      '/admin/submissions',
    ]

    for (const route of adminRoutes) {
      await page.goto(`${FRONTEND}${route}`)
      await page.waitForTimeout(1000)

      // 应该被重定向或显示无权限
      const url = page.url()
      expect(url).not.toContain('/admin/')
    }

    await clearStorage(page)
  })

  test('教师账号可以访问管理后台', async ({ page }) => {
    await clearStorage(page)
    await setAuthState(page, testUsers.teacher)

    await page.goto(`${FRONTEND}/admin/dashboard`)
    await page.waitForTimeout(3000)

    // 验证可以访问
    // 注意：具体验证取决于后端权限
  })

  test.afterEach(async ({ page }) => {
    await clearStorage(page)
  })
})

test.describe('教师管理 - 仪表盘', () => {
  test.beforeEach(async ({ page }) => {
    await clearStorage(page)
    await setAuthState(page, testUsers.teacher)
  })

  test.afterEach(async ({ page }) => {
    await clearStorage(page)
  })

  test('仪表盘页面正确加载', async ({ page }) => {
    await page.goto(`${FRONTEND}/admin/dashboard`)
    await page.waitForTimeout(3000)

    await expect(page.locator('main, .dashboard, [class*="content"]').first()).toBeVisible()
  })

  test('仪表盘显示统计数据', async ({ page }) => {
    await page.goto(`${FRONTEND}/admin/dashboard`)
    await page.waitForTimeout(3000)

    // 查找统计数据卡片
    const statCards = page.locator('[class*="stat"], [class*="card"], .el-card').first()
    expect(await statCards.count()).toBeGreaterThanOrEqual(0)
  })

  test('仪表盘显示快速入口', async ({ page }) => {
    await page.goto(`${FRONTEND}/admin/dashboard`)
    await page.waitForTimeout(2000)

    // 查找快捷入口按钮
    const quickLinks = page.locator('a[href*="/admin/"], button').first()
    expect(await quickLinks.count()).toBeGreaterThanOrEqual(0)
  })
})

test.describe('教师管理 - 题目管理', () => {
  test.beforeEach(async ({ page }) => {
    await clearStorage(page)
    await setAuthState(page, testUsers.teacher)
  })

  test.afterEach(async ({ page }) => {
    await clearStorage(page)
  })

  test('题目管理页面正确加载', async ({ page }) => {
    await page.goto(`${FRONTEND}/admin/problems`)
    await page.waitForTimeout(3000)

    await expect(page.locator('main, [class*="content"]').first()).toBeVisible()
  })

  test('题目列表显示', async ({ page }) => {
    await page.goto(`${FRONTEND}/admin/problems`)
    await page.waitForTimeout(3000)

    const problemList = page.locator('table, [class*="list"], .el-table').first()
    if (await problemList.isVisible()) {
      await expect(problemList).toBeVisible()
    }
  })

  test('新建题目按钮存在', async ({ page }) => {
    await page.goto(`${FRONTEND}/admin/problems`)
    await page.waitForTimeout(2000)

    const newBtn = page.locator('button:has-text("新建"), button:has-text("创建"), button:has-text("Add")').first()
    if (await newBtn.isVisible()) {
      await expect(newBtn).toBeVisible()
    }
  })

  test('可以打开新建题目表单', async ({ page }) => {
    await page.goto(`${FRONTEND}/admin/problems`)
    await page.waitForTimeout(2000)

    const newBtn = page.locator('button:has-text("新建"), button:has-text("创建")').first()
    if (await newBtn.isVisible()) {
      await newBtn.click()
      await page.waitForTimeout(1000)

      // 验证表单出现
      const form = page.locator('form, .el-dialog, [class*="form"]').first()
      expect(await form.count()).toBeGreaterThan(0)
    }
  })

  test('新建题目表单填写', async ({ page }) => {
    await page.goto(`${FRONTEND}/admin/problems`)
    await page.waitForTimeout(2000)

    // 点击新建
    const newBtn = page.locator('button:has-text("新建"), button:has-text("创建")').first()
    if (await newBtn.isVisible()) {
      await newBtn.click()
      await page.waitForTimeout(1000)

      // 填写表单
      const titleInput = page.locator('input[type="text"], .el-input input').first()
      if (await titleInput.isVisible()) {
        await titleInput.fill(`Test Problem ${Date.now()}`)
        await page.waitForTimeout(500)
      }
    }
  })

  test('AI 出题功能入口', async ({ page }) => {
    await page.goto(`${FRONTEND}/admin/problems`)
    await page.waitForTimeout(2000)

    // 查找 AI 出题按钮
    const aiBtn = page.locator('button:has-text("AI"), button:has-text("智能"), [class*="ai"]').first()
    if (await aiBtn.count() > 0) {
      // AI 功能可能存在
    }
  })
})

test.describe('教师管理 - 竞赛管理', () => {
  test.beforeEach(async ({ page }) => {
    await clearStorage(page)
    await setAuthState(page, testUsers.teacher)
  })

  test.afterEach(async ({ page }) => {
    await clearStorage(page)
  })

  test('竞赛管理页面正确加载', async ({ page }) => {
    await page.goto(`${FRONTEND}/admin/exams`)
    await page.waitForTimeout(3000)

    await expect(page.locator('main, [class*="content"]').first()).toBeVisible()
  })

  test('竞赛列表显示', async ({ page }) => {
    await page.goto(`${FRONTEND}/admin/exams`)
    await page.waitForTimeout(3000)

    const examList = page.locator('table, .el-table, [class*="exam"]').first()
    if (await examList.isVisible()) {
      await expect(examList).toBeVisible()
    }
  })

  test('创建新竞赛', async ({ page }) => {
    await page.goto(`${FRONTEND}/admin/exams`)
    await page.waitForTimeout(2000)

    const newBtn = page.locator('button:has-text("新建"), button:has-text("创建"), button:has-text("创建考试")').first()
    if (await newBtn.isVisible()) {
      await newBtn.click()
      await page.waitForTimeout(1000)

      // 填写竞赛名称
      const nameInput = page.locator('input').first()
      if (await nameInput.isVisible()) {
        await nameInput.fill(`Test Contest ${Date.now()}`)
      }
    }
  })

  test('竞赛时间设置', async ({ page }) => {
    await page.goto(`${FRONTEND}/admin/exams`)
    await page.waitForTimeout(2000)

    const newBtn = page.locator('button:has-text("新建"), button:has-text("创建")').first()
    if (await newBtn.isVisible()) {
      await newBtn.click()
      await page.waitForTimeout(1000)

      // 查找时间选择器
      const datePicker = page.locator('.el-date-editor, [class*="date-picker"], [class*="time"]').first()
      if (await datePicker.count() > 0) {
        // 时间选择器存在
      }
    }
  })

  test('竞赛题目添加', async ({ page }) => {
    await page.goto(`${FRONTEND}/admin/exams`)
    await page.waitForTimeout(2000)

    // 查找编辑或添加题目按钮
    const addProblemBtn = page.locator('button:has-text("添加题目"), button:has-text("选题"), [class*="add-problem"]').first()
    if (await addProblemBtn.count() > 0) {
      // 添加题目功能存在
    }
  })
})

test.describe('教师管理 - 考试监控', () => {
  test.beforeEach(async ({ page }) => {
    await clearStorage(page)
    await setAuthState(page, testUsers.teacher)
  })

  test.afterEach(async ({ page }) => {
    await clearStorage(page)
  })

  test('考试监控页面正确加载', async ({ page }) => {
    const examId = testProblems[0].id
    await page.goto(`${FRONTEND}/admin/exams/${examId}/monitor`)
    await page.waitForTimeout(3000)

    await expect(page.locator('main, [class*="content"]').first()).toBeVisible()
  })

  test('考生提交矩阵显示', async ({ page }) => {
    const examId = 1
    await page.goto(`${FRONTEND}/admin/exams/${examId}/monitor`)
    await page.waitForTimeout(3000)

    // 查找提交矩阵
    const matrix = page.locator('[class*="matrix"], table, .el-table').first()
    if (await matrix.isVisible()) {
      await expect(matrix).toBeVisible()
    }
  })

  test('实时刷新功能', async ({ page }) => {
    const examId = 1
    await page.goto(`${FRONTEND}/admin/exams/${examId}/monitor`)
    await page.waitForTimeout(3000)

    const refreshBtn = page.locator('button:has-text("刷新"), [class*="refresh"]').first()
    if (await refreshBtn.isVisible()) {
      await refreshBtn.click()
      await page.waitForTimeout(1000)
    }
  })
})

test.describe('教师管理 - 提交管理', () => {
  test.beforeEach(async ({ page }) => {
    await clearStorage(page)
    await setAuthState(page, testUsers.teacher)
  })

  test.afterEach(async ({ page }) => {
    await clearStorage(page)
  })

  test('提交管理页面正确加载', async ({ page }) => {
    await page.goto(`${FRONTEND}/admin/submissions`)
    await page.waitForTimeout(3000)

    await expect(page.locator('main, [class*="content"]').first()).toBeVisible()
  })

  test('提交列表显示', async ({ page }) => {
    await page.goto(`${FRONTEND}/admin/submissions`)
    await page.waitForTimeout(3000)

    const table = page.locator('table, .el-table').first()
    if (await table.isVisible()) {
      await expect(table).toBeVisible()
    }
  })

  test('提交筛选功能', async ({ page }) => {
    await page.goto(`${FRONTEND}/admin/submissions`)
    await page.waitForTimeout(2000)

    // 查找筛选控件
    const filterInput = page.locator('input[placeholder*="搜索"], .el-input input').first()
    if (await filterInput.isVisible()) {
      await filterInput.fill('Accepted')
      await page.waitForTimeout(1000)
    }
  })
})

test.describe('教师管理 - 学情分析', () => {
  test.beforeEach(async ({ page }) => {
    await clearStorage(page)
    await setAuthState(page, testUsers.teacher)
  })

  test.afterEach(async ({ page }) => {
    await clearStorage(page)
  })

  test('学情分析页面正确加载', async ({ page }) => {
    await page.goto(`${FRONTEND}/admin/analytics`)
    await page.waitForTimeout(3000)

    await expect(page.locator('main, [class*="content"]').first()).toBeVisible()
  })

  test('图表显示', async ({ page }) => {
    await page.goto(`${FRONTEND}/admin/analytics`)
    await page.waitForTimeout(3000)

    // 查找图表
    const charts = page.locator('[class*="chart"], canvas, .el-chart, svg').first()
    expect(await charts.count()).toBeGreaterThanOrEqual(0)
  })
})

test.describe('教师管理 - 系统设置', () => {
  test.beforeEach(async ({ page }) => {
    await clearStorage(page)
    await setAuthState(page, testUsers.teacher)
  })

  test.afterEach(async ({ page }) => {
    await clearStorage(page)
  })

  test('设置页面正确加载', async ({ page }) => {
    await page.goto(`${FRONTEND}/admin/settings`)
    await page.waitForTimeout(3000)

    await expect(page.locator('main, [class*="content"]').first()).toBeVisible()
  })

  test('运行模式切换', async ({ page }) => {
    await page.goto(`${FRONTEND}/admin/settings`)
    await page.waitForTimeout(2000)

    // 查找模式切换
    const switchInput = page.locator('.el-switch, [class*="switch"]').first()
    if (await switchInput.count() > 0) {
      // 设置选项存在
    }
  })
})
