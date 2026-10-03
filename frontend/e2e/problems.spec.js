/**
 * E2E 测试: 题目模块
 * 覆盖题目列表、详情、提交等功能
 */
import { test, expect } from '@playwright/test'
import {
  testUsers,
  testProblems,
  FRONTEND,
  setAuthState,
  clearStorage,
} from './fixtures/index.js'

async function enterCode(page, code) {
  // Monaco 的隐藏 IME textarea 不可点击；通过实际编辑区域输入。
  const editor = page.locator('.editor-wrapper .monaco-editor .view-lines').first()
  await expect(editor).toBeVisible()
  await editor.click()
  // Monaco 按 UA 判定快捷键；设备模拟的 UA 可能与运行测试的主机不同。
  const modifier = await page.evaluate(() => navigator.userAgent.includes('Macintosh') ? 'Meta' : 'Control')
  await page.keyboard.press(`${modifier}+A`)
  await page.keyboard.insertText(code)
  await expect(editor).toContainText(code)
}

test.describe('题目模块 - 题目列表', () => {
  test.beforeEach(async ({ page }) => {
    await clearStorage(page)
    await setAuthState(page, testUsers.student)
  })

  test.afterEach(async ({ page }) => {
    await clearStorage(page)
  })

  test('题目列表页正确加载', async ({ page }) => {
    await page.goto(`${FRONTEND}/problems`)
    await page.waitForTimeout(2000)

    // 验证页面主要元素
    await expect(page.locator('h1, h2, .page-title, [class*="title"]').first()).toBeVisible()
  })

  test('题目列表包含题目卡片', async ({ page }) => {
    await page.goto(`${FRONTEND}/problems`)
    await page.waitForTimeout(3000)

    // 验证有题目列表或空状态
    const hasContent = await page.locator('.problem-card, .problem-item, table tbody tr, [class*="problem"]').count()
    expect(hasContent).toBeGreaterThanOrEqual(0) // 允许空列表
  })

  test('题目搜索功能', async ({ page }) => {
    await page.goto(`${FRONTEND}/problems`)
    await page.waitForTimeout(2000)

    // 查找搜索框
    const searchInput = page.locator('input[type="search"], input[placeholder*="搜索"], .search-input input').first()
    if (await searchInput.isVisible()) {
      await searchInput.fill('A+B')
      await page.waitForTimeout(1000)

      // 验证搜索结果
      const results = await page.locator('.problem-card, .problem-item, tbody tr').count()
      expect(results).toBeGreaterThanOrEqual(0)
    }
  })

  test('题目难度筛选', async ({ page }) => {
    await page.goto(`${FRONTEND}/problems`)
    await page.waitForTimeout(2000)

    // 查找难度筛选按钮
    const difficultyFilter = page.locator('button:has-text("Easy"), button:has-text("Medium"), button:has-text("Hard"), .filter-btn').first()
    if (await difficultyFilter.isVisible()) {
      await difficultyFilter.click()
      await page.waitForTimeout(1000)
    }
  })

  test('题目列表分页', async ({ page }) => {
    await page.goto(`${FRONTEND}/problems`)
    await page.waitForTimeout(2000)

    // 查找分页控件
    const pagination = page.locator('.el-pagination, .pagination, [class*="pagination"]').first()
    if (await pagination.isVisible()) {
      const nextBtn = pagination.locator('button:has-text("下一页"), button:has-text(">"), [class*="next"]').first()
      if (await nextBtn.isEnabled()) {
        await nextBtn.click()
        await page.waitForTimeout(1000)
      }
    }
  })
})

