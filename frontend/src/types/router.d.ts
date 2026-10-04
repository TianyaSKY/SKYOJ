import 'vue-router'
import type { UserRole } from '@/schemas/user'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    role?: UserRole
  }
}
