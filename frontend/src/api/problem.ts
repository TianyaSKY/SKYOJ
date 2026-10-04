import type * as Problem from '@/types/problem'
import type * as Submission from '@/types/submission'
import type { CreateProblemInput, UpdateProblemInput } from '@/schemas/problem'
import type { MessageResponse } from '@/types/common'
import request from '@/utils/request'

export function getProblemList(params?: Problem.ProblemQuery): Promise<Problem.ProblemListResponse[] | Problem.PaginatedProblemsResponse> {
    return request<Problem.ProblemListResponse[] | Problem.PaginatedProblemsResponse>({
        url: '/problems/',
        method: 'get',
        params
    })
}

export function searchProblems(params?: Problem.SearchQuery): Promise<Problem.SearchProblemResponse[]> {
    return request<Problem.SearchProblemResponse[]>({
        url: '/search',
        method: 'get',
        params
    })
}

export function getProblemDetail(id: number): Promise<Problem.ProblemDetailResponse> {
    return request<Problem.ProblemDetailResponse>({
        url: `/problems/${id}`,
        method: 'get'
    })
}

export function submitSolution(data: Submission.SubmitCodeBody | FormData): Promise<Submission.SubmitCodeResponse> {
    const isFormData = data instanceof FormData
    return request<Submission.SubmitCodeResponse>({
        url: '/submissions/submit',
        method: 'post',
        data,
        timeout: 120000,
        headers: isFormData ? {'Content-Type': 'multipart/form-data'} : undefined
    })
}

export function getSubmissionDetail(id: number): Promise<Submission.SubmissionDetailResponse> {
    return request<Submission.SubmissionDetailResponse>({
        url: `/submissions/${id}`,
        method: 'get'
    })
}

// --- Admin Functions ---

export function createProblem(data: CreateProblemInput): Promise<Problem.CreateProblemResponse> {
    return request<Problem.CreateProblemResponse>({
        url: '/problems/',
        method: 'post',
        data
    })
}

export function updateProblem(id: number, data: UpdateProblemInput): Promise<MessageResponse> {
    return request<MessageResponse>({
        url: `/problems/${id}`,
        method: 'put',
        data
    })
}

export function deleteProblem(id: number): Promise<MessageResponse> {
    return request<MessageResponse>({
        url: `/problems/${id}`,
        method: 'delete'
    })
}

export function uploadTestCases(id: number, formData: FormData): Promise<Problem.UploadTestCasesResponse> {
    return request<Problem.UploadTestCasesResponse>({
        url: `/problems/${id}/upload_files`,
        method: 'post',
        data: formData,
        timeout: 300000,
        headers: {'Content-Type': 'multipart/form-data'}
    })
}

export function getTestCaseSummary(id: number): Promise<Problem.TestCaseSummaryResponse> {
    return request<Problem.TestCaseSummaryResponse>({
        url: `/problems/${id}/test_cases/summary`,
        method: 'get'
    })
}

export function downloadTestCases(id: number): Promise<Blob> {
    return request<Blob>({
        url: `/problems/${id}/test_cases`,
        method: 'get',
        responseType: 'blob'
    })
}

export function deleteAllTestCases(id: number): Promise<MessageResponse> {
    return request<MessageResponse>({
        url: `/problems/${id}/test_cases`,
        method: 'delete'
    })
}
