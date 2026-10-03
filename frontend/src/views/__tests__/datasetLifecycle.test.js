import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
vi.mock('@/stores/user', () => ({ useUserStore: () => ({ user: { role: 'teacher' } }) }))
vi.mock('@/api/dataset', () => ({ getDatasetList: vi.fn(), uploadDataset: vi.fn(), deleteDataset: vi.fn(), downloadDataset: vi.fn() }))
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn(), success: vi.fn(), warning: vi.fn() } }))
import DatasetListView from '../DatasetListView.vue'
import { getDatasetList, uploadDataset } from '@/api/dataset'
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
