import {z} from 'zod'

/** AI 出题表单 */
export const generateProblemDraftSchema = z.object({
  background: z
    .string()
    .trim()
    .min(1, '题目背景不能为空')
    .max(5000, '题目背景过长'),
  difficulty: z
    .string()
    .trim()
    .min(1, '请选择难度')
    .max(32, '难度字段过长'),
})

/** 测例脚本生成表单 */
export const generateTestScriptDraftSchema = z.object({
  problem_id: z
    .number({invalid_type_error: '题目 ID 无效'})
    .int('题目 ID 必须是整数')
    .min(1, '题目 ID 无效'),
  direction: z.string().max(5000, '生成方向过长').default(''),
  count: z
    .number({invalid_type_error: '测试点个数无效'})
    .int('测试点个数必须是整数')
    .min(1, '至少 1 组')
    .max(50, '最多 50 组')
    .default(10),
  range_info: z.string().max(2000, '数据范围描述过长').default(''),
})

/** 测例执行表单 */
export const executeTestDataDraftSchema = z.object({
  problem_id: z
    .number({invalid_type_error: '题目 ID 无效'})
    .int()
    .min(1, '题目 ID 无效'),
  code: z.string().trim().min(1, '脚本代码不能为空'),
  type: z.string().trim().min(1).max(32).default('acm'),
  language: z.string().trim().min(1).max(32).default('python'),
  source_draft_id: z.number().int().min(1).optional().nullable(),
})
