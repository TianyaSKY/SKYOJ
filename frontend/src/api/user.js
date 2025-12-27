import request from '@/utils/request'

/**
 * Get the submission history for the currently logged-in user.
 * The user is identified by the token sent in the request header.
 */
export function getUserSubmissions(userId = null) {
    return request({
        url: userId ? `/user/${userId}/submissions` : '/user/submissions',
        method: 'get'
    })
}

export function register(data) {
    return request({
        url: '/auth/register',
        method: 'post',
        data
    })
}

export function getUserProfile(userId) {
    return request({
        url: `/user/${userId}/profile`,
        method: 'get'
    })
}

export function getAllUsers() {
    return request({
        url: '/user/all',
        method: 'get'
    })
}

export function uploadAvatar(formData) {
    return request({
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
export function getAvatarUrl(filename) {
    return `/user/avatars/${filename}`
}
