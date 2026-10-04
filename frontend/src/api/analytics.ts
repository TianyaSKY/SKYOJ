import request from '@/utils/request'
import type { PlatformAnalyticsResponse } from '@/types/analytics'

export function getPlatformAnalytics(): Promise<PlatformAnalyticsResponse> {
  return request<PlatformAnalyticsResponse>({ url: '/admin/analytics', method: 'get' })
}
