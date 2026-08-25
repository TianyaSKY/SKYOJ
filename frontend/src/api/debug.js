import request from '@/utils/request'

/**
 * 提交 ACM 调试运行。
 * 仅 ACM 题目可用；执行第一个测试点，不计入成绩。
 * @param {Object} data - { problem_id, code, language, exam_id? }
 */
export function debugSolution(data) {
    return request({
        url: '/debug',
        method: 'post',
        data
    })
}

/**
 * 查询调试运行结果（含输入/期望输出/实际输出/状态）。
 * @param {number} id
 */
export function getDebugRun(id) {
    return request({
        url: `/debug/${id}`,
        method: 'get'
    })
}
