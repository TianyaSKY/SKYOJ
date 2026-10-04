import type * as System from '@/types/system'
import type { MessageResponse, JsonValue } from '@/types/common'
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

// 占位：原“重建搜索索引”按钮在重构中移除（dd457285），仅保留 API 客户端壳；
// 后端尚未提供对应端点，调用会 404；后续若恢复索引重建功能请同时补 sys_dict.py。
export function rebuildIndex(): Promise<MessageResponse> {
    return request<MessageResponse>({
        url: '/sys/rebuild_index',
        method: 'post'
    })
}
