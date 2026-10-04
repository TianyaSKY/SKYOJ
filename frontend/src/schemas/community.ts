import { z } from 'zod'

// 保留 Markdown 原文，空白检查仅用于校验，不删除代码块缩进。
const nonblank = (value: string) => value.trim().length > 0

export const solutionFormSchema = z.object({
  title: z
    .string()
    .min(2, '题解标题至少 2 个字符')
    .max(200, '题解标题最多 200 个字符')
    .refine(nonblank, '题解标题不能为空'),
  content: z
    .string()
    .min(1, '题解正文不能为空')
    .max(20000, '题解正文最多 20000 个字符')
    .refine(nonblank, '题解正文不能为空'),
  language: z.string().max(50, '代码示例语言最多 50 个字符').nullable().optional(),
})

export const commentFormSchema = z.object({
  content: z.string().trim().min(1, '评论不能为空').max(1000, '评论最多 1000 个字符'),
})

export type SolutionFormInput = z.input<typeof solutionFormSchema>
export type SolutionForm = z.output<typeof solutionFormSchema>

export type CommentFormInput = z.input<typeof commentFormSchema>
export type CommentForm = z.output<typeof commentFormSchema>
