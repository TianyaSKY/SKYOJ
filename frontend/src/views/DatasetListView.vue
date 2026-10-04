<template>
  <div class="dataset-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <h2 class="header-title">公开数据集</h2>
          <el-button :loading="loading" :disabled="loading" @click="fetchDatasets()"
            >刷新</el-button
          >
          <el-button v-if="isTeacher" :icon="Upload" type="primary" @click="openUpload">
            上传数据集
          </el-button>
        </div>
      </template>

      <el-table v-loading="loading" :data="datasets" stripe style="width: 100%">
        <el-table-column label="名称" min-width="200" prop="name" />
        <el-table-column label="描述" min-width="300" prop="description" />
        <el-table-column label="上传者" prop="uploader" width="120" />
        <el-table-column label="大小" prop="file_size" width="100" />
        <el-table-column label="状态" width="100">
          <template #default="scope">
            <el-tag
              :type="
                scope.row.status === 'failed'
                  ? 'danger'
                  : scope.row.status === 'pending'
                    ? 'warning'
                    : 'success'
              "
            >
              {{ datasetStatuses[scope.row.status || 'ready'] || scope.row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="上传日期" prop="created_at" width="180">
          <template #default="scope">
            {{ new Date(scope.row.created_at).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column align="center" fixed="right" label="操作" width="180">
          <template #default="scope">
            <el-button-group>
              <el-button
                :icon="Download"
                size="small"
                type="success"
                :disabled="!canDownload(scope.row)"
                @click="handleDownload(scope.row)"
              >
                下载
              </el-button>
              <el-popconfirm
                v-if="isTeacher"
                cancel-button-text="取消"
                confirm-button-text="确定"
                title="确定要删除这个数据集吗？"
                @confirm="handleDelete(scope.row)"
              >
                <template #reference>
                  <el-button
                    :icon="Delete"
                    size="small"
                    type="danger"
                    :loading="deleting.has(scope.row.id)"
                    :disabled="deleting.has(scope.row.id)"
                  >
                    删除
                  </el-button>
                </template>
              </el-popconfirm>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          :current-page="currentPage"
          :page-size="pageSize"
          :disabled="loading"
          :page-sizes="[10, 20, 50]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- Upload Dialog -->
    <el-dialog v-model="uploadDialogVisible" title="上传数据集" width="500px">
      <el-form :model="uploadForm" label-position="top">
        <el-form-item label="数据集名称">
          <el-input v-model="uploadForm.name" placeholder="请输入数据集名称"></el-input>
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="uploadForm.description"
            placeholder="请输入数据集描述"
            type="textarea"
          ></el-input>
        </el-form-item>
        <el-form-item label="数据集文件">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            action="#"
          >
            <el-button type="primary">选择文件</el-button>
            <template #tip>
              <div class="el-upload__tip">请上传 ZIP, CSV, JSON 等格式的文件，最大限制 500MB。</div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="uploadDialogVisible = false">取消</el-button>
          <el-button
            :loading="uploading"
            :disabled="uploading"
            type="primary"
            @click="handleUpload"
          >
            确认上传
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useUserStore } from '@/stores/user'
import { deleteDataset, downloadDataset, getDatasetList, uploadDataset } from '@/api/dataset'
import { ElMessage, type UploadInstance, type UploadFile, type UploadFiles } from 'element-plus'
import type { DatasetResponse } from '@/types/dataset'
import { Delete, Download, Upload } from '@element-plus/icons-vue'

const userStore = useUserStore()
const datasets = ref<DatasetResponse[]>([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const deleting = ref(new Set<number>())
const pageSize = ref(20)
const uploadDialogVisible = ref(false)
const uploading = ref(false)
const uploadRef = ref<UploadInstance>()
let uploadVersion = 0
let listVersion = 0
let requestedPage = 1
let requestedPageSize = 20
let disposed = false
let refreshTimer: ReturnType<typeof setTimeout> | null = null
const isCurrentUpload = (version: number) =>
  !disposed && version === uploadVersion && uploadDialogVisible.value

const MAX_SIZE_MB = 500
const datasetStatuses: Record<string, string> = {
  pending: '处理中',
  ready: '可下载',
  failed: '处理失败',
}
const canDownload = (row: DatasetResponse) => !row.status || row.status === 'ready'

const scheduleRefresh = (delay: number) => {
  if (disposed) return
  if (refreshTimer !== null) clearTimeout(refreshTimer)
  refreshTimer = setTimeout(() => {
    refreshTimer = null
    fetchDatasets()
  }, delay)
}

const uploadForm = ref<{ name: string; description: string; file: File | null }>({
  name: '',
  description: '',
  file: null,
})

const isTeacher = computed(() => userStore.user?.role === 'teacher')

const fetchDatasets = async (page = requestedPage, size = requestedPageSize): Promise<void> => {
  if (disposed) return
  if (refreshTimer !== null) {
    clearTimeout(refreshTimer)
    refreshTimer = null
  }
  requestedPage = page
  requestedPageSize = size
  const version = ++listVersion
  const isCurrent = () => !disposed && version === listVersion
  loading.value = true
  try {
    const res = await getDatasetList({
      page,
      page_size: size,
    })
    if (!isCurrent()) return
    const items = Array.isArray(res) ? res : 'datasets' in res ? res.datasets : res.data
    const count = !Array.isArray(res) && 'datasets' in res ? res.total : items.length
    const lastPage = Math.max(1, Math.ceil(count / size))
    if (page > lastPage) return await fetchDatasets(lastPage, size)
    datasets.value = items
    total.value = count
    currentPage.value = page
    pageSize.value = size
    // 等本次查询结束再安排下一次查询，避免慢请求重叠。
    if (items.some((item) => item.status === 'pending')) scheduleRefresh(2000)
  } catch (error) {
    if (isCurrent()) {
      requestedPage = currentPage.value
      requestedPageSize = pageSize.value
      ElMessage.error('获取数据集列表失败')
    }
  } finally {
    if (isCurrent()) loading.value = false
  }
}

const handleSizeChange = (val: number) => fetchDatasets(1, val)
const handleCurrentChange = (val: number) => fetchDatasets(val, pageSize.value)

const handleDownload = async (row: DatasetResponse) => {
  if (disposed || !canDownload(row)) return
  try {
    const blob = await downloadDataset(row.id)
    const url = window.URL.createObjectURL(new Blob([blob]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', row.name || `dataset_${row.id}`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error('下载失败')
  }
}

const handleDelete = async (row: DatasetResponse) => {
  if (disposed || deleting.value.has(row.id)) return
  deleting.value.add(row.id)
  try {
    await deleteDataset(row.id)
    if (disposed) return
    ElMessage.success('删除成功')
    await fetchDatasets()
  } catch (error) {
    if (!disposed) ElMessage.error('删除失败')
  } finally {
    deleting.value.delete(row.id)
  }
}

const handleFileChange = (file: UploadFile) => {
  const isLtLimit = (file.size ?? 0) / 1024 / 1024 < MAX_SIZE_MB
  if (!isLtLimit) {
    ElMessage.error(`上传文件大小不能超过 ${MAX_SIZE_MB}MB!`)
    uploadRef.value?.clearFiles()
    uploadForm.value.file = null
    return
  }
  uploadForm.value.file = file.raw || null
}

const handleFileRemove = (file: UploadFile, files: UploadFiles) => {
  uploadForm.value.file = files[0]?.raw || null
}

const resetUploadForm = () => {
  uploadForm.value = { name: '', description: '', file: null }
  uploadRef.value?.clearFiles()
}

const openUpload = () => {
  uploadVersion += 1
  uploading.value = false
  resetUploadForm()
  uploadDialogVisible.value = true
}

watch(
  uploadDialogVisible,
  (visible) => {
    if (!visible) {
      uploadVersion += 1
      uploading.value = false
      resetUploadForm()
    }
  },
  { flush: 'sync' },
)

const handleUpload = async () => {
  if (!uploadDialogVisible.value || uploading.value) return
  const version = uploadVersion
  if (!uploadForm.value.name || !uploadForm.value.file) {
    ElMessage.warning('请填写数据集名称并选择文件')
    return
  }

  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('name', uploadForm.value.name)
    formData.append('description', uploadForm.value.description)
    formData.append('file', uploadForm.value.file)

    await uploadDataset(formData)
    if (disposed) return
    // 上传已生效时刷新列表，不能关闭后来打开的上传窗口。
    scheduleRefresh(1000)
    if (!isCurrentUpload(version)) return
    ElMessage.success('上传已开始，请稍后刷新列表查看')
    uploadDialogVisible.value = false
  } catch (error) {
    if (isCurrentUpload(version)) ElMessage.error('上传失败')
  } finally {
    if (isCurrentUpload(version)) uploading.value = false
  }
}

onBeforeUnmount(() => {
  disposed = true
  if (refreshTimer !== null) clearTimeout(refreshTimer)
})

onMounted(() => {
  fetchDatasets()
})
</script>

<style scoped>
.dataset-container {
  max-width: 1200px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  margin: 0;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}
</style>
