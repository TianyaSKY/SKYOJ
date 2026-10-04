import type { ExamDetailResponse, ExamListResponse, ExamProblemStatusResponse } from '@/types/exam'
import type { ProblemListResponse } from '@/types/problem'

// 测试样例使用完整协议结构，个别用例只覆盖与该行为有关的字段。
export function examResponse(id: number, fields: Partial<ExamDetailResponse & ExamListResponse> = {}): ExamDetailResponse & ExamListResponse {
  return {
    id, title: `考试${id}`, description: '', start_time: '2090-06-15T10:00:00', end_time: '2090-06-15T11:00:00',
    contest_type: 'icpc', freeze_minutes: null, is_visible: true, created_by: 1,
    has_password: false, problem_count: 0, submission_count: 0, problems: [], ...fields,
  }
}
export function examStatus(fields: Partial<ExamProblemStatusResponse>): ExamProblemStatusResponse {
  return { problem_id: 1, display_id: null, title: '题目', max_score: 100, status: 'Accepted', current_score: 0, last_submitted_at: null, ...fields }
}
export function problemResponse(fields: Partial<ProblemListResponse>): ProblemListResponse {
  return {
    id: 1, title: '题目', type: 'acm', language: 'python', time_limit: 1000, memory_limit: 128,
    test_case_status: 'ready', test_case_count: 1, test_case_valid_count: 1, ...fields,
  }
}
export function deferred<T>() {
  let resolve!: (value: T) => void, reject!: (reason: unknown) => void
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
