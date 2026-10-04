import {z} from 'zod'

const username = z.string().min(1, '请输入用户名').max(80, '用户名最多 80 个字符')
export const loginSchema = z.object({
  username,
  password: z.string().min(1, '请输入密码').max(128, '密码最多 128 个字符'),
})
export const registerSchema = z.object({
  username,
  password: z.string().min(6, '密码至少 6 个字符').max(128, '密码最多 128 个字符'),
})

export type LoginInput = z.input<typeof loginSchema>
export type Login = z.output<typeof loginSchema>

export type RegisterInput = z.input<typeof registerSchema>
export type Register = z.output<typeof registerSchema>
