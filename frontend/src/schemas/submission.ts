import { z } from 'zod'

// WebSocket 外部消息必须经过运行时校验，缺省可选字段兼容历史推送。
export const submissionMessageSchema = z.object({
  submission_id: z.number().int().positive().optional(),
  status: z.string().min(1),
  score: z.number().finite().optional(),
  output_log: z.string().optional(),
})

export type SubmissionMessage = z.output<typeof submissionMessageSchema>