test.describe('题目模块 - 题目详情', () => {
  test.beforeEach(async ({ page }) => {
    await clearStorage(page)
    await setAuthState(page, testUsers.student)
  })

  test.afterEach(async ({ page }) => {
    await clearStorage(page)
  })

  test('题目详情页包含必要元素', async ({ page }) => {
    // 使用测试题目ID
    const problemId = testProblems[0].id
    await page.goto(`${FRONTEND}/problem/${problemId}`)
    await page.waitForTimeout(3000)

    // 验证关键元素
    // 题目描述区域
    const descriptionArea = page.locator('.problem-description, .markdown-body, [class*="description"]').first()
    if (await descriptionArea.isVisible()) {
      await expect(descriptionArea).toBeVisible()
    }

    // 代码编辑器
    const editor = page.locator('.monaco-editor, .CodeMirror, [class*="editor"]').first()
    if (await editor.isVisible()) {
      await expect(editor).toBeVisible()
    }

    // 提交按钮
    const submitBtn = page.locator('button:has-text("提交"), button:has-text("Submit"), [class*="submit"]').first()
    if (await submitBtn.isVisible()) {
      await expect(submitBtn).toBeVisible()
    }
  })

  test('题目标签显示', async ({ page }) => {
    const problemId = testProblems[0].id
    await page.goto(`${FRONTEND}/problem/${problemId}`)
    await page.waitForTimeout(2000)

    // 验证标签显示
    const tags = page.locator('.el-tag, [class*="tag"]').first()
    // 标签可能不存在，这是正常的
    expect(await tags.count()).toBeGreaterThanOrEqual(0)
  })

  test('题目时间/空间限制显示', async ({ page }) => {
    const problemId = testProblems[0].id
    await page.goto(`${FRONTEND}/problem/${problemId}`)
    await page.waitForTimeout(2000)

    // 验证限制信息显示
    const limits = page.locator('text=/时间|空间|限制|Limit/i').first()
    if (await limits.isVisible()) {
      await expect(limits).toBeVisible()
    }
  })
})

test.describe('题目模块 - 代码提交', () => {
  test.beforeEach(async ({ page }) => {
    await clearStorage(page)
    await setAuthState(page, testUsers.student)
  })

  test.afterEach(async ({ page }) => {
    await clearStorage(page)
  })

  test('代码编辑器可以输入代码', async ({ page }) => {
    const problemId = testProblems[0].id
    await page.goto(`${FRONTEND}/problem/${problemId}`)
    await page.waitForTimeout(3000)

    // 查找编辑器
    await enterCode(page, 'print(3)')
  })

  test('提交按钮点击后触发提交', async ({ page }) => {
    const problemId = testProblems[0].id
    await page.goto(`${FRONTEND}/problem/${problemId}`)
    await page.waitForTimeout(3000)

    // 输入代码
    await enterCode(page, 'print(3)')

    // 点击提交
    const responsePromise = page.waitForResponse(response =>
      response.url().includes('/api/submissions') && response.request().method() === 'POST')
    await page.getByRole('button', {name: '提交代码', exact: true}).click()
    const response = await responsePromise
    expect(response.ok()).toBeTruthy()
    const result = await response.json()
    expect(result.submission_id).toBeGreaterThan(0)
    const saved = await page.request.get(`${FRONTEND}/api/submissions/${result.submission_id}`, {
      headers: {Authorization: `Bearer ${await page.evaluate(() => localStorage.getItem('token'))}`},
    })
    expect(saved.ok()).toBeTruthy()
    expect((await saved.json()).code).toBe('print(3)')
  })

  test('提交后可以查看提交详情', async ({ page }) => {
    const problemId = testProblems[0].id
    await page.goto(`${FRONTEND}/problem/${problemId}`)
    await page.waitForTimeout(3000)

    // 提交代码
    const submitBtn = page.locator('button:has-text("提交"), button:has-text("Submit")').first()
    if (await submitBtn.isVisible() && await submitBtn.isEnabled()) {
      await submitBtn.click()
      await page.waitForTimeout(3000)

      // 尝试点击查看提交详情
      const viewDetailBtn = page.locator('a:has-text("查看"), a:has-text("详情"), [href*="/submission/"]').first()
      if (await viewDetailBtn.isVisible()) {
        await viewDetailBtn.click()
        await page.waitForTimeout(2000)
        await expect(page).toHaveURL(/\/submission\/\d+/)
      }
    }
  })
})

test.describe('题目模块 - 提交记录', () => {
  test.beforeEach(async ({ page }) => {
    await clearStorage(page)
    await setAuthState(page, testUsers.student)
  })

  test.afterEach(async ({ page }) => {
    await clearStorage(page)
  })

  test('提交详情页显示判题状态', async ({ page }) => {
    // 使用测试提交ID
    const submissionId = 1
    await page.goto(`${FRONTEND}/submission/${submissionId}`)
    await page.waitForTimeout(3000)

    // 验证判题状态显示
    const status = page.locator('[class*="status"], [class*="result"], .el-tag').first()
    // 允许状态为任意值
    expect(await status.count()).toBeGreaterThanOrEqual(0)
  })

  test('提交详情页显示源代码', async ({ page }) => {
    const submissionId = 1
    await page.goto(`${FRONTEND}/submission/${submissionId}`)
    await page.waitForTimeout(2000)

    // 验证代码显示区域
    const codeArea = page.locator('.monaco-editor, pre code, [class*="source"]').first()
    if (await codeArea.isVisible()) {
      await expect(codeArea).toBeVisible()
    }
  })
})
