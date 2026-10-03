import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
vi.mock('@/stores/user', () => ({ useUserStore: () => ({ user: { role: 'teacher' } }) }))
vi.mock('@/api/dataset', () => ({ getDatasetList: vi.fn(), uploadDataset: vi.fn(), deleteDataset: vi.fn(), downloadDataset: vi.fn() }))
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn(), success: vi.fn(), warning: vi.fn() } }))
import DatasetListView from '../DatasetListView.vue'
import { getDatasetList, uploadDataset, deleteDataset, downloadDataset } from '@/api/dataset'
import { ElMessage } from 'element-plus'
let wrapper
function deferred() {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
function mountPage() {
  wrapper = shallowMount(DatasetListView, { global: {
    directives: { loading: () => {} },
    stubs: Object.fromEntries(['el-card','el-button','el-table','el-table-column','el-button-group','el-popconfirm','el-pagination','el-dialog','el-form','el-form-item','el-input','el-upload'].map(name => [name,true])),
  } })
}
function selectFile(name = 'data.csv') {
  const file = new File(['data'], name)
  wrapper.vm.uploadForm.name = name
  wrapper.vm.handleFileChange({ raw: file, size: file.size })
  return file
}
beforeEach(() => {
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
  vi.resetAllMocks()
  getDatasetList.mockResolvedValue({ datasets: [], total: 0 })
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined; vi.clearAllTimers(); vi.useRealTimers() })
it('移除已选文件后不能继续上传该文件，重新选择后上传新文件', async () => {
  mountPage(); await flushPromises()
  wrapper.vm.openUpload()
  const removed = selectFile()
  wrapper.vm.handleFileRemove({ raw: removed }, [])
  await wrapper.vm.handleUpload()
  expect(uploadDataset).not.toHaveBeenCalled()
  expect(ElMessage.warning).toHaveBeenCalled()
  const replacement = selectFile('replacement.csv')
  uploadDataset.mockResolvedValue({})
  await wrapper.vm.handleUpload()
  expect(uploadDataset.mock.calls[0][0].get('file')).toMatchObject({ name: replacement.name, size: replacement.size })
})
it('上传期间重复点击只发送一次请求', async () => {
  const upload = deferred()
  uploadDataset.mockReturnValue(upload.promise)
  mountPage(); await flushPromises()
  wrapper.vm.openUpload(); selectFile()
  const first = wrapper.vm.handleUpload()
  await wrapper.vm.handleUpload()
  expect(uploadDataset).toHaveBeenCalledOnce()
  upload.resolve({}); await first
  expect(wrapper.vm.uploading).toBe(false)
})
it('旧上传成功不能关闭新窗口或清除新文件', async () => {
  const upload = deferred()
  uploadDataset.mockReturnValue(upload.promise)
  mountPage(); await flushPromises()
  wrapper.vm.openUpload(); selectFile()
  const first = wrapper.vm.handleUpload()
  wrapper.vm.uploadDialogVisible = false
  wrapper.vm.openUpload(); const file = selectFile('new.csv')
  upload.resolve({}); await first
  expect(wrapper.vm.uploadDialogVisible).toBe(true)
  expect(wrapper.vm.uploadForm.file).toMatchObject({ name: file.name, size: file.size })
  expect(ElMessage.success).not.toHaveBeenCalled()
  await vi.advanceTimersByTimeAsync(1000)
  expect(getDatasetList).toHaveBeenCalledTimes(2)
})
it('旧上传失败不能解除新窗口的上传状态或弹出旧错误', async () => {
  const old = deferred(), current = deferred()
  uploadDataset.mockReturnValueOnce(old.promise).mockReturnValueOnce(current.promise)
  mountPage(); await flushPromises()
  wrapper.vm.openUpload(); selectFile()
  const first = wrapper.vm.handleUpload()
  wrapper.vm.uploadDialogVisible = false
  wrapper.vm.openUpload(); selectFile('new.csv')
  const second = wrapper.vm.handleUpload()
  old.reject(new Error('old failed')); await first
  expect(wrapper.vm.uploading).toBe(true)
  expect(ElMessage.error).not.toHaveBeenCalled()
  current.resolve({}); await second
  expect(wrapper.vm.uploading).toBe(false)
})
it.each([true, false])('卸载后旧上传完成或刷新计时器不再查询列表（响应先完成：%s）', async resolveFirst => {
  const upload = deferred()
  uploadDataset.mockReturnValue(upload.promise)
  mountPage(); await flushPromises()
  wrapper.vm.openUpload(); selectFile()
  const first = wrapper.vm.handleUpload()
  if (resolveFirst) { upload.resolve({}); await first }
  wrapper.unmount(); wrapper = undefined
  if (!resolveFirst) { upload.resolve({}); await first }
  await vi.advanceTimersByTimeAsync(2000)
  expect(getDatasetList).toHaveBeenCalledOnce()
})

it('翻页失败保留原页码和内容，允许重试', async () => {
  getDatasetList.mockResolvedValueOnce({ datasets: [{ id: 1 }], total: 21 })
  mountPage(); await flushPromises()
  getDatasetList.mockRejectedValueOnce(new Error('page failed'))
  await wrapper.vm.handleCurrentChange(2)
  expect(wrapper.vm.currentPage).toBe(1)
  expect(wrapper.vm.datasets).toEqual([{ id: 1 }])
  expect(wrapper.vm.loading).toBe(false)
  getDatasetList.mockResolvedValueOnce({ datasets: [{ id: 21 }], total: 21 })
  await wrapper.vm.handleCurrentChange(2)
  expect(wrapper.vm.currentPage).toBe(2)
  expect(wrapper.vm.datasets).toEqual([{ id: 21 }])
})
it('调整每页数量失败时保留此前分页参数', async () => {
  mountPage(); await flushPromises()
  getDatasetList.mockRejectedValueOnce(new Error('size failed'))
  await wrapper.vm.handleSizeChange(50)
  expect(wrapper.vm.pageSize).toBe(20)
  expect(wrapper.vm.currentPage).toBe(1)
  await wrapper.vm.fetchDatasets()
  expect(getDatasetList).toHaveBeenLastCalledWith({ page: 1, page_size: 20 })
})
it('删除末页最后一条记录后自动回退到有效页', async () => {
  getDatasetList.mockResolvedValueOnce({ datasets: [{ id: 1 }], total: 21 })
  mountPage(); await flushPromises()
  getDatasetList.mockResolvedValueOnce({ datasets: [{ id: 21 }], total: 21 })
  await wrapper.vm.handleCurrentChange(2)
  deleteDataset.mockResolvedValue({})
  getDatasetList.mockResolvedValueOnce({ datasets: [], total: 20 })
    .mockResolvedValueOnce({ datasets: [{ id: 1 }], total: 20 })
  await wrapper.vm.handleDelete({ id: 21 })
  expect(wrapper.vm.currentPage).toBe(1)
  expect(wrapper.vm.datasets).toEqual([{ id: 1 }])
  expect(getDatasetList).toHaveBeenLastCalledWith({ page: 1, page_size: 20 })
})
it('重复删除只发送一次，卸载后的删除响应不刷新页面或显示提示', async () => {
  const deletion = deferred()
  deleteDataset.mockReturnValue(deletion.promise)
  mountPage(); await flushPromises()
  const first = wrapper.vm.handleDelete({ id: 1 })
  await wrapper.vm.handleDelete({ id: 1 })
  expect(deleteDataset).toHaveBeenCalledOnce()
  wrapper.unmount(); wrapper = undefined
  deletion.resolve({}); await first
  expect(getDatasetList).toHaveBeenCalledOnce()
  expect(ElMessage.success).not.toHaveBeenCalled()
})
it('旧翻页响应不能覆盖后来成功的页码和内容', async () => {
  mountPage(); await flushPromises()
  const old = deferred()
  getDatasetList.mockReturnValueOnce(old.promise).mockResolvedValueOnce({ datasets: [{ id: 41 }], total: 41 })
  const first = wrapper.vm.handleCurrentChange(2)
  await wrapper.vm.handleCurrentChange(3)
  old.resolve({ datasets: [{ id: 21 }], total: 41 }); await first
  expect(wrapper.vm.currentPage).toBe(3)
  expect(wrapper.vm.datasets).toEqual([{ id: 41 }])
})

it('待处理数据集继续刷新，进入 ready 或 failed 后停止查询', async () => {
  getDatasetList.mockResolvedValueOnce({ datasets: [{ id: 1, status: 'pending' }], total: 1 })
    .mockResolvedValueOnce({ datasets: [{ id: 1, status: 'pending' }], total: 1 })
    .mockResolvedValueOnce({ datasets: [{ id: 1, status: 'ready' }, { id: 2, status: 'failed' }], total: 2 })
  mountPage(); await flushPromises()
  await vi.advanceTimersByTimeAsync(4000)
  expect(getDatasetList).toHaveBeenCalledTimes(3)
  expect(wrapper.vm.datasets[0].status).toBe('ready')
  await vi.advanceTimersByTimeAsync(6000)
  expect(getDatasetList).toHaveBeenCalledTimes(3)
})
it('待处理列表的慢查询不会重叠，卸载后不重新安排刷新', async () => {
  const poll = deferred()
  getDatasetList.mockResolvedValueOnce({ datasets: [{ id: 1, status: 'pending' }], total: 1 }).mockReturnValueOnce(poll.promise)
  mountPage(); await flushPromises()
  await vi.advanceTimersByTimeAsync(10000)
  expect(getDatasetList).toHaveBeenCalledTimes(2)
  wrapper.unmount(); wrapper = undefined
  poll.resolve({ datasets: [{ id: 1, status: 'pending' }], total: 1 }); await flushPromises()
  await vi.advanceTimersByTimeAsync(4000)
  expect(getDatasetList).toHaveBeenCalledTimes(2)
})
it('轮询失败后停止自动请求，手动刷新可恢复查询', async () => {
  getDatasetList.mockResolvedValueOnce({ datasets: [{ id: 1, status: 'pending' }], total: 1 }).mockRejectedValueOnce(new Error('offline'))
  mountPage(); await flushPromises()
  await vi.advanceTimersByTimeAsync(6000)
  expect(getDatasetList).toHaveBeenCalledTimes(2)
  expect(ElMessage.error).toHaveBeenCalledWith('获取数据集列表失败')
  getDatasetList.mockResolvedValueOnce({ datasets: [{ id: 1, status: 'ready' }], total: 1 })
  await wrapper.vm.fetchDatasets()
  expect(wrapper.vm.datasets[0].status).toBe('ready')
})
it('未完成或失败的数据集不能发起下载，兼容旧接口没有状态的记录', async () => {
  mountPage(); await flushPromises()
  await wrapper.vm.handleDownload({ id: 1, status: 'pending' })
  await wrapper.vm.handleDownload({ id: 2, status: 'failed' })
  expect(downloadDataset).not.toHaveBeenCalled()
  expect(wrapper.vm.canDownload({ status: 'ready' })).toBe(true)
  expect(wrapper.vm.canDownload({})).toBe(true)
})
