<script setup>
/**
 * 题目标签面板：在题目标题下展示当前题目的标签，
 * 教师可挂 / 摘标签；普通用户可建议。
 *
 * 数据流：
 * - onMounted 同时拉题目已贴标签 / 全站可选标签。
 * - 教师贴：approved=true 立即生效；普通用户：approved=false 进入审批。
 */
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/request'
import { useUserStore } from '@/stores/user'

const props = defineProps({
  problemId: { type: Number, required: true }
})

const loading = ref(false)
const attached = ref([])        // 当前题目已贴标签
const all = ref([])              // 全站标签
const attachDialogVisible = ref(false)
const selectedTagId = ref(null)
const approved = ref(false)

const userStore = useUserStore()
const isTeacher = computed(() => userStore.user?.role === 'teacher')

async function load () {
  loading.value = true
  try {
    const [a, b] = await Promise.all([
      request({ url: `/tags/problems/${props.problemId}`, method: 'get' }),
      request({ url: `/tags`, method: 'get' })
    ])
    attached.value = a || []
    all.value = b || []
  } catch (e) {
    ElMessage.error(e.message || '加载标签失败')
  } finally {
    loading.value = false
  }
}

watch(() => props.problemId, () => load(), { immediate: false })
onMounted(load)

function openAttach () {
  selectedTagId.value = null
  approved.value = isTeacher.value
  attachDialogVisible.value = true
}

async function confirmAttach () {
  if (!selectedTagId.value) {
    ElMessage.warning('请选择标签')
    return
  }
  try {
    await request({
      url: `/tags/problems/${props.problemId}/attach`,
      method: 'post',
      data: { tag_id: selectedTagId.value, approved: approved.value }
    })
    ElMessage.success(isTeacher.value ? '标签已挂上' : '已提交建议，等待教师审核')
    attachDialogVisible.value = false
    load()
  } catch (e) {
    ElMessage.error(e.message || '操作失败')
  }
}

async function detach (tag) {
  try {
    await ElMessageBox.confirm(`从该题目移除标签「${tag.name}」？`, '确认移除', { type: 'warning' })
    await request({
      url: `/tags/problems/${props.problemId}/${tag.id}`,
      method: 'delete'
    })
    ElMessage.success('已移除')
    load()
  } catch (e) {
    if (e !== 'cancel' && e?.message !== 'cancel') {
      ElMessage.error(e.message || '移除失败')
    }
  }
}
</script>

<template>
  <div class="tag-panel">
    <div class="tag-list">
      <el-tag
        v-for="t in attached"
        :key="t.id"
        :type="t.category === '基础' ? 'success' : 'info'"
        size="small"
        :closable="isTeacher"
        @close="detach(t)"
      >
        {{ t.name }}
      </el-tag>
      <el-button link size="small" type="primary" @click="openAttach">
        <el-icon><Plus /></el-icon>
        <span style="margin-left: 4px">添加标签</span>
      </el-button>
    </div>

    <el-dialog v-model="attachDialogVisible" title="添加标签" width="480px">
      <el-form label-position="top">
        <el-form-item label="选择标签">
          <el-select v-model="selectedTagId" placeholder="搜索标签" filterable style="width: 100%">
            <el-option
              v-for="t in all.filter(x => !attached.find(a => a.id === x.id))"
              :key="t.id"
              :label="t.name + (t.category ? ` (${t.category})` : '')"
              :value="t.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="!isTeacher">
          <el-checkbox v-model="approved">
            作为教师认证标签（仅教师可勾选）
          </el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="attachDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmAttach">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.tag-panel {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}
.tag-list {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}
</style>
