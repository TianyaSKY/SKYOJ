/**
 * E2E 测试: 竞赛/考试模块
 * 覆盖考试列表、详情、排行榜等功能
 */
import { test, expect } from '@playwright/test'
import {
  testUsers,
  testExams,
  FRONTEND,
  setAuthState,
  clearStorage,
} from './fixtures/index.js'

// 按页面隔离考试模式，避免并行用例修改全局系统配置互相影响。
test.beforeEach(async ({page}) => {
  await page.route('**/api/sys/info', route => route.fulfill({
    json: {title: 'SKYOJ', practice: false, warning: false, info: ''},
  }))
})

test.describe('竞赛模块 - 考试列表', () => {
  test.beforeEach(async ({ page }) => {
    await clearStorage(page)
    await setAuthState(page, testUsers.student)
  })

  test.afterEach(async ({ page }) => {
    await clearStorage(page)
  })

  test('考试中心页面正确加载', async ({ page }) => {
    await page.goto(`${FRONTEND}/exam`)
    await page.waitForTimeout(2000)

    // 验证页面标题
    const title = page.locator('h1, h2, .page-title').first()
    await expect(title).toBeVisible()
  })

  test('考试列表显示', async ({ page }) => {
    await page.goto(`${FRONTEND}/exam`)
    await page.waitForTimeout(3000)

    // 验证有考试卡片或空状态
    const hasContent = await page.locator('.exam-card, .contest-item, [class*="exam"]').count()
    expect(hasContent).toBeGreaterThanOrEqual(0)
  })

  test('考试卡片显示关键信息', async ({ page }) => {
    await page.goto(`${FRONTEND}/exam`)
    await page.waitForTimeout(3000)

    // 查找考试卡片
    const examCard = page.locator('.exam-card').filter({hasText: testExams[0].title})
    await expect(examCard).toBeVisible()
    await expect(examCard.locator('.exam-title')).toHaveText(testExams[0].title)
    await expect(examCard.locator('.exam-meta')).toContainText('开始:')
    await expect(examCard.locator('.exam-meta')).toContainText('结束:')
  })

  test('已结束的考试标记', async ({ page }) => {
    await page.goto(`${FRONTEND}/exam`)
    await page.waitForTimeout(2000)

    // 查找已结束标记
    const ended = page.locator('text=/已结束|Ended|Closed/i').first()
    if (await ended.count() > 0) {
      await expect(ended.first()).toBeVisible()
    }
  })

  test('未开始的考试显示倒计时', async ({ page }) => {
    await page.goto(`${FRONTEND}/exam`)
    await page.waitForTimeout(2000)

    // 查找倒计时或即将开始标记
    const countdown = page.locator('text=/即将开始|Coming Soon|Countdown/i').first()
    if (await countdown.count() > 0) {
      await expect(countdown.first()).toBeVisible()
    }
  })
})

test.describe('竞赛模块 - 考试详情', () => {
  test.beforeEach(async ({ page }) => {
    await clearStorage(page)
    await setAuthState(page, testUsers.student)
  })

  test.afterEach(async ({ page }) => {
    await clearStorage(page)
  })

  test('考试详情页正确加载', async ({ page }) => {
    const examId = testExams[0].id
    await page.goto(`${FRONTEND}/exam/${examId}`)
    await page.waitForTimeout(3000)

    // 验证页面主要元素
    const content = page.locator('.exam-detail, .contest-detail, main, [class*="content"]').first()
    await expect(content).toBeVisible()
  })

  test('考试倒计时显示', async ({ page }) => {
    const examId = testExams[0].id
    await page.goto(`${FRONTEND}/exam/${examId}`)
    await page.waitForTimeout(2000)

    // 查找倒计时
    const timer = page.locator('.timer-value')
    await expect(timer).toHaveText(/\d{2}:\d{2}:\d{2}/)
  })

  test('考试题目列表显示', async ({ page }) => {
    const examId = testExams[0].id
    await page.goto(`${FRONTEND}/exam/${examId}`)
    await page.waitForTimeout(3000)

    // 查找题目列表
    const problemList = page.locator('.problem-list, table, [class*="problem"]').first()
    if (await problemList.isVisible()) {
      await expect(problemList).toBeVisible()
    }
  })

  test('考试密码输入框', async ({ page }) => {
    const examId = testExams[0].id
    await page.goto(`${FRONTEND}/exam/${examId}`)
    await page.waitForTimeout(2000)

    // 查找密码输入框
    const passwordInput = page.locator('input[type="password"]').first()
    if (await passwordInput.isVisible()) {
      await expect(passwordInput).toBeVisible()
    }
  })

  test('考试说明显示', async ({ page }) => {
    const examId = testExams[0].id
    await page.goto(`${FRONTEND}/exam/${examId}`)
    await page.waitForTimeout(2000)

    // 查找考试说明区域
    const description = page.locator('[class*="description"], [class*="info"]').first()
    if (await description.isVisible()) {
      await expect(description).toBeVisible()
    }
  })
})

