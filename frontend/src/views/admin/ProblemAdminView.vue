<template>
  <div class="problem-admin-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <h2>题目管理</h2>
          <div class="header-actions">
            <el-button :icon="Document" @click="goToDraftBox">AI 草稿箱</el-button>
            <el-button :icon="MagicStick" type="success" @click="handleAiCreate"
            >AI 生成题目
            </el-button
            >
            <el-button :icon="Plus" type="primary" @click="handleCreate">新增题目</el-button>
          </div>
        </div>
      </template>

      <el-table v-loading="loading" :data="problems" stripe>
        <el-table-column label="ID" prop="id" width="80"/>
        <el-table-column label="标题" min-width="200" prop="title">
          <template #default="scope">
            <el-link type="primary" @click="goToProblem(scope.row.id)">{{ scope.row.title }}</el-link>
          </template>
        </el-table-column>
        <el-table-column label="类型" prop="type" width="100"/>
        <el-table-column label="语言" prop="language" width="150">
          <template #default="scope">
            <el-tag size="small">
              {{ scope.row.language || 'python' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column align="center" fixed="right" label="操作" width="280">
          <template #default="scope">
            <el-button :icon="Edit" size="small" @click="handleEdit(scope.row)">编辑</el-button>
            <el-button :icon="Cpu" size="small" type="warning" @click="handleAiTestData(scope.row)"
            >AICase
            </el-button
            >
            <el-popconfirm title="确定要删除这道题目吗？" @confirm="handleDelete(scope.row.id)">
              <template #reference>
                <el-button :icon="Delete" size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Edit/Create Dialog -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="82%" top="4vh" @close="resetForm">
      <el-form ref="formRef" v-loading="dialogLoading" :model="form" label-position="top">
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title"/>
        </el-form-item>
        <el-form-item label="内容 (Markdown)" prop="content">
          <MarkdownContentEditor
              v-model="form.content"
              default-mode="split"
              min-height="360px"
              :rows="16"
              placeholder="题目描述支持 Markdown：标题、代码块、公式等"
          />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="6">
            <el-form-item label="类型" prop="type">
              <el-select v-model="form.type" placeholder="请选择题目类型">
                <el-option label="ACM" value="acm"/>
                <el-option label="Kaggle" value="kaggle"/>
                <el-option label="OOP" value="oop"/>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="允许语言" prop="language">
              <el-select
                  v-model="form.language"
                  placeholder="请选择允许的语言"
                  style="width: 100%"
              >
                <el-option label="Python" value="python"/>
                <el-option label="C++" value="cpp"/>
                <el-option label="C" value="c"/>
                <el-option label="Java" value="java"/>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="时间限制 (ms)" prop="time_limit">
              <el-input-number v-model="form.time_limit" :min="100" style="width: 100%"/>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="内存限制 (MB)" prop="memory_limit">
              <el-input-number v-model="form.memory_limit" :min="32" style="width: 100%"/>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="默认模板代码 (可选)" prop="template_code">
          <div v-if="dialogVisible" class="editor-container mini-editor">
            <vue-monaco-editor
                v-model:value="form.template_code"
                :language="form.language || 'python'"
                :options="miniEditorOptions"
                theme="vs-dark"
            />
          </div>
        </el-form-item>

        <!-- Test Cases Upload (Only in Edit Mode) -->
        <div v-if="isEdit" class="test-cases-section">
          <el-divider content-position="left">测试点管理</el-divider>
          <el-form-item label="上传测试点 (ZIP)">
            <el-upload
                :auto-upload="false"
                :file-list="testCaseFileList"
                :limit="1"
                :on-change="handleTestCaseChange"
                :on-remove="handleTestCaseRemove"
                accept=".zip"
                action="#"
                class="upload-demo"
            >
              <el-button type="primary">选择文件</el-button>
              <template #tip>
                <div class="el-upload__tip">请上传包含输入输出文件的 ZIP 包。</div>
              </template>
            </el-upload>
            <div class="mt-2">
              <el-button
                  :disabled="!selectedTestCaseFile"
                  :loading="uploadingTestCases"
                  size="small"
                  type="success"
                  @click="handleUploadTestCases"
              >
                上传测试点
              </el-button>
              <el-button
                  :icon="Download"
                  :loading="downloadingTestCases"
                  size="small"
                  type="info"
                  @click="handleDownloadTestCases"
              >
                下载所有测试点
              </el-button>
              <el-popconfirm title="确定要删除所有测试点吗？" @confirm="handleDeleteAllTestCases">
                <template #reference>
                  <el-button
                      :icon="Delete"
                      :loading="deletingTestCases"
                      size="small"
                      type="danger"
                  >
                    删除所有测试点
                  </el-button>
                </template>
              </el-popconfirm>
            </div>
          </el-form-item>
        </div>
        <div v-else>
          <el-alert
              :closable="false"
              show-icon
              title="请先保存题目，然后再编辑以上传测试点。"
              type="info"
          />
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button :loading="submitting" type="primary" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>

    <!-- AI Generation Dialog（异步提交到草稿箱） -->
    <el-dialog v-model="aiDialogVisible" title="AI 生成题目" width="520px">
      <el-alert
          :closable="false"
          class="mb-12"
          show-icon
          title="提交后将在后台生成，可关闭本窗口，到「AI 草稿箱」查看结果并创建正式题目。"
          type="info"
      />
      <el-form :model="aiForm" label-position="top">
        <el-form-item label="题目背景/大致方向" required>
          <el-input
              v-model="aiForm.background"
              :rows="4"
              placeholder="例如：关于字符串处理的题目，要求统计元音字母数量，适合初学者。"
              type="textarea"
          />
        </el-form-item>
        <el-form-item label="题目难度">
          <el-radio-group v-model="aiForm.difficulty">
            <el-radio value="简单">简单</el-radio>
            <el-radio value="中等">中等</el-radio>
            <el-radio value="困难">困难</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="aiDialogVisible = false">取消</el-button>
        <el-button @click="goToDraftBox">打开草稿箱</el-button>
        <el-button :loading="aiGenerating" type="primary" @click="generateProblem">
          提交后台生成
        </el-button>
      </template>
    </el-dialog>

    <!-- AI Test Data Generation Dialog（异步提交到草稿箱） -->
    <el-dialog v-model="aiTestDataVisible" title="AI 生成测试数据" width="560px">
      <el-alert
          :closable="false"
          class="mb-12"
          show-icon
          title="脚本在后台生成。完成后请到「AI 草稿箱」预览脚本并提交执行，无需在本页等待。"
          type="info"
      />
      <div v-loading="fetchingDetail">
        <el-form :model="testDataForm" label-position="top">
          <el-form-item label="生成方向/要求 (可选)">
            <el-input
                v-model="testDataForm.direction"
                :rows="4"
                placeholder="例如：生成若干组数据，包含边界情况（空字符串、超长字符串），数据分布均匀。"
                type="textarea"
            />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="aiTestDataVisible = false">取消</el-button>
        <el-button @click="goToDraftBox">打开草稿箱</el-button>
        <el-button
            :disabled="fetchingDetail || !currentProblem"
            :loading="scriptGenerating"
            type="primary"
            @click="handleGenerateScript"
        >
          提交后台生成脚本
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import {computed, onMounted, ref} from 'vue'
import {useRouter} from 'vue-router'
import {
  createProblem,
  deleteAllTestCases,
  deleteProblem,
  downloadTestCases,
  getProblemDetail,
  getProblemList,
  updateProblem,
  uploadTestCases,
} from '@/api/problem'
import {
  submitProblemGenerationDraft,
  submitTestScriptGenerationDraft,
} from '@/api/llm'
import {
  generateProblemDraftSchema,
  generateTestScriptDraftSchema,
} from '@/schemas/aiDraft'
import {ElMessage} from 'element-plus'
import {Cpu, Delete, Document, Download, Edit, MagicStick, Plus} from '@element-plus/icons-vue'
import {VueMonacoEditor} from '@guolao/vue-monaco-editor'
import MarkdownContentEditor from '@/components/MarkdownContentEditor.vue'

const router = useRouter()
const problems = ref([])
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const dialogLoading = ref(false)
const isEdit = ref(false)
const currentProblemId = ref(null)
const currentProblem = ref(null)

// AI Generation State
const aiDialogVisible = ref(false)
const aiGenerating = ref(false)
const aiForm = ref({
  background: '',
  difficulty: '简单',
})

// AI Test Data State
const aiTestDataVisible = ref(false)
const fetchingDetail = ref(false)
const scriptGenerating = ref(false)
const testDataForm = ref({
  direction: '',
})

const miniEditorOptions = {
  automaticLayout: true,
  minimap: {enabled: false},
  fontSize: 13,
  scrollBeyondLastLine: false,
  lineNumbers: 'on',
  folding: false,
}

// Test Case Upload Refs
const testCaseFileList = ref([])
const selectedTestCaseFile = ref(null)
const uploadingTestCases = ref(false)
const downloadingTestCases = ref(false)
const deletingTestCases = ref(false)

const form = ref({
  title: '',
  content: '',
  language: 'python',
  type: 'acm',
  time_limit: 1000,
  memory_limit: 128,
  template_code: '',
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
    template_code: '',
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

const handleAiCreate = () => {
  aiForm.value = {background: '', difficulty: '简单'}
  aiDialogVisible.value = true
}

const goToDraftBox = () => {
  router.push({name: 'ai-draft-box'})
}

const generateProblem = async () => {
  const parsed = generateProblemDraftSchema.safeParse({
    background: aiForm.value.background,
    difficulty: aiForm.value.difficulty,
  })
  if (!parsed.success) {
    ElMessage.warning(parsed.error.issues[0]?.message || '参数校验失败')
    return
  }

  aiGenerating.value = true
  try {
    const res = await submitProblemGenerationDraft(parsed.data)
    aiDialogVisible.value = false
    ElMessage.success(res.message || '已提交后台生成，请到草稿箱查看')
  } catch (error) {
    const msg = error?.response?.data?.error || '提交 AI 出题任务失败'
    ElMessage.error(msg)
  } finally {
    aiGenerating.value = false
  }
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
    // Ensure template_code is a string to avoid Monaco Editor \"Illegal argument\" error
    form.value = {
      ...detail,
      template_code: detail.template_code || '',
      language: detail.language || 'python'
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

// AI Test Data Handlers（异步：只提交生成脚本任务）
const handleAiTestData = async (row) => {
  aiTestDataVisible.value = true
  fetchingDetail.value = true
  testDataForm.value = {
    direction: '',
  }

  try {
    currentProblem.value = await getProblemDetail(row.id)
  } catch (error) {
    ElMessage.error('获取题目详情失败')
    aiTestDataVisible.value = false
  } finally {
    fetchingDetail.value = false
  }
}

const handleGenerateScript = async () => {
  if (!currentProblem.value?.id) {
    ElMessage.warning('题目信息未加载完成')
    return
  }

  const parsed = generateTestScriptDraftSchema.safeParse({
    problem_id: currentProblem.value.id,
    direction: testDataForm.value.direction || '',
  })
  if (!parsed.success) {
    ElMessage.warning(parsed.error.issues[0]?.message || '参数校验失败')
    return
  }

  scriptGenerating.value = true
  try {
    const res = await submitTestScriptGenerationDraft(parsed.data)
    aiTestDataVisible.value = false
    ElMessage.success(res.message || '已提交后台生成，请到草稿箱查看')
  } catch (error) {
    const msg = error?.response?.data?.error || '提交测例脚本任务失败'
    ElMessage.error(msg)
  } finally {
    scriptGenerating.value = false
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

const handleDownloadTestCases = async () => {
  downloadingTestCases.value = true
  try {
    const blob = await downloadTestCases(currentProblemId.value)
    const url = window.URL.createObjectURL(new Blob([blob]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `problem_${currentProblemId.value}_testcases.zip`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('下载开始')
  } catch (error) {
    ElMessage.error('下载失败')
  } finally {
    downloadingTestCases.value = false
  }
}

const handleDeleteAllTestCases = async () => {
  deletingTestCases.value = true
  try {
    await deleteAllTestCases(currentProblemId.value)
    ElMessage.success('所有测试点已删除')
  } catch (error) {
    ElMessage.error('删除失败')
  } finally {
    deletingTestCases.value = false
  }
}

const goToProblem = (id) => {
  router.push({name: 'problem-detail', params: {id}})
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

.header-actions {
  display: flex;
  gap: 12px;
}

.mt-2 {
  margin-top: 10px;
  display: flex;
  gap: 10px;
}

.mb-12 {
  margin-bottom: 12px;
}

.test-cases-section {
  margin-top: 20px;
  padding-top: 10px;
  border-top: 1px dashed var(--el-border-color);
}

.editor-container {
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  overflow: hidden;
  width: 100%;
}

.mini-editor {
  height: 200px;
}
</style>
