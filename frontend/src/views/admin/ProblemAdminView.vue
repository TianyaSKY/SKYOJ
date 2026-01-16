<template>
  <div class="problem-admin-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <h2>题目管理</h2>
          <div class="header-actions">
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
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="70%" @close="resetForm">
      <el-form ref="formRef" v-loading="dialogLoading" :model="form" label-position="top">
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title"/>
        </el-form-item>
        <el-form-item label="内容 (Markdown)" prop="content">
          <el-input v-model="form.content" :rows="10" type="textarea"/>
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

    <!-- AI Generation Dialog -->
    <el-dialog v-model="aiDialogVisible" title="AI 生成题目" width="500px">
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
            <el-radio label="简单">简单</el-radio>
            <el-radio label="中等">中等</el-radio>
            <el-radio label="困难">困难</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="aiDialogVisible = false">取消</el-button>
        <el-button :loading="aiGenerating" type="primary" @click="generateProblem"
        >生成预览
        </el-button
        >
      </template>
    </el-dialog>

    <!-- AI Test Data Generation Dialog -->
    <el-dialog v-model="aiTestDataVisible" title="AI 生成测试数据" width="900px">
      <el-steps :active="aiStep" finish-status="success" simple style="margin-bottom: 20px">
        <el-step title="配置方向"/>
        <el-step title="生成脚本"/>
        <el-step title="执行生成"/>
      </el-steps>

      <div v-if="aiStep === 0" v-loading="fetchingDetail">
        <el-form :model="testDataForm" label-position="top">
          <el-form-item label="生成方向/要求 (可选)">
            <el-input
                v-model="testDataForm.direction"
                :rows="3"
                placeholder="例如：生成 10 组数据，包含边界情况（空字符串、超长字符串），数据分布均匀。"
                type="textarea"
            />
          </el-form-item>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="测试点个数">
                <el-input-number v-model="testDataForm.count" :max="50" :min="1"/>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="数据范围描述">
                <el-input
                    v-model="testDataForm.range_info"
                    placeholder="例如：n <= 10^5, a[i] <= 10^9"
                />
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
      </div>

      <div v-if="aiStep === 1">
        <div class="script-header">
          <span>生成的 {{ generatedLanguage === 'java' ? 'Java 测试类' : '测试脚本' }}</span>
          <el-tag size="small" type="info">语言: {{ generatedLanguage }}</el-tag>
        </div>
        <div v-if="aiTestDataVisible" class="editor-container script-editor">
          <vue-monaco-editor
              v-model:value="generatedScript"
              :language="generatedLanguage"
              :options="editorOptions"
              theme="vs-dark"
          />
        </div>
      </div>

      <div v-if="aiStep === 2" class="execution-status">
        <div v-if="executing" class="loading-box">
          <el-icon class="is-loading">
            <Loading/>
          </el-icon>
          <p>正在生成测试数据并提交到服务器...</p>
        </div>
        <div v-else-if="executionResult" class="result-box">
          <el-result
              :sub-title="`已成功生成并上传 ${testDataForm.count} 组测试数据。`"
              icon="success"
              title="生成成功"
          >
            <template #extra>
              <el-button type="primary" @click="aiTestDataVisible = false">完成</el-button>
            </template>
          </el-result>
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button v-if="aiStep > 0 && aiStep < 2" @click="aiStep--">上一步</el-button>
          <el-button
              v-if="aiStep === 0"
              :disabled="fetchingDetail"
              :loading="scriptGenerating"
              type="primary"
              @click="handleGenerateScript"
          >
            下一步：生成脚本
          </el-button>
          <el-button
              v-if="aiStep === 1"
              :loading="executing"
              type="success"
              @click="handleExecuteScript"
          >
            执行并提交
          </el-button>
        </div>
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
import {askLLM, executeAndSubmitTestData} from '@/api/llm'
import {ElMessage} from 'element-plus'
import {Cpu, Delete, Download, Edit, Loading, MagicStick, Plus} from '@element-plus/icons-vue'
import {VueMonacoEditor} from '@guolao/vue-monaco-editor'

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
const aiStep = ref(0)
const scriptGenerating = ref(false)
const executing = ref(false)
const generatedScript = ref('')
const generatedLanguage = ref('python')
const executionResult = ref(null)
const testDataForm = ref({
  direction: '',
  count: 10,
  range_info: '',
})

// Editor Options
const editorOptions = {
  automaticLayout: true,
  minimap: {enabled: true},
  fontSize: 14,
  scrollBeyondLastLine: false,
  roundedSelection: false,
  readOnly: false,
  cursorStyle: 'line',
}

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

