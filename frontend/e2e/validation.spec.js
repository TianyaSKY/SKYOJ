/** 表单校验回归，API 使用可控响应，验证实际页面是否发出请求。 */
import {test, expect} from '@playwright/test'

test.beforeEach(async ({page}) => {
  await page.route('**/api/sys/info', route => route.fulfill({
    json: {title: 'SKYOJ', practice: true, warning: false, info: ''},
  }))
})

test('登录允许后端支持的一位密码并发送已校验的请求', async ({page}) => {
  let payload
  await page.route('**/api/auth/login', async route => {
    payload = route.request().postDataJSON()
    await route.fulfill({json: {token: 'test-token', user: {id: 1, username: 'a', role: 'student'}}})
  })
  await page.goto('/login')
  await page.locator('input[type="text"]').fill('a')
  await page.locator('input[type="password"]').fill('x')
  await page.locator('button[type="submit"]').click()
  await expect.poll(() => payload).toEqual({username: 'a', password: 'x'})
})

test('注册拒绝超长用户名，修改后接受一位用户名', async ({page}) => {
  let calls = 0
  let payload
  await page.route('**/api/auth/register', async route => {
    calls += 1
    payload = route.request().postDataJSON()
    await route.fulfill({status: 201, json: {message: 'User registered successfully'}})
  })
  await page.goto('/register')
  await page.locator('input[type="text"]').fill('x'.repeat(81))
  await page.locator('input[type="password"]').nth(0).fill('123456')
  await page.locator('input[type="password"]').nth(1).fill('123456')
  await page.locator('button[type="submit"]').click()
  await expect(page.locator('.el-form-item__error').first()).toBeVisible()
  expect(calls).toBe(0)
  await page.locator('input[type="text"]').fill('a')
  await page.locator('button[type="submit"]').click()
  await expect.poll(() => payload).toEqual({username: 'a', password: '123456'})
  expect(calls).toBe(1)
})
