import { isRecord } from '@/types/http'

// 捕获值可以是任意类型，只有明确的非空字符串消息才适合展示。
export function errorMessage(error: unknown, fallback: string): string {
  return isRecord(error) && typeof error.message === 'string' && error.message
    ? error.message
    : fallback
}

export function backendErrorMessage(error: unknown, fallback: string): string {
  const response = isRecord(error) && isRecord(error.response) ? error.response : null
  const data = response && isRecord(response.data) ? response.data : null
  const message = data?.message || data?.error
  return typeof message === 'string' && message ? message : fallback
}
