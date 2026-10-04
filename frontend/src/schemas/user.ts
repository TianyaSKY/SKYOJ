import { z } from 'zod'

export const userRoleSchema = z.enum(['student', 'teacher', 'admin'])
export type UserRole = z.output<typeof userRoleSchema>

// 兼容已有部分用户缓存，验证已存在字段，不补入身份或默认角色。
export const cachedUserSchema = z
  .object({
    id: z.number().int().positive().optional(),
    username: z.string().optional(),
    role: userRoleSchema.optional(),
    created_at: z.string().nullable().optional(),
    avatar: z.string().nullable().optional(),
  })
  .passthrough()
export type CachedUser = z.output<typeof cachedUserSchema>
