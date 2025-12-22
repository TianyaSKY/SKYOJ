<template>
  <div class="problem-admin-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <h2>题目管理</h2>
          <el-button type="primary" :icon="Plus" @click="handleCreate">新增题目</el-button>
        </div>
      </template>

      <el-table :data="problems" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="title" label="标题" min-width="200" />
        <el-table-column prop="type" label="类型" width="100" />
        <el-table-column prop="language" label="语言" width="100">
          <template #default="scope">
            <el-tag size="small">{{ scope.row.language || 'All' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" align="center" fixed="right">
          <template #default="scope">
            <el-button size="small" :icon="Edit" @click="handleEdit(scope.row)">编辑</el-button>
            <el-popconfirm
              title="确定要删除这道题目吗？"
              @confirm="handleDelete(scope.row.id)"
            >
              <template #reference>
                <el-button size="small" type="danger" :icon="Delete">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Edit/Create Dialog -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="70%" @close="resetForm">
      <el-form :model="form" label-position="top" ref="formRef" v-loading="dialogLoading">
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" />
        </el-form-item>
        <el-form-item label="内容 (Markdown)" prop="content">
          <el-input v-model="form.content" type="textarea" :rows="10" />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="6">
            <el-form-item label="类型" prop="type">
              <el-select v-model="form.type" placeholder="请选择题目类型">
                <el-option label="ACM" value="acm" />
                <el-option label="Kaggle" value="kaggle" />
                <el-option label="OOP" value="oop" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="语言" prop="language">
              <el-select v-model="form.language" placeholder="请选择语言">
                <el-option label="Python" value="python" />
                <el-option label="C++" value="cpp" />
                <el-option label="C" value="c" />
                <el-option label="Java" value="java" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="时间限制 (ms)" prop="time_limit">
              <el-input-number v-model="form.time_limit" :min="100" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="内存限制 (MB)" prop="memory_limit">
              <el-input-number v-model="form.memory_limit" :min="32" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="默认模板代码 (可选)" prop="template_code">
          <el-input v-model="form.template_code" type="textarea" :rows="5" />
        </el-form-item>

        <!-- Test Cases Upload (Only in Edit Mode) -->
        <div v-if="isEdit" class="test-cases-section">
          <el-divider content-position="left">测试点管理</el-divider>
          <el-form-item label="上传测试点 (ZIP)">
            <el-upload
              class="upload-demo"
              action="#"
              :auto-upload="false"
              :limit="1"
              accept=".zip"
              :on-change="handleTestCaseChange"
              :on-remove="handleTestCaseRemove"
              :file-list="testCaseFileList"
            >
              <el-button type="primary">选择文件</el-button>
              <template #tip>
                <div class="el-upload__tip">
                  请上传包含输入输出文件的 ZIP 包。
                </div>
              </template>
            </el-upload>
            <el-button
              type="success"
              size="small"
              class="mt-2"
              @click="handleUploadTestCases"
              :loading="uploadingTestCases"
              :disabled="!selectedTestCaseFile"
            >
              上传测试点
            </el-button>
          </el-form-item>
        </div>
        <div v-else>
          <el-alert title="请先保存题目，然后再编辑以上传测试点。" type="info" show-icon :closable="false" />
        </div>

      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { getProblemList, createProblem, updateProblem, deleteProblem, getProblemDetail, uploadTestCases } from '@/api/problem'
import { ElMessage } from 'element-plus'
import { Plus, Edit, Delete } from '@element-plus/icons-vue'

const problems = ref([])
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const dialogLoading = ref(false)
const isEdit = ref(false)
const currentProblemId = ref(null)

// Test Case Upload Refs
const testCaseFileList = ref([])
const selectedTestCaseFile = ref(null)
const uploadingTestCases = ref(false)

const form = ref({
  title: '',
  content: '',
  language: 'python',
  type: 'acm',
  time_limit: 1000,
  memory_limit: 128,
  template_code: ''
})

const dialogTitle = computed(() => (isEdit.value ? '编辑题目' : '新增题目'))

const fetchProblems = async () => {
  loading.value = true
  try {
    problems.value = await getProblemList()
  } catch (error) {
    ElMessage.error('获取题目列表失败')
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  form.value = {
    title: '',
    content: '',
    language: 'python',
    type: 'acm',
    time_limit: 1000,
    memory_limit: 128,
    template_code: ''
  }
  currentProblemId.value = null

  // Reset test case upload
  testCaseFileList.value = []
  selectedTestCaseFile.value = null
}

const handleCreate = () => {
  isEdit.value = false
  resetForm()
  dialogVisible.value = true
}

const handleEdit = async (row) => {
  isEdit.value = true
  currentProblemId.value = row.id
  dialogVisible.value = true
  dialogLoading.value = true

  // Reset test case upload when opening edit dialog
  testCaseFileList.value = []
  selectedTestCaseFile.value = null

  try {
    const detail = await getProblemDetail(row.id)
    form.value = { ...detail }
    if (!form.value.language) {
      form.value.language = 'python'
    }
  } catch (error) {
    ElMessage.error('获取题目详情失败')
    dialogVisible.value = false
  } finally {
    dialogLoading.value = false
  }
}

const handleDelete = async (id) => {
  try {
    await deleteProblem(id)
    ElMessage.success('删除成功')
    fetchProblems() // Refresh list
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

const handleSubmit = async () => {
  submitting.value = true
  try {
    if (isEdit.value) {
      await updateProblem(currentProblemId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await createProblem(form.value)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    fetchProblems() // Refresh list
  } catch (error) {
    ElMessage.error('操作失败')
  } finally {
    submitting.value = false
  }
}

// Test Case Upload Handlers
const handleTestCaseChange = (uploadFile, uploadFiles) => {
  if (uploadFiles.length > 1) {
    uploadFiles.splice(0, 1)
  }
  selectedTestCaseFile.value = uploadFile.raw
  testCaseFileList.value = uploadFiles
}

const handleTestCaseRemove = () => {
  selectedTestCaseFile.value = null
  testCaseFileList.value = []
}

const handleUploadTestCases = async () => {
  if (!selectedTestCaseFile.value) return

  uploadingTestCases.value = true
  try {
    const formData = new FormData()
    formData.append('file', selectedTestCaseFile.value)

    await uploadTestCases(currentProblemId.value, formData)
    ElMessage.success('测试点上传成功')
    testCaseFileList.value = []
    selectedTestCaseFile.value = null
  } catch (error) {
    ElMessage.error('测试点上传失败')
  } finally {
    uploadingTestCases.value = false
  }
}

onMounted(() => {
  fetchProblems()
})
</script>

<style scoped>
.problem-admin-container {
  max-width: 1200px;
  margin: 0 auto;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.mt-2 {
  margin-top: 10px;
}
.test-cases-section {
  margin-top: 20px;
  padding-top: 10px;
  border-top: 1px dashed var(--el-border-color);
}
</style>
