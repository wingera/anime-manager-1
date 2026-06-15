<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, reactive } from 'vue'
import { useRoute } from 'vue-router'
import { useDownloadsStore } from '../stores/downloads'
import { useRenameStore } from '../stores/rename'
import type { RenameRuleUpdateRequest } from '../types/rename'

const route = useRoute()
const renameStore = useRenameStore()
const downloadsStore = useDownloadsStore()
const taskId = computed(() => Number(route.query.download_id ?? 0))
const currentDownload = computed(() =>
  downloadsStore.downloads.find((download) => download.id === taskId.value)
)
const isNas115Task = computed(() => currentDownload.value?.provider === 'nas115')
const applyButtonText = computed(() =>
  isNas115Task.value ? '执行 115 网盘重命名' : '执行重命名'
)

const form = reactive({
  enabled: false,
  auto_execute: false,
  name_template: '{clean_title} - {episode}{ext}',
  episode_padding: 2,
  remove_words: ''
})

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}

function fillRuleForm(): void {
  if (!renameStore.rule) return
  form.enabled = renameStore.rule.enabled
  form.auto_execute = renameStore.rule.auto_execute
  form.name_template = renameStore.rule.name_template
  form.episode_padding = renameStore.rule.episode_padding
  form.remove_words = renameStore.rule.remove_words
}

function actionStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    completed: '已完成',
    failed: '已失败',
    rolled_back: '已回滚'
  }
  return labels[status] ?? '待确认'
}

function previewStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    pending: '待执行',
    renamed: '已重命名',
    failed: '已失败',
    rolled_back: '已回滚'
  }
  return labels[status] ?? '待确认'
}

async function loadPage(): Promise<void> {
  try {
    await renameStore.fetchRule()
    await downloadsStore.fetchDownloads()
    fillRuleForm()
    if (taskId.value) await renameStore.fetchTask(taskId.value)
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '读取自动重命名信息失败'))
  }
}

function buildPayload(): RenameRuleUpdateRequest {
  return {
    enabled: form.enabled,
    auto_execute: form.auto_execute,
    name_template: form.name_template,
    episode_padding: form.episode_padding,
    remove_words: form.remove_words
  }
}

async function saveRule(): Promise<void> {
  try {
    await renameStore.saveRule(buildPayload())
    fillRuleForm()
    ElMessage.success('自动重命名规则已保存')
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '保存自动重命名规则失败'))
  }
}

async function generatePreview(): Promise<void> {
  if (!taskId.value) {
    ElMessage.warning('请先从下载队列选择下载任务')
    return
  }
  try {
    await renameStore.generatePreviews(taskId.value)
    await renameStore.fetchTask(taskId.value)
    ElMessage.success('重命名预览已生成')
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '生成重命名预览失败'))
  }
}

async function applyRename(): Promise<void> {
  if (!taskId.value) {
    ElMessage.warning('请先从下载队列选择下载任务')
    return
  }
  try {
    await ElMessageBox.confirm(
      '确认执行无冲突且可信度达标的重命名预览？',
      applyButtonText.value,
      {
        confirmButtonText: '执行',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await renameStore.applyRename(taskId.value)
    ElMessage.success('重命名执行完成')
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error(getErrorMessage(error, '执行重命名失败'))
  }
}

async function runAutoRenameNow(): Promise<void> {
  if (!taskId.value) {
    ElMessage.warning('请先从下载队列选择下载任务')
    return
  }
  try {
    await renameStore.runAutoRename(taskId.value)
    ElMessage.success('自动重命名已触发')
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '触发自动重命名失败'))
  }
}

