import type * as Exam from '@/types/exam'
import type * as Submission from '@/types/submission'
import type { CreateExamInput, UpdateExamInput } from '@/schemas/exam'
import type { MessageResponse } from '@/types/common'
import request from '@/utils/request'

export function getExamList(params?: Record<string, never>): Promise<Exam.ExamListResponse[]> {
  return request<Exam.ExamListResponse[]>({
    url: '/exams/',
    method: 'get',
    params,
  })
}

export function getExamDetail(id: number): Promise<Exam.ExamDetailResponse> {
  return request<Exam.ExamDetailResponse>({
    url: `/exams/${id}`,
    method: 'get',
  })
}

export function createExam(data: CreateExamInput): Promise<Exam.ExamResponse> {
  return request<Exam.ExamResponse>({
    url: '/exams/',
    method: 'post',
    data,
  })
}

export function updateExam(id: number, data: UpdateExamInput): Promise<Exam.ExamResponse> {
  return request<Exam.ExamResponse>({
    url: `/exams/${id}`,
    method: 'put',
    data,
  })
}

export function deleteExam(id: number): Promise<MessageResponse> {
  return request<MessageResponse>({
    url: `/exams/${id}`,
    method: 'delete',
  })
}

export function addExamProblem(
  examId: number,
  data: Exam.AddExamProblem,
): Promise<MessageResponse> {
  return request<MessageResponse>({
    url: `/exams/${examId}/problems`,
    method: 'post',
    data,
  })
}

export function removeExamProblem(examId: number, problemId: number): Promise<MessageResponse> {
  return request<MessageResponse>({
    url: `/exams/${examId}/problems/${problemId}`,
    method: 'delete',
  })
}

export function verifyExamPassword(id: number, password?: string | null): Promise<MessageResponse> {
  return request<MessageResponse>({
    url: `/exams/${id}/verify`,
    method: 'post',
    data: { password },
  })
}

export function enterExam(id: number, password?: string | null): Promise<Exam.EnterExamResponse> {
  return request<Exam.EnterExamResponse>({
    url: `/exams/${id}/enter`,
    method: 'post',
    data: { password },
  })
}

export function exitExam(): Promise<Exam.ExamTokenResponse> {
  return request<Exam.ExamTokenResponse>({
    url: '/exams/exit',
    method: 'post',
  })
}

export function getMyExamStatus(examId?: number | null): Promise<Exam.ExamProblemStatusResponse[]> {
  return request<Exam.ExamProblemStatusResponse[]>({
    url: '/exams/status',
    method: 'get',
    params: examId == null ? undefined : { exam_id: examId },
  })
}

/**
 * 导出考试成绩 (CSV)
 */
export function exportExamScores(id: number): Promise<Blob> {
  return request<Blob>({
    url: `/exams/${id}/export_scores`,
    method: 'get',
    responseType: 'blob', // 重要：处理文件流
  })
}

/**
 * 获取考试监控数据（教师端）
 */
export function getExamMonitor(id: number): Promise<Exam.MonitorResponse> {
  return request<Exam.MonitorResponse>({
    url: `/exams/${id}/monitor`,
    method: 'get',
  })
}

/**
 * 获取考试排名（滚榜数据）
 */
export function getExamRank(id: number): Promise<Exam.RankResponse> {
  return request<Exam.RankResponse>({
    url: `/exams/${id}/rank`,
    method: 'get',
  })
}

/**
 * 获取特定提交的详细信息（包含代码）
 */
export function getSubmissionDetail(id: number): Promise<Submission.SubmissionDetailResponse> {
  return request<Submission.SubmissionDetailResponse>({
    url: `/submissions/${id}`,
    method: 'get',
  })
}
