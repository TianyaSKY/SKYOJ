import {z} from 'zod'

export const createProblemSchema = z.object({
  title: z.string().min(1, '请输入题目标题').max(200, '标题最多 200 个字符'),
  content: z.string().min(1, '请输入题目内容'),
  language: z.enum(['python', 'java', 'c', 'cpp']),
  type: z.enum(['acm', 'oop', 'kaggle']),
  time_limit: z.number().int().min(100).max(30000).default(1000),
  memory_limit: z.number().int().min(16).max(4096).default(128),
  template_code: z.string().default(''),
})
export const updateProblemSchema = createProblemSchema.partial().extend({
  content: z.string().nullable().optional(),
  title: createProblemSchema.shape.title.nullable().optional(),
  language: createProblemSchema.shape.language.nullable().optional(),
  type: createProblemSchema.shape.type.nullable().optional(),
  time_limit: createProblemSchema.shape.time_limit.nullable().optional(),
  memory_limit: createProblemSchema.shape.memory_limit.nullable().optional(),
  template_code: z.string().nullable().optional(),
})
