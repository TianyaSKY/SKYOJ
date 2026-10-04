import type * as Dataset from '@/types/dataset'
import type { MessageResponse, PaginationQuery } from '@/types/common'
import request from '@/utils/request'

/**
 * 获取公开数据集列表
 * @param {object} params 查询参数
 */
export function getDatasetList(params?: PaginationQuery): Promise<Dataset.DatasetResponse[] | Dataset.PaginatedDatasetsResponse | Dataset.LegacyDatasetListResponse> {
    return request<Dataset.DatasetResponse[] | Dataset.PaginatedDatasetsResponse | Dataset.LegacyDatasetListResponse>({
        url: '/datasets',
        method: 'get',
        params
    })
}

/**
 * 上传新的数据集文件
 * @param {FormData} data 包含文件和元数据的表单数据
 */
export function uploadDataset(data: FormData): Promise<Dataset.UploadDatasetResponse> {
    return request<Dataset.UploadDatasetResponse>({
        url: '/datasets',
        method: 'post',
        data,
        timeout: 300000,
        headers: {'Content-Type': 'multipart/form-data'}
    })
}

/**
 * 删除数据集
 * @param {number} id 数据集ID
 */
export function deleteDataset(id: number): Promise<MessageResponse> {
    return request<MessageResponse>({
        url: `/datasets/${id}`,
        method: 'delete'
    })
}

/**
 * 下载数据集（携带登录态，避免把 token 放进 URL）
 * @param {number} id 数据集ID
 */
export function downloadDataset(id: number): Promise<Blob> {
    return request<Blob>({
        url: `/datasets/${id}/download`,
        method: 'get',
        responseType: 'blob',
        timeout: 300000
    })
}
