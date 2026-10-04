import type * as User from '@/types/user'
import type { RegisterInput } from '@/schemas/auth'
import type { MessageResponse } from '@/types/common'
import request from '@/utils/request'

/**
 * Get the submission history for the currently logged-in user.
 * The user is identified by the token sent in the request header.
 */
export function getUserSubmissions(userId: number | null = null): Promise<User.UserSubmissionResponse[]> {
    return request<User.UserSubmissionResponse[]>({
        url: userId ? `/user/${userId}/submissions` : '/user/submissions',
        method: 'get'
    })
}

export function register(data: RegisterInput): Promise<MessageResponse> {
    return request<MessageResponse>({
        url: '/auth/register',
        method: 'post',
        data
    })
}

export function getUserProfile(userId: number): Promise<User.UserProfileResponse> {
    return request<User.UserProfileResponse>({
        url: `/user/${userId}/profile`,
        method: 'get'
    })
}

export function getAllUsers(): Promise<User.UserProfileResponse[]> {
    return request<User.UserProfileResponse[]>({
        url: '/user/all',
        method: 'get'
    })
}

export function uploadAvatar(formData: FormData): Promise<User.UploadAvatarResponse> {
    return request<User.UploadAvatarResponse>({
        url: '/user/avatar',
        method: 'post',
        data: formData,
        headers: {
            'Content-Type': 'multipart/form-data'
        }
    })
}

/**
 * 获取头像文件
 * @param {string} filename 头像文件名
 */
export function getAvatarUrl(filename: string): string {
    return `/user/avatars/${filename}`
}
