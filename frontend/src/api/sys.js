import request from '@/utils/request'

export function getSysInfo() {
    return request({
        url: '/sys/info',
        method: 'get'
    })
}

export function updateSysInfo(data) {
    return request({
        url: '/sys/info',
        method: 'put',
        data
    })
}

export function getSysStatistics() {
    return request({
        url: '/sys/statistics',
        method: 'get'
    })
}

// 占位：原“重建搜索索引”按钮在重构中移除（dd457285），仅保留 API 客户端壳；
// 后端尚未提供对应端点，调用会 404；后续若恢复索引重建功能请同时补 sys_dict.py。
export function rebuildIndex() {
    return request({
        url: '/sys/rebuild_index',
        method: 'post'
    })
}
