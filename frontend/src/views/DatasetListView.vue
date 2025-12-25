<template>
  <div class="dataset-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <h2 class="header-title">公开数据集</h2>
          <el-button
              v-if="isTeacher"
              :icon="Upload"
              type="primary"
              @click="uploadDialogVisible = true"
          >
            上传数据集
          </el-button>
        </div>
      </template>

      <el-table v-loading="loading" :data="datasets" stripe style="width: 100%">
        <el-table-column label="名称" min-width="200" prop="name"/>
        <el-table-column label="描述" min-width="300" prop="description"/>
        <el-table-column label="上传者" prop="uploader" width="120"/>
        <el-table-column label="大小" prop="file_size" width="100"/>
        <el-table-column label="上传日期" prop="created_at" width="180">
          <template #default="scope">
            {{ new Date(scope.row.created_at).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column align="center" fixed="right" label="操作" width="250">
          <template #default="scope">
            <el-button-group>
              <el-button
                  :icon="Download"
                  size="small"
                  type="success"
                  @click="handleDownload(scope.row)"
              >
                下载
              </el-button>
              <el-button
                  :icon="Link"
                  size="small"
                  type="info"
                  @click="copyDownloadLink(scope.row)"
              >
                复制链接
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
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50]"
            :total="total"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- Upload Dialog -->
    <el-dialog v-model="uploadDialogVisible" title="上传数据集" width="500px" @close="resetUploadForm">
      <el-form :model="uploadForm" label-position="top">
        <el-form-item label="数据集名称">
          <el-input v-model="uploadForm.name" placeholder="请输入数据集名称"></el-input>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="uploadForm.description" placeholder="请输入数据集描述" type="textarea"></el-input>
        </el-form-item>
        <el-form-item label="数据集文件">
          <el-upload
              ref="uploadRef"
              :auto-upload="false"
              :limit="1"
              :on-change="handleFileChange"
              action="#"
          >
            <el-button type="primary">选择文件</el-button>
            <template #tip>
              <div class="el-upload__tip">
                请上传 ZIP, CSV, JSON 等格式的文件，最大限制 500MB。
              </div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="uploadDialogVisible = false">取消</el-button>
          <el-button :loading="uploading" type="primary" @click="handleUpload">
            确认上传
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import {computed, onMounted, ref} from 'vue'
import {useUserStore} from '@/stores/user'
import {deleteDataset, getDatasetList, uploadDataset} from '@/api/dataset'
import {ElMessage} from 'element-plus'
import {Delete, Download, Link, Upload} from '@element-plus/icons-vue'

const userStore = useUserStore()
const datasets = ref([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const uploadDialogVisible = ref(false)
const uploading = ref(false)
const uploadRef = ref(null)

const MAX_SIZE_MB = 500

const uploadForm = ref({
  name: '',
  description: '',
  file: null
})

const isTeacher = computed(() => userStore.user?.role === 'teacher')

const fetchDatasets = async () => {
  loading.value = true
  try {
    const res = await getDatasetList({
      page: currentPage.value,
      page_size: pageSize.value
    })
    if (res.datasets) {
      datasets.value = res.datasets
      total.value = res.total
    } else {
      datasets.value = res.data || res
      total.value = datasets.value.length
    }
  } catch (error) {
    ElMessage.error('获取数据集列表失败')
  } finally {
    loading.value = false
  }
}

const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  fetchDatasets()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchDatasets()
}

const handleDownload = (row) => {
  const token = userStore.token
  const url = `${window.location.origin}${row.download_url}?token=${token}`
  window.open(url, '_blank')
}

const copyDownloadLink = (row) => {
  const token = userStore.token
  if (!token) {
    ElMessage.warning('请先登录以获取下载链接')
    return
  }
  const url = `${window.location.origin}${row.download_url}?token=${token}`

  navigator.clipboard.writeText(url).then(() => {
    ElMessage.success('下载链接已复制到剪贴板（含临时Token）')
  }).catch(() => {
    ElMessage.error('复制失败，请手动复制')
  })
}

const handleDelete = async (row) => {
  try {
    await deleteDataset(row.id)
    ElMessage.success('删除成功')
    fetchDatasets()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

const handleFileChange = (file) => {
  const isLtLimit = file.size / 1024 / 1024 < MAX_SIZE_MB
  if (!isLtLimit) {
    ElMessage.error(`上传文件大小不能超过 ${MAX_SIZE_MB}MB!`)
    uploadRef.value?.clearFiles()
    uploadForm.value.file = null
    return
  }
  uploadForm.value.file = file.raw
}

const resetUploadForm = () => {
  uploadForm.value = {name: '', description: '', file: null}
  uploadRef.value?.clearFiles()
}

const handleUpload = async () => {
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
    ElMessage.success('上传已开始，请稍后刷新列表查看')
    uploadDialogVisible.value = false
    // 延迟刷新，给异步保存一点时间
    setTimeout(() => {
      fetchDatasets()
    }, 1000)
  } catch (error) {
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}

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