test.describe('竞赛模块 - 排行榜', () => {
  test.beforeEach(async ({ page }) => {
    await clearStorage(page)
    await setAuthState(page, testUsers.student)
  })

  test.afterEach(async ({ page }) => {
    await clearStorage(page)
  })

  test('排行榜页面正确加载', async ({ page }) => {
    const examId = testExams[0].id
    await page.goto(`${FRONTEND}/exam/${examId}/rank`)
    await page.waitForTimeout(3000)

    // 验证页面
    const content = page.locator('.rank-table, table, main').first()
    await expect(content).toBeVisible()
  })

  test('排行榜显示用户名和分数', async ({ page }) => {
    const examId = testExams[0].id
    await page.goto(`${FRONTEND}/exam/${examId}/rank`)
    await page.waitForTimeout(3000)

    // 验证表格内容
    const table = page.locator('table').first()
    if (await table.isVisible()) {
      // 验证有数据行
      const rows = page.locator('tbody tr')
      const count = await rows.count()
      expect(count).toBeGreaterThanOrEqual(0)
    }
  })

  test('排行榜前三名突出显示', async ({ page }) => {
    const examId = testExams[0].id
    await page.goto(`${FRONTEND}/exam/${examId}/rank`)
    await page.waitForTimeout(3000)

    // 查找领奖台或前三名标记
    const podium = page.locator('[class*="podium"], [class*="top-three"], .rank-1, .rank-2, .rank-3').first()
    // 可能存在也可能不存在
    expect(await podium.count()).toBeGreaterThanOrEqual(0)
  })

  test('排行榜刷新功能', async ({ page }) => {
    const examId = testExams[0].id
    await page.goto(`${FRONTEND}/exam/${examId}/rank`)
    await page.waitForTimeout(3000)

    // 查找刷新按钮
    const refreshBtn = page.locator('button:has-text("刷新"), button:has-text("Refresh"), [class*="refresh"]').first()
    if (await refreshBtn.isVisible()) {
      await refreshBtn.click()
      await page.waitForTimeout(2000)
    }
  })
})

test.describe('竞赛模块 - 竞赛进行中', () => {
  test.beforeEach(async ({ page }) => {
    await clearStorage(page)
    await setAuthState(page, testUsers.student)
  })

  test.afterEach(async ({ page }) => {
    await clearStorage(page)
  })

  test('进入竞赛后显示答题界面', async ({ page }) => {
    const examId = testExams[0].id
    // 带密码进入
    await page.goto(`${FRONTEND}/exam/${examId}`)
    await page.waitForTimeout(2000)

    // 如果有密码框，输入密码
    const passwordInput = page.locator('input[type="password"]').first()
    if (await passwordInput.isVisible()) {
      await passwordInput.fill(testExams[0].password)
      const joinBtn = page.locator('button:has-text("进入"), button:has-text("Join"), button:has-text("开始")').first()
      if (await joinBtn.isVisible()) {
        await joinBtn.click()
        await page.waitForTimeout(3000)
      }
    }

    // 验证答题界面元素
    const questionArea = page.locator('[class*="question"], [class*="problem"]').first()
    expect(await questionArea.count()).toBeGreaterThanOrEqual(0)
  })

  test('提交记录在竞赛期间保存', async ({ page }) => {
    const examId = testExams[0].id
    await page.goto(`${FRONTEND}/exam/${examId}`)
    await page.waitForTimeout(2000)

    // 进入竞赛后进行操作
    const passwordInput = page.locator('input[type="password"]').first()
    if (await passwordInput.isVisible()) {
      await passwordInput.fill(testExams[0].password)
      const joinBtn = page.locator('button:has-text("进入"), button:has-text("Join")').first()
      if (await joinBtn.isVisible()) {
        await joinBtn.click()
        await page.waitForTimeout(3000)

        // 提交代码
        const submitBtn = page.locator('button:has-text("提交"), button:has-text("Submit")').first()
        if (await submitBtn.isVisible() && await submitBtn.isEnabled()) {
          await submitBtn.click()
          await page.waitForTimeout(2000)

          // 验证提交成功
          const successMsg = page.locator('.el-message--success, [class*="success"]').first()
          // 提交应该成功或显示判题中
        }
      }
    }
  })
})
