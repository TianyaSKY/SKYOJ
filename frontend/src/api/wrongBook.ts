import request from '@/utils/request'
import type { PaginationQuery } from '@/types/common'
import type {
  WrongBookStatsResponse,
  WrongBookListResponse,
  ToggleReviewResponse,
} from '@/types/wrongBook'

export function getWrongBookStats(): Promise<WrongBookStatsResponse> {
  return request<WrongBookStatsResponse>({ url: '/wrong-book/stats', method: 'get' })
}

export function getWrongBook(params: PaginationQuery): Promise<WrongBookListResponse> {
  return request<WrongBookListResponse>({ url: '/wrong-book/', method: 'get', params })
}

export function toggleWrongBookReview(entryId: number): Promise<ToggleReviewResponse> {
  return request<ToggleReviewResponse>({
    url: `/wrong-book/${entryId}/toggle-review`,
    method: 'post',
  })
}
