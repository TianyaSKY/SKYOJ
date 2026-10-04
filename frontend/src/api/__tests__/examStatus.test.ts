import { beforeEach, expect, it, vi } from 'vitest'
vi.mock('@/utils/request', () => ({ default: vi.fn() }))
import request from '@/utils/request'
import { getMyExamStatus } from '../exam'

beforeEach(() => vi.resetAllMocks())

it.each([8, '8', undefined])('状态查询绑定页面考试 %s，省略时兼容旧调用', async examId => {
  const statuses = [{ problem_id: 1, current_score: 50 }]
  vi.mocked(request).mockResolvedValue(statuses)
  let result
  if (typeof examId === 'string') {
    // 旧 JS 调用仍保持运行时兼容，新 TS 调用须在路由边界转换数字。
    // @ts-expect-error 验证旧 JS 字符串 ID 的兼容行为
    result = await getMyExamStatus(examId)
  } else {
    result = await getMyExamStatus(examId)
  }
  expect(result).toBe(statuses)
  expect(request).toHaveBeenCalledExactlyOnceWith({
    url: '/exams/status', method: 'get',
    params: examId == null ? undefined : { exam_id: examId },
  })
})
