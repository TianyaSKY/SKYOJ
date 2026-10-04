import request from '@/utils/request'
import type { TagResponse } from '@/types/community'

export interface AttachTagBody {
  tag_id: number
  approved: boolean
}

export function getTags(): Promise<TagResponse[]> {
  return request<TagResponse[]>({ url: '/tags', method: 'get' })
}

export function getProblemTags(problemId: number): Promise<TagResponse[]> {
  return request<TagResponse[]>({ url: `/tags/problems/${problemId}`, method: 'get' })
}

export function attachProblemTag(problemId: number, data: AttachTagBody): Promise<void> {
  return request<void>({ url: `/tags/problems/${problemId}/attach`, method: 'post', data })
}

export function detachProblemTag(problemId: number, tagId: number): Promise<void> {
  return request<void>({ url: `/tags/problems/${problemId}/${tagId}`, method: 'delete' })
}
