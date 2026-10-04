import { z } from 'zod'

/** AI 出题表单 */
export const generateProblemDraftSchema = z.object({
  background: z.string().trim().min(1, '题目背景不能为空').max(5000, '题目背景过长'),
  difficulty: z.string().trim().min(1, '请选择难度').max(32, '难度字段过长'),
})

/** 测例脚本生成表单 */
export const generateTestScriptDraftSchema = z.object({
  problem_id: z.number({ error: '题目 ID 无效' }).int('题目 ID 必须是整数').min(1, '题目 ID 无效'),
  direction: z.string().max(5000, '生成方向过长').default(''),
})

/** 测例执行表单 */
export const executeTestDataDraftSchema = z.object({
  problem_id: z.number({ error: '题目 ID 无效' }).int().min(1, '题目 ID 无效'),
  code: z.string().trim().min(1, '脚本代码不能为空'),
  type: z.string().trim().min(1).max(32).default('acm'),
  language: z.string().trim().min(1).max(32).default('python'),
  source_draft_id: z.number().int().min(1).optional().nullable(),
})

export type GenerateProblemDraftInput = z.input<typeof generateProblemDraftSchema>
export type GenerateProblemDraft = z.output<typeof generateProblemDraftSchema>

export type GenerateTestScriptDraftInput = z.input<typeof generateTestScriptDraftSchema>
export type GenerateTestScriptDraft = z.output<typeof generateTestScriptDraftSchema>

export type ExecuteTestDataDraftInput = z.input<typeof executeTestDataDraftSchema>
export type ExecuteTestDataDraft = z.output<typeof executeTestDataDraftSchema>

// LLM 分析结果来自外部模型，展示前校验结构。
export const codeAnalysisSchema = z.object({
  rating: z.string(),
  logic: z.string(),
  suggestion: z.string(),
})
export type CodeAnalysis = z.output<typeof codeAnalysisSchema>

// 不同任务共享草稿容器，已知展示与执行字段校验类型，保留任务专属 JSON 字段。
export const draftResultSchema = z
  .object({
    title: z.string().optional(),
    content: z.string().optional(),
    type: z.string().optional(),
    language: z.string().optional(),
    code: z.string().optional(),
    problem_id: z.number().int().positive().optional(),
    problem_type: z.string().optional(),
    time_limit: z.number().optional(),
    memory_limit: z.number().optional(),
    message: z.string().optional(),
  })
  .catchall(z.json())
export type DraftResult = z.output<typeof draftResultSchema>
