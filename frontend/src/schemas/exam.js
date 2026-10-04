import {z} from 'zod'

// 接受日期选择器的本地时间和带时区 ISO 时间，与后端 datetime 对齐。
const datetime = z.string().refine(value =>
  /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}/.test(value) && Number.isFinite(Date.parse(value)),
  '请输入有效的考试时间',
)
const problemIds = z.array(z.number().int().positive()).refine(ids => new Set(ids).size === ids.length, '考试题目不能重复')
const fields = z.object({
  title: z.string().min(1, '请输入考试标题').max(100, '标题最多 100 个字符'),
  description: z.string(),
  start_time: datetime,
  end_time: datetime,
  contest_type: z.enum(['icpc', 'ioi']),
  freeze_minutes: z.number().int().nonnegative().nullable().optional(),
  password: z.string().nullable().optional(),
  is_visible: z.boolean(),
})
const timesValid = value => !value.start_time || !value.end_time ||
  Date.parse(value.start_time) < Date.parse(value.end_time)
export const createExamSchema = fields.extend({
  problem_ids: problemIds.default([]),
  description: fields.shape.description.default(''),
  contest_type: fields.shape.contest_type.default('icpc'),
  is_visible: fields.shape.is_visible.default(false),
}).refine(timesValid, {
  message: '考试开始时间必须早于结束时间', path: ['end_time'],
})
export const updateExamSchema = fields.partial().extend({problem_ids: problemIds.nullable().optional()}).refine(timesValid, {
  message: '考试开始时间必须早于结束时间', path: ['end_time'],
})
