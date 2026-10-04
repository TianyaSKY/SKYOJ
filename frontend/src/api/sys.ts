import type * as System from '@/types/system'
import type { JsonValue } from '@/types/common'
import request from '@/utils/request'

export function getSysInfo(): Promise<System.SystemConfig> {
    return request<System.SystemConfig>({
        url: '/sys/info',
        method: 'get'
    })
}

export function updateSysInfo(data: Record<string, JsonValue>): Promise<System.UpdateSysConfigResponse> {
    return request<System.UpdateSysConfigResponse>({
        url: '/sys/info',
        method: 'put',
        data
    })
}

export function getSysStatistics(): Promise<System.SystemStatisticsResponse> {
    return request<System.SystemStatisticsResponse>({
        url: '/sys/statistics',
        method: 'get'
    })
}
