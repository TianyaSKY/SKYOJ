import request from '@/utils/request'
import type { PaginationQuery } from '@/types/common'
import type {
  SolutionListResponse,
  SolutionDetailResponse,
  ToggleLikeResponse,
  ToggleFavoriteResponse,
  CommentListResponse,
  CommentResponse,
} from '@/types/community'
import type { SolutionFormInput, CommentFormInput } from '@/schemas/community'

export function getSolutions(
  problemId: number,
  params: PaginationQuery,
): Promise<SolutionListResponse> {
  return request<SolutionListResponse>({
    url: `/problems/${problemId}/solutions`,
    method: 'get',
    params,
  })
}

export function createSolution(
  problemId: number,
  data: SolutionFormInput,
): Promise<SolutionDetailResponse> {
  return request<SolutionDetailResponse>({
    url: `/problems/${problemId}/solutions`,
    method: 'post',
    data,
  })
}

export function updateSolution(
  solutionId: number,
  data: SolutionFormInput,
): Promise<SolutionDetailResponse> {
  return request<SolutionDetailResponse>({
    url: `/problems/solutions/${solutionId}`,
    method: 'put',
    data,
  })
}

// 后端以 204 返回，无响应正文。
export function hideSolution(solutionId: number): Promise<void> {
  return request<void>({ url: `/problems/solutions/${solutionId}`, method: 'delete' })
}

export function toggleSolutionLike(solutionId: number): Promise<ToggleLikeResponse> {
  return request<ToggleLikeResponse>({
    url: `/problems/solutions/${solutionId}/like`,
    method: 'post',
  })
}

export function toggleSolutionFavorite(solutionId: number): Promise<ToggleFavoriteResponse> {
  return request<ToggleFavoriteResponse>({
    url: `/problems/solutions/${solutionId}/favorite`,
    method: 'post',
  })
}

export function getComments(
  solutionId: number,
  params: PaginationQuery,
): Promise<CommentListResponse> {
  return request<CommentListResponse>({
    url: `/problems/solutions/${solutionId}/comments`,
    method: 'get',
    params,
  })
}

export function createComment(
  solutionId: number,
  data: CommentFormInput,
): Promise<CommentResponse> {
  return request<CommentResponse>({
    url: `/problems/solutions/${solutionId}/comments`,
    method: 'post',
    data,
  })
}

export function deleteComment(commentId: number): Promise<void> {
  return request<void>({ url: `/problems/comments/${commentId}`, method: 'delete' })
}