async function rollbackAction(actionId: number): Promise<void> {
  if (!taskId.value) return
  try {
    await ElMessageBox.confirm('确认尝试回滚这个重命名动作？', '回滚重命名', {
      confirmButtonText: '回滚',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await renameStore.rollback(actionId, taskId.value)
    ElMessage.success('重命名动作已回滚')
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error(getErrorMessage(error, '回滚重命名失败'))
  }
}

onMounted(() => {
  void loadPage()
})
</script>

<template>
  <section class="rename-page">
    <div class="page-heading">
      <div>
        <h2>自动重命名</h2>
        <p>下载完成后先生成预览，只有无冲突且规则可信时才会执行重命名。</p>
      </div>
      <el-button type="primary" :loading="renameStore.saving" @click="saveRule">保存规则</el-button>
    </div>

    <el-alert
      class="rename-alert"
      type="warning"
      title="当前项目未发现稳定的 115 重命名客户端时，执行会记录失败原因，不会删除或覆盖文件。"
      show-icon
      :closable="false"
    />

    <el-alert
      v-if="isNas115Task"
      class="rename-alert"
      type="info"
      title="该操作会调用 NAS 上的 115 服务重命名网盘文件，不会删除文件。"
      show-icon
      :closable="false"
    />

    <el-alert
      v-if="renameStore.errorMessage"
      class="rename-alert"
      type="error"
      :title="renameStore.errorMessage"
      show-icon
      :closable="false"
    />

    <el-form label-position="top" class="rule-form" :model="form" @submit.prevent="saveRule">
      <section class="settings-band">
        <div class="switch-grid">
          <el-form-item label="启用自动重命名">
            <el-switch v-model="form.enabled" active-text="启用" inactive-text="关闭" />
          </el-form-item>
          <el-form-item label="下载完成后自动执行">
            <el-switch v-model="form.auto_execute" active-text="执行" inactive-text="只预览" />
          </el-form-item>
        </div>
        <el-form-item label="命名模板">
          <el-input v-model="form.name_template" />
          <p class="field-help">
            可用变量：{title}、{clean_title}、{original_name}、{episode}、{episode_raw}、{ext}
          </p>
        </el-form-item>
        <div class="field-grid">
          <el-form-item label="集数位数">
            <el-input-number v-model="form.episode_padding" :min="1" :max="4" />
          </el-form-item>
          <el-form-item label="移除词">
            <el-input v-model="form.remove_words" placeholder="多个词用英文逗号分隔" />
          </el-form-item>
        </div>
      </section>
    </el-form>

    <section class="task-band">
      <div class="section-heading">
        <div>
          <h3>任务重命名预览</h3>
          <p>{{ taskId ? `当前下载任务编号：${taskId}` : '请从下载队列进入具体任务。' }}</p>
        </div>
        <div class="heading-actions">
          <el-button :disabled="!taskId" :loading="renameStore.loading" @click="loadPage">刷新</el-button>
          <el-button
            type="primary"
            plain
            :disabled="!taskId"
            :loading="renameStore.generating"
            @click="generatePreview"
          >
            生成重命名预览
          </el-button>
          <el-button
            type="success"
            plain
            :disabled="!taskId || renameStore.previews.length === 0"
            :loading="renameStore.applying"
            @click="applyRename"
          >
            {{ applyButtonText }}
          </el-button>
          <el-button :disabled="!taskId" :loading="renameStore.applying" @click="runAutoRenameNow">
            手动触发自动流程
          </el-button>
        </div>
      </div>

      <el-table
        class="rename-table"
        :data="renameStore.previews"
        v-loading="renameStore.loading"
        empty-text="暂无重命名预览"
      >
        <el-table-column prop="original_name" label="原文件名" min-width="220" />
        <el-table-column prop="target_name" label="目标文件名" min-width="220" />
        <el-table-column prop="file_type" label="文件类型" width="110" />
        <el-table-column prop="episode_number" label="集数" width="90" />
        <el-table-column prop="confidence" label="可信度" width="100" />
        <el-table-column label="冲突" width="100">
          <template #default="{ row }">
            <el-tag :type="row.conflict ? 'danger' : 'success'">
              {{ row.conflict ? '有冲突' : '无冲突' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">{{ previewStatusLabel(row.status) }}</template>
        </el-table-column>
        <el-table-column prop="warning_message" label="警告" min-width="220" />
      </el-table>
    </section>

    <section class="task-band">
      <div class="section-heading">
        <div>
          <h3>重命名记录</h3>
          <p>仅记录本系统触发的重命名动作，可在安全时尝试改回旧名称。</p>
        </div>
      </div>

      <el-table class="rename-table" :data="renameStore.actions" empty-text="暂无重命名记录">
        <el-table-column prop="old_name" label="旧名称" min-width="220" />
        <el-table-column prop="new_name" label="新名称" min-width="220" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">{{ actionStatusLabel(row.status) }}</template>
        </el-table-column>
        <el-table-column prop="error_message" label="错误原因" min-width="220" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button
              size="small"
              :disabled="row.status !== 'completed'"
              :loading="renameStore.rollingBackId === row.id"
              @click="rollbackAction(row.id)"
            >
              回滚
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </section>
</template>

<style scoped>
.rename-page {
  width: 100%;
  max-width: 1120px;
  min-width: 0;
}

.page-heading,
.section-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.page-heading h2,
.section-heading h3 {
  margin: 0;
  color: #111827;
  line-height: 1.3;
}

.page-heading h2 {
  font-size: 24px;
}

.section-heading h3 {
  font-size: 18px;
}

.page-heading p,
.section-heading p,
.field-help {
  margin: 6px 0 0;
  color: #6b7280;
  line-height: 1.6;
}

.rename-alert {
  margin-bottom: 16px;
}

.settings-band,
.task-band {
  min-width: 0;
  margin-bottom: 18px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  background: #ffffff;
}

.switch-grid,
.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.heading-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.heading-actions .el-button {
  margin-left: 0;
}

.rename-table {
  width: 100%;
}

:deep(.el-table .cell) {
  overflow-wrap: anywhere;
}

@media (max-width: 720px) {
  .page-heading,
  .section-heading {
    flex-direction: column;
  }

  .switch-grid,
  .field-grid {
    grid-template-columns: 1fr;
  }

  .heading-actions,
  .heading-actions .el-button,
  .page-heading .el-button {
    width: 100%;
  }
}
</style>
