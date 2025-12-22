<template>
  <div class="dataset-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <h2 class="header-title">公开数据集</h2>
          <el-button
            v-if="isTeacher"
            type="primary"
            :icon="Upload"
            @click="uploadDialogVisible = true"
          >
            上传数据集
          </el-button>
        </div>
      </template>

      <el-table :data="datasets" style="width: 100%" v-loading="loading" stripe>
        <el-table-column prop="name" label="名称" min-width="200" />
        <el-table-column prop="description" label="描述" min-width="300" />
        <el-table-column prop="uploader" label="上传者" width="120" />
        <el-table-column prop="file_size" label="大小" width="100" />
        <el-table-column prop="created_at" label="上传日期" width="180">
          <template #default="scope">
            {{ new Date(scope.row.created_at).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" align="center" fixed="right">
          <template #default="scope">
            <el-button-group>
              <el-button
                type="success"
                :icon="Download"
                size="small"
                @click="handleDownload(scope.row)"
              >
                下载
              </el-button>
              <el-button
                type="info"
                :icon="Link"
                size="small"
                @click="copyDownloadLink(scope.row)"
              >
                复制链接
              </el-button>
              <el-popconfirm
                v-if="isTeacher"
                title="确定要删除这个数据集吗？"
                confirm-button-text="确定"
                cancel-button-text="取消"
                @confirm="handleDelete(scope.row)"
              >
                <template #reference>
                  <el-button
                    type="danger"
                    :icon="Delete"
                    size="small"
                  >
                    删除
                  </el-button>
                </template>
              </el-popconfirm>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Upload Dialog -->
    <el-dialog v-model="uploadDialogVisible" title="上传数据集" width="500px" @close="resetUploadForm">
      <el-form :model="uploadForm" label-position="top">
        <el-form-item label="数据集名称">
          <el-input v-model="uploadForm.name" placeholder="请输入数据集名称"></el-input>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="uploadForm.description" type="textarea" placeholder="请输入数据集描述"></el-input>
        </el-form-item>
        <el-form-item label="数据集文件">
          <el-upload
            ref="uploadRef"
            action="#"
            :limit="1"
            :auto-upload="false"
            :on-change="handleFileChange"
          >
            <el-button type="primary">选择文件</el-button>
            <template #tip>
              <div class="el-upload__tip">
                请上传 ZIP, CSV, JSON 等格式的文件。
              </div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="uploadDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleUpload" :loading="uploading">
            确认上传
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useUserStore } from '@/stores/user'
import { getDatasetList, uploadDataset, deleteDataset } from '@/api/dataset'
import { ElMessage } from 'element-plus'
import { Upload, Download, Delete, Link } from '@element-plus/icons-vue'

const userStore = useUserStore()
const datasets = ref([])
const loading = ref(false)
const uploadDialogVisible = ref(false)
const uploading = ref(false)
const uploadRef = ref(null)

const uploadForm = ref({
  name: '',
  description: '',
  file: null
})

const isTeacher = computed(() => userStore.user?.role === 'teacher')

const fetchDatasets = async () => {
  loading.value = true
  try {
    const response = await getDatasetList()
    datasets.value = response.data || response
  } catch (error) {
    ElMessage.error('获取数据集列表失败')
  } finally {
    loading.value = false
  }
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
  uploadForm.value.file = file.raw
}

const resetUploadForm = () => {
  uploadForm.value = { name: '', description: '', file: null }
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
    ElMessage.success('上传成功！')
    uploadDialogVisible.value = false
    fetchDatasets()
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
</style>
