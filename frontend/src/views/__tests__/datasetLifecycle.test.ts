import type { DatasetResponse, PaginatedDatasetsResponse, UploadDatasetResponse } from '@/types/dataset'
import type { UploadFile, UploadFiles, UploadRawFile } from 'element-plus'
import type { MessageResponse } from '@/types/common'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
vi.mock('@/stores/user', () => ({ useUserStore: () => ({ user: { role: 'teacher' } }) }))
vi.mock('@/api/dataset', () => ({ getDatasetList: vi.fn(), uploadDataset: vi.fn(), deleteDataset: vi.fn(), downloadDataset: vi.fn() }))
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn(), success: vi.fn(), warning: vi.fn() } }))
import DatasetListView from '../DatasetListView.vue'
import { getDatasetList, uploadDataset, deleteDataset, downloadDataset } from '@/api/dataset'
import { ElMessage } from 'element-plus'
let wrapper: ReturnType<typeof mountPage> | undefined
const dataset = (value: Partial<DatasetResponse>): DatasetResponse => ({
  id: 1, name: '数据集', description: null, uploader: 'teacher', file_size: '4 B', created_at: null,
  download_url: '/datasets/1/download', status: 'ready', ...value,
})
const page = (value: { datasets: DatasetResponse[]; total: number }): PaginatedDatasetsResponse => ({ page: 1, page_size: 20, ...value })
const uploaded: UploadDatasetResponse = { message: '上传成功', dataset: dataset({}) }
const deleted: MessageResponse = { message: '删除成功' }
function current() {
  if (!wrapper) throw new Error('数据集页面未挂载')
  return wrapper
}
// 测试可访问 setup 状态，公共组件类型不公开这些内部字段。
function setupState() {
  return current().vm as unknown as {
    uploadForm: { name: string; description: string; file: File | null }; uploading: boolean; uploadDialogVisible: boolean;
    currentPage: number; pageSize: number; datasets: DatasetResponse[]; loading: boolean;
    openUpload(): void; handleFileChange(file: UploadFile): void; handleFileRemove(file: UploadFile, files: UploadFiles): void;
    handleUpload(): Promise<void>; handleCurrentChange(page: number): Promise<void>; handleSizeChange(size: number): Promise<void>;
    fetchDatasets(): Promise<void>; handleDelete(row: Pick<DatasetResponse, 'id'>): Promise<void>;
    handleDownload(row: Pick<DatasetResponse, 'id' | 'status'>): Promise<void>; canDownload(row: Partial<Pick<DatasetResponse, 'status'>>): boolean;
  }
}
function deferred<T>() {
  let resolve!: (value: T) => void, reject!: (reason: unknown) => void
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
function mountPage() {
  const mounted = shallowMount(DatasetListView, { global: {
    directives: { loading: () => {} },
    stubs: Object.fromEntries(['el-card','el-button','el-table','el-table-column','el-button-group','el-popconfirm','el-pagination','el-dialog','el-form','el-form-item','el-input','el-upload'].map(name => [name,true])),
  } })
  wrapper = mounted
  return mounted
}
function selectFile(name = 'data.csv') {
  const file: UploadRawFile = Object.assign(new File(['data'], name), { uid: 1 })
  setupState().uploadForm.name = name
  setupState().handleFileChange({ raw: file, size: file.size, name: file.name, uid: file.uid, status: 'ready' })
  return file
}
beforeEach(() => {
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
  vi.resetAllMocks()
  vi.mocked(getDatasetList).mockResolvedValue(page({ datasets: [], total: 0 }))
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined; vi.clearAllTimers(); vi.useRealTimers() })
it('移除已选文件后不能继续上传该文件，重新选择后上传新文件', async () => {
  mountPage(); await flushPromises()
  setupState().openUpload()
  const removed = selectFile()
  setupState().handleFileRemove({ raw: removed, name: removed.name, uid: removed.uid, status: 'ready' }, [])
  await setupState().handleUpload()
  expect(uploadDataset).not.toHaveBeenCalled()
  expect(ElMessage.warning).toHaveBeenCalled()
  const replacement = selectFile('replacement.csv')
  vi.mocked(uploadDataset).mockResolvedValue(uploaded)
  await setupState().handleUpload()
  expect(vi.mocked(uploadDataset).mock.calls[0][0].get('file')).toMatchObject({ name: replacement.name, size: replacement.size })
})
it('上传期间重复点击只发送一次请求', async () => {
  const upload = deferred<UploadDatasetResponse>()
  vi.mocked(uploadDataset).mockReturnValue(upload.promise)
  mountPage(); await flushPromises()
  setupState().openUpload(); selectFile()
  const first = setupState().handleUpload()
  await setupState().handleUpload()
  expect(uploadDataset).toHaveBeenCalledOnce()
  upload.resolve(uploaded); await first
  expect(setupState().uploading).toBe(false)
})
it('旧上传成功不能关闭新窗口或清除新文件', async () => {
  const upload = deferred<UploadDatasetResponse>()
  vi.mocked(uploadDataset).mockReturnValue(upload.promise)
  mountPage(); await flushPromises()
  setupState().openUpload(); selectFile()
  const first = setupState().handleUpload()
  setupState().uploadDialogVisible = false
  setupState().openUpload(); const file = selectFile('new.csv')
  upload.resolve(uploaded); await first
  expect(setupState().uploadDialogVisible).toBe(true)
  expect(setupState().uploadForm.file).toMatchObject({ name: file.name, size: file.size })
  expect(ElMessage.success).not.toHaveBeenCalled()
  await vi.advanceTimersByTimeAsync(1000)
  expect(getDatasetList).toHaveBeenCalledTimes(2)
})
it('旧上传失败不能解除新窗口的上传状态或弹出旧错误', async () => {
  const old = deferred<UploadDatasetResponse>(), current = deferred<UploadDatasetResponse>()
  vi.mocked(uploadDataset).mockReturnValueOnce(old.promise).mockReturnValueOnce(current.promise)
  mountPage(); await flushPromises()
  setupState().openUpload(); selectFile()
  const first = setupState().handleUpload()
  setupState().uploadDialogVisible = false
  setupState().openUpload(); selectFile('new.csv')
  const second = setupState().handleUpload()
  old.reject(new Error('old failed')); await first
  expect(setupState().uploading).toBe(true)
  expect(ElMessage.error).not.toHaveBeenCalled()
  current.resolve(uploaded); await second
  expect(setupState().uploading).toBe(false)
})
it.each([true, false])('卸载后旧上传完成或刷新计时器不再查询列表（响应先完成：%s）', async resolveFirst => {
  const upload = deferred<UploadDatasetResponse>()
  vi.mocked(uploadDataset).mockReturnValue(upload.promise)
  mountPage(); await flushPromises()
  setupState().openUpload(); selectFile()
  const first = setupState().handleUpload()
  if (resolveFirst) { upload.resolve(uploaded); await first }
  current().unmount(); wrapper = undefined
  if (!resolveFirst) { upload.resolve(uploaded); await first }
  await vi.advanceTimersByTimeAsync(2000)
  expect(getDatasetList).toHaveBeenCalledOnce()
})

it('翻页失败保留原页码和内容，允许重试', async () => {
  vi.mocked(getDatasetList).mockResolvedValueOnce(page({ datasets: [dataset({ id: 1 })], total: 21 }))
  mountPage(); await flushPromises()
  vi.mocked(getDatasetList).mockRejectedValueOnce(new Error('page failed'))
  await setupState().handleCurrentChange(2)
  expect(setupState().currentPage).toBe(1)
  expect(setupState().datasets).toEqual([dataset({ id: 1 })])
  expect(setupState().loading).toBe(false)
  vi.mocked(getDatasetList).mockResolvedValueOnce(page({ datasets: [dataset({ id: 21 })], total: 21 }))
  await setupState().handleCurrentChange(2)
  expect(setupState().currentPage).toBe(2)
  expect(setupState().datasets).toEqual([dataset({ id: 21 })])
})
it('调整每页数量失败时保留此前分页参数', async () => {
  mountPage(); await flushPromises()
  vi.mocked(getDatasetList).mockRejectedValueOnce(new Error('size failed'))
  await setupState().handleSizeChange(50)
  expect(setupState().pageSize).toBe(20)
  expect(setupState().currentPage).toBe(1)
  await setupState().fetchDatasets()
  expect(getDatasetList).toHaveBeenLastCalledWith({ page: 1, page_size: 20 })
})
it('删除末页最后一条记录后自动回退到有效页', async () => {
  vi.mocked(getDatasetList).mockResolvedValueOnce(page({ datasets: [dataset({ id: 1 })], total: 21 }))
  mountPage(); await flushPromises()
  vi.mocked(getDatasetList).mockResolvedValueOnce(page({ datasets: [dataset({ id: 21 })], total: 21 }))
  await setupState().handleCurrentChange(2)
  vi.mocked(deleteDataset).mockResolvedValue(deleted)
  vi.mocked(getDatasetList).mockResolvedValueOnce(page({ datasets: [], total: 20 }))
    .mockResolvedValueOnce(page({ datasets: [dataset({ id: 1 })], total: 20 }))
  await setupState().handleDelete(dataset({ id: 21 }))
  expect(setupState().currentPage).toBe(1)
  expect(setupState().datasets).toEqual([dataset({ id: 1 })])
  expect(getDatasetList).toHaveBeenLastCalledWith({ page: 1, page_size: 20 })
})
it('重复删除只发送一次，卸载后的删除响应不刷新页面或显示提示', async () => {
  const deletion = deferred<MessageResponse>()
  vi.mocked(deleteDataset).mockReturnValue(deletion.promise)
  mountPage(); await flushPromises()
  const first = setupState().handleDelete(dataset({ id: 1 }))
  await setupState().handleDelete(dataset({ id: 1 }))
  expect(deleteDataset).toHaveBeenCalledOnce()
  current().unmount(); wrapper = undefined
  deletion.resolve(deleted); await first
  expect(getDatasetList).toHaveBeenCalledOnce()
  expect(ElMessage.success).not.toHaveBeenCalled()
})
it('旧翻页响应不能覆盖后来成功的页码和内容', async () => {
  mountPage(); await flushPromises()
  const old = deferred<PaginatedDatasetsResponse>()
  vi.mocked(getDatasetList).mockReturnValueOnce(old.promise).mockResolvedValueOnce(page({ datasets: [dataset({ id: 41 })], total: 41 }))
  const first = setupState().handleCurrentChange(2)
  await setupState().handleCurrentChange(3)
  old.resolve(page({ datasets: [dataset({ id: 21 })], total: 41 })); await first
  expect(setupState().currentPage).toBe(3)
  expect(setupState().datasets).toEqual([dataset({ id: 41 })])
})

it('待处理数据集继续刷新，进入 ready 或 failed 后停止查询', async () => {
  vi.mocked(getDatasetList).mockResolvedValueOnce(page({ datasets: [dataset({ id: 1, status: 'pending' })], total: 1 }))
    .mockResolvedValueOnce(page({ datasets: [dataset({ id: 1, status: 'pending' })], total: 1 }))
    .mockResolvedValueOnce(page({ datasets: [dataset({ id: 1, status: 'ready' }), dataset({ id: 2, status: 'failed' })], total: 2 }))
  mountPage(); await flushPromises()
  await vi.advanceTimersByTimeAsync(4000)
  expect(getDatasetList).toHaveBeenCalledTimes(3)
  expect(setupState().datasets[0].status).toBe('ready')
  await vi.advanceTimersByTimeAsync(6000)
  expect(getDatasetList).toHaveBeenCalledTimes(3)
})
it('待处理列表的慢查询不会重叠，卸载后不重新安排刷新', async () => {
  const poll = deferred<PaginatedDatasetsResponse>()
  vi.mocked(getDatasetList).mockResolvedValueOnce(page({ datasets: [dataset({ id: 1, status: 'pending' })], total: 1 })).mockReturnValueOnce(poll.promise)
  mountPage(); await flushPromises()
  await vi.advanceTimersByTimeAsync(10000)
  expect(getDatasetList).toHaveBeenCalledTimes(2)
  current().unmount(); wrapper = undefined
  poll.resolve(page({ datasets: [dataset({ id: 1, status: 'pending' })], total: 1 })); await flushPromises()
  await vi.advanceTimersByTimeAsync(4000)
  expect(getDatasetList).toHaveBeenCalledTimes(2)
})
it('轮询失败后停止自动请求，手动刷新可恢复查询', async () => {
  vi.mocked(getDatasetList).mockResolvedValueOnce(page({ datasets: [dataset({ id: 1, status: 'pending' })], total: 1 })).mockRejectedValueOnce(new Error('offline'))
  mountPage(); await flushPromises()
  await vi.advanceTimersByTimeAsync(6000)
  expect(getDatasetList).toHaveBeenCalledTimes(2)
  expect(ElMessage.error).toHaveBeenCalledWith('获取数据集列表失败')
  vi.mocked(getDatasetList).mockResolvedValueOnce(page({ datasets: [dataset({ id: 1, status: 'ready' })], total: 1 }))
  await setupState().fetchDatasets()
  expect(setupState().datasets[0].status).toBe('ready')
})
it('未完成或失败的数据集不能发起下载，兼容旧接口没有状态的记录', async () => {
  mountPage(); await flushPromises()
  await setupState().handleDownload(dataset({ id: 1, status: 'pending' }))
  await setupState().handleDownload(dataset({ id: 2, status: 'failed' }))
  expect(downloadDataset).not.toHaveBeenCalled()
  expect(setupState().canDownload({ status: 'ready' })).toBe(true)
  expect(setupState().canDownload({})).toBe(true)
})
