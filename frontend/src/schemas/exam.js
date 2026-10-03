import {z} from 'zod'

// 接受日期选择器的本地时间和带时区 ISO 时间，与后端 datetime 对齐。
const datetime = z.string().refine(value =>
  /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}/.test(value) && Number.isFinite(Date.parse(value)),
  '请输入有效的考试时间',
)
const fields = z.object({
  title: z.string().min(1, '请输入考试标题').max(100, '标题最多 100 个字符'),
  description: z.string().default(''),
  start_time: datetime,
  end_time: datetime,
  contest_type: z.enum(['icpc', 'ioi']).default('icpc'),
  freeze_minutes: z.number().int().nonnegative().nullable().optional(),
  password: z.string().nullable().optional(),
  is_visible: z.boolean().default(false),
})
const timesValid = value => !value.start_time || !value.end_time ||
  Date.parse(value.start_time) < Date.parse(value.end_time)
export const createExamSchema = fields.refine(timesValid, {
  message: '考试开始时间必须早于结束时间', path: ['end_time'],
})
export const updateExamSchema = fields.partial().refine(timesValid, {
  message: '考试开始时间必须早于结束时间', path: ['end_time'],
})
