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
  it('考试更新保留明确清空封榜与省略字段的区别', () => {
    expect(updateExamSchema.parse({freeze_minutes: null})).toEqual({freeze_minutes: null})
    expect(updateExamSchema.parse({title: '更名'})).not.toHaveProperty('freeze_minutes')
    expect(updateExamSchema.parse({title: '更名'})).toEqual({title: '更名'})
    expect(updateExamSchema.parse({freeze_minutes: 0})).toEqual({freeze_minutes: 0})
    expect(createExamSchema.parse(exam)).toMatchObject({
      description: '', contest_type: 'icpc', is_visible: false,
    })
  })
  it('局部更新题目不补入创建时的资源限制默认值', () => {
    expect(updateProblemSchema.parse({title: '更名'})).toEqual({title: '更名'})
    expect(updateProblemSchema.parse({})).toEqual({})
    expect(updateProblemSchema.parse({time_limit: null, memory_limit: null})).toEqual({
      time_limit: null, memory_limit: null,
    })
    expect(updateProblemSchema.parse({time_limit: 5000, memory_limit: 512})).toEqual({
      time_limit: 5000, memory_limit: 512,
    })
    expect(createProblemSchema.parse(problem)).toMatchObject({
      time_limit: 1000, memory_limit: 128, template_code: '',
    })
  })
})
