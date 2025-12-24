import request from '@/utils/request'

/**
 * 获取公开数据集列表
 * @param {object} params 查询参数
 */
export function getDatasetList(params) {
    return request({
        url: '/datasets',
        method: 'get',
        params
    })
}

/**
 * 上传新的数据集文件
 * @param {FormData} data 包含文件和元数据的表单数据
 */
export function uploadDataset(data) {
    return request({
        url: '/datasets',
        method: 'post',
        data,
        headers: {'Content-Type': 'multipart/form-data'}
    })
}

/**
 * 删除数据集
 * @param {number} id 数据集ID
 */
export function deleteDataset(id) {
    return request({
        url: `/datasets/${id}`,
        method: 'delete'
    })
}
