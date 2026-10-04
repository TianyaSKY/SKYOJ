import { z } from 'zod'

const fields = z.object({
  title: z.string().min(1, '请输入题目标题').max(200, '标题最多 200 个字符'),
  content: z.string().min(1, '请输入题目内容'),
  language: z.enum(['python', 'java', 'c', 'cpp']),
  type: z.enum(['acm', 'oop', 'kaggle']),
  time_limit: z.number().int().min(100).max(30000),
  memory_limit: z.number().int().min(16).max(4096),
  template_code: z.string(),
})
export const createProblemSchema = fields.extend({
  time_limit: fields.shape.time_limit.default(1000),
  memory_limit: fields.shape.memory_limit.default(128),
  template_code: fields.shape.template_code.default(''),
})
export const updateProblemSchema = fields.partial().extend({
  content: z.string().nullable().optional(),
  title: fields.shape.title.nullable().optional(),
  language: fields.shape.language.nullable().optional(),
  type: fields.shape.type.nullable().optional(),
  time_limit: fields.shape.time_limit.nullable().optional(),
  memory_limit: fields.shape.memory_limit.nullable().optional(),
  template_code: z.string().nullable().optional(),
})

export type CreateProblemInput = z.input<typeof createProblemSchema>
export type CreateProblem = z.output<typeof createProblemSchema>

export type UpdateProblemInput = z.input<typeof updateProblemSchema>
export type UpdateProblem = z.output<typeof updateProblemSchema>
