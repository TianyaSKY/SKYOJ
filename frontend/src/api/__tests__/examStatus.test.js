import { beforeEach, expect, it, vi } from 'vitest'
vi.mock('@/utils/request', () => ({ default: vi.fn() }))
import request from '@/utils/request'
import { getMyExamStatus } from '../exam'

beforeEach(() => vi.resetAllMocks())

it.each([8, '8', undefined])('状态查询绑定页面考试 %s，省略时兼容旧调用', async examId => {
  const statuses = [{ problem_id: 1, current_score: 50 }]
  request.mockResolvedValue(statuses)
  expect(await getMyExamStatus(examId)).toBe(statuses)
  expect(request).toHaveBeenCalledExactlyOnceWith({
    url: '/exams/status', method: 'get',
    params: examId == null ? undefined : { exam_id: examId },
  })
})
