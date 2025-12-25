import request from '@/utils/request'

/**
 * 获取查重日志列表
 * @param {Object} params { problem_id, min_score }
 */
export function getPlagiarismLogs(params) {
    return request({
        url: '/plagiarism/logs',
        method: 'get',
        params
    })
}

/**
 * 获取特定提交的查重详情
 */
export function getPlagiarismDetail(submissionId) {
    return request({
        url: `/plagiarism/logs/${submissionId}`,
        method: 'get'
    })
}

/**
 * 手动触发批量查重任务
 */
export function checkPlagiarismBatch(data) {
    return request({
        url: '/plagiarism/check_batch',
        method: 'post',
        data
    })
}

/**
 * 删除特定的查重日志
 */
export function deletePlagiarismLog(logId) {
    return request({
        url: `/plagiarism/logs/${logId}`,
        method: 'delete'
    })
}
