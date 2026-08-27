import request from '@/utils/request'

export function getProblemList(params) {
    return request({
        url: '/problems/',
        method: 'get',
        params
    })
}

export function searchProblems(params) {
    return request({
        url: '/search',
        method: 'get',
        params
    })
}

export function getProblemDetail(id) {
    return request({
        url: `/problems/${id}`,
        method: 'get'
    })
}

export function submitSolution(data) {
    const isFormData = data instanceof FormData
    return request({
        url: '/submissions/submit',
        method: 'post',
        data,
        timeout: 120000,
        headers: isFormData ? {'Content-Type': 'multipart/form-data'} : undefined
    })
}

export function getSubmissionDetail(id) {
    return request({
        url: `/submissions/${id}`,
        method: 'get'
    })
}

// --- Admin Functions ---

export function createProblem(data) {
    return request({
        url: '/problems/',
        method: 'post',
        data
    })
}

export function updateProblem(id, data) {
    return request({
        url: `/problems/${id}`,
        method: 'put',
        data
    })
}

export function deleteProblem(id) {
    return request({
        url: `/problems/${id}`,
        method: 'delete'
    })
}

export function uploadTestCases(id, formData) {
    return request({
        url: `/problems/${id}/upload_files`,
        method: 'post',
        data: formData,
        timeout: 300000,
        headers: {'Content-Type': 'multipart/form-data'}
    })
}

export function getTestCaseSummary(id) {
    return request({
        url: `/problems/${id}/test_cases/summary`,
        method: 'get'
    })
}

export function downloadTestCases(id) {
    return request({
        url: `/problems/${id}/test_cases`,
        method: 'get',
        responseType: 'blob'
    })
}

export function deleteAllTestCases(id) {
    return request({
        url: `/problems/${id}/test_cases`,
        method: 'delete'
    })
}
