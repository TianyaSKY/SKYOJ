import {describe, expect, it} from 'vitest'
import {loginSchema, registerSchema} from '../auth'
import {createProblemSchema, updateProblemSchema} from '../problem'
import {createExamSchema, updateExamSchema} from '../exam'

const problem = {title: '题目', content: '说明', language: 'python', type: 'acm'}
const exam = {title: '考试', start_time: '2026-10-03T10:00:00', end_time: '2026-10-03T12:00:00'}

describe('HTTP 请求校验契约', () => {
  it('登录允许已有短密码，注册要求至少六位', () => {
    expect(loginSchema.safeParse({username: 'a', password: 'x'}).success).toBe(true)
    expect(registerSchema.safeParse({username: 'a', password: 'x'}).success).toBe(false)
    expect(registerSchema.safeParse({username: 'a', password: '123456'}).success).toBe(true)
  })
  it('用户名及密码长度与后端一致', () => {
    expect(loginSchema.safeParse({username: 'x'.repeat(81), password: 'x'}).success).toBe(false)
    expect(registerSchema.safeParse({username: 'a', password: 'x'.repeat(129)}).success).toBe(false)
  })
  it('题目限制及枚举校验，移除详情中的只读字段', () => {
    expect(createProblemSchema.parse({...problem, id: 99}).id).toBeUndefined()
    for (const patch of [{time_limit: 99}, {memory_limit: 4097}, {language: 'ruby'}, {content: ''}]) {
      expect(createProblemSchema.safeParse({...problem, ...patch}).success).toBe(false)
    }
    expect(updateProblemSchema.safeParse({content: '', time_limit: null}).success).toBe(true)
  })
  it('考试校验时间顺序、比赛类型和封榜范围', () => {
    expect(createExamSchema.safeParse(exam).success).toBe(true)
    for (const patch of [{end_time: exam.start_time}, {contest_type: 'unknown'}, {freeze_minutes: -1}]) {
      expect(createExamSchema.safeParse({...exam, ...patch}).success).toBe(false)
    }
    expect(updateExamSchema.safeParse({title: '更名'}).success).toBe(true)
  })
})