const generateProblem = async () => {
  if (!aiForm.value.background) {
    ElMessage.warning('请输入题目背景')
    return
  }

  aiGenerating.value = true
  try {
    const res = await askLLM({
      system_setting: `你是一个专业的算法竞赛出题人。请根据用户提供的背景 and 难度，设计一道高质量的编程题目。
      平台支持三种模式：
      1. ACM 模式：标准 I/O，严格文本比对。
      2. OOP 模式：实现特定接口/类，运行单元测试。
      3. Kaggle 模式：提交预测结果 CSV 文件，基于 Metric 评分。
      请根据题目性质选择最合适的模式。题目内容必须使用 Markdown 格式，包含：题目描述、输入格式、输出格式、样例输入、样例输出、提示/说明。`,
      prompt: `题目背景: ${aiForm.value.background}\n难度: ${aiForm.value.difficulty}`,
      output_format: {
        title: '题目名称',
        content: 'Markdown 格式的题目内容',
        template_code: '该题目的初始代码模板（可选）',
        type: 'acm/oop/kaggle',
        language: '建议的编程语言 (python/cpp/java/c)',
        time_limit: 1000,
        memory_limit: 128,
      },
    })

    if (res) {
      isEdit.value = false
      resetForm()
      form.value = {
        title: res.title,
        content: res.content,
        language: res.language || 'python',
        type: res.type || 'acm',
        time_limit: res.time_limit || 1000,
        memory_limit: res.memory_limit || 128,
        template_code: res.template_code || '',
      }
      aiDialogVisible.value = false
      dialogVisible.value = true
      ElMessage.success('题目已生成，请预览并确认')
    }
  } catch (error) {
    ElMessage.error('AI 生成失败')
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

// AI Test Data Handlers
const handleAiTestData = async (row) => {
  aiTestDataVisible.value = true
  fetchingDetail.value = true
  aiStep.value = 0
  generatedScript.value = ''
  generatedLanguage.value = 'python'
  executionResult.value = null
  testDataForm.value = {
    direction: '',
    count: 10,
    range_info: '',
  }

  try {
    // Fetch full problem details from /api/problems/id
    currentProblem.value = await getProblemDetail(row.id)
  } catch (error) {
    ElMessage.error('获取题目详情失败')
    aiTestDataVisible.value = false
  } finally {
    fetchingDetail.value = false
  }
}

const handleGenerateScript = async () => {
  scriptGenerating.value = true
  try {
    const type = currentProblem.value.type
    const language = currentProblem.value.language || 'All'

    const modeConfigs = {
      acm: {
        role: '测试数据生成专家',
        task: '编写一个 Python 脚本，用于生成随机的输入数据（.in）和对应的标准答案（.out）。并直接放置在原始文件夹下',
        rule: `脚本应循环生成${testDataForm.value.count}组测试数据的测试点文件。`,
      },
      oop: {
        role: '自动化测试专家',
        task: '编写一个单元测试脚本，用于验证学生提交的代码实现。',
        rule: `【重要】脚本必须包含/导入学生的代码。
        - 对于 C++: 使用 #include \"solution.cpp\"
        - 对于 Java: 假设学生类在同包下直接调用，或使用 import Solution;
        - 对于 Python: 使用 from solution import *
        严禁在脚本中自行实现题目要求的类，必须测试外部导入的实现。最后一行必须只打印一个 0-100 的整数分数。`,
      },
      kaggle: {
        role: '数据科学竞赛裁判',
        task: '编写一个评估脚本，用于对比学生的预测结果 and 已有的标准答案。',
        rule: '【重要】严禁在脚本中生成随机数据 or 创建 truth.csv。脚本应假设当前目录下已存在 truth.csv（老师上传）和 submission.csv（学生上传）。脚本只需读取这两个文件，计算指标（如 Accuracy/MSE），最后一行只打印一个 0-100 的整数分数。',
      },
    }

    const config = modeConfigs[type] || modeConfigs.acm

    const systemSetting = `你是一个专业的${config.role}。
    当前题目类型：${type.toUpperCase()}
    题目目标语言：${language}

    任务目标：${config.task}

    具体要求：
    1. 语言：${type === 'oop' ? '使用 ' + language : '使用 Python'}。
    2. 逻辑：${config.rule}
    3. 输出控制：你可以打印调试日志，但脚本执行的最后一行输出必须且只能是一个整数（0-100），代表得分。
    4. 依赖：尽量使用基础库（如 csv, math, json），如果使用 pandas 或 sklearn，请确保逻辑简洁。`

    const res = await askLLM({
      system_setting: systemSetting,
      prompt: `题目内容: ${JSON.stringify(currentProblem.value)}\n生成要求: ${testDataForm.value.direction || '执行标准评估逻辑'}\n数据范围/参考: ${testDataForm.value.range_info || '无'}`,
      output_format: {
        code: '生成的完整代码字符串',
        language: '脚本使用的编程语言 (python/java/cpp/c)',
      },
    })

    generatedScript.value = res.code || ''
    generatedLanguage.value = res.language || (currentProblem.value.type === 'oop' ? (currentProblem.value.language || 'java') : 'python')
    aiStep.value = 1
  } catch (error) {
    ElMessage.error('生成脚本失败')
  } finally {
    scriptGenerating.value = false
  }
}

const handleExecuteScript = async () => {
  executing.value = true
  aiStep.value = 2
  try {
    const res = await executeAndSubmitTestData({
      problem_id: currentProblem.value.id,
      code: generatedScript.value,
      type: currentProblem.value.type,
      language: currentProblem.value.language,
    })
    executionResult.value = res
    ElMessage.success('测试数据生成并提交成功')
  } catch (error) {
    ElMessage.error('执行失败')
    aiStep.value = 1 // Go back to script step if failed
  } finally {
    executing.value = false
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

.test-cases-section {
  margin-top: 20px;
  padding-top: 10px;
  border-top: 1px dashed var(--el-border-color);
}

.script-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
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

.script-editor {
  height: 450px;
}

.execution-status {
  padding: 40px 0;
  text-align: center;
}

.loading-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
  color: var(--el-text-color-secondary);
}

.loading-box .el-icon {
  font-size: 40px;
}
</style>
