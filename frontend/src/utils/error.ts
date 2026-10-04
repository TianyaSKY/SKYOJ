import { isRecord } from '@/types/http'

// 捕获值可以是任意类型，只有明确的非空字符串消息才适合展示。
export function errorMessage(error: unknown, fallback: string): string {
  return isRecord(error) && typeof error.message === 'string' && error.message
    ? error.message : fallback
}
