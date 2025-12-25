import request from '@/utils/request'

export function getExamList(params) {
    return request({
        url: '/exams/',
        method: 'get',
        params
    })
}

export function getExamDetail(id) {
    return request({
        url: `/exams/${id}`,
        method: 'get'
    })
}

export function createExam(data) {
    return request({
        url: '/exams/',
        method: 'post',
        data
    })
}

export function updateExam(id, data) {
    return request({
        url: `/exams/${id}`,
        method: 'put',
        data
    })
}

export function deleteExam(id) {
    return request({
        url: `/exams/${id}`,
        method: 'delete'
    })
}

export function addExamProblem(examId, data) {
    return request({
        url: `/exams/${examId}/problems`,
        method: 'post',
        data
    })
}

export function removeExamProblem(examId, problemId) {
    return request({
        url: `/exams/${examId}/problems/${problemId}`,
        method: 'delete'
    })
}

export function verifyExamPassword(id, password) {
    return request({
        url: `/exams/${id}/verify`,
        method: 'post',
        data: {password}
    })
}

export function enterExam(id, password) {
    return request({
        url: `/exams/${id}/enter`,
        method: 'post',
        data: {password}
    })
}

export function exitExam() {
    return request({
        url: '/exams/exit',
        method: 'post'
    })
}

export function getMyExamStatus() {
    return request({
        url: '/exams/status',
        method: 'get'
    })
}

/**
 * 获取考试监控数据（教师端）
 */
export function getExamMonitor(id) {
    return request({
        url: `/exams/${id}/monitor`,
        method: 'get'
    })
}

/**
 * 获取特定提交的详细信息（包含代码）
 */
export function getSubmissionDetail(id) {
    return request({
        url: `/submissions/${id}`,
        method: 'get'
    })
}

/**
 * 查重单次提交
 */
export function checkSubmissionPlagiarism(id) {
    return request({
        url: `/submissions/${id}/check_plagiarism`,
        method: 'post'
    })
}

/**
 * 查重整场考试
 */
export function checkExamPlagiarism(id) {
    return request({
        url: `/exams/${id}/check_plagiarism`,
        method: 'post'
    })
}
