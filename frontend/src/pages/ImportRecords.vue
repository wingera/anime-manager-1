<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, ref } from 'vue'
import { useImportsStore } from '../stores/imports'
import type { ImportActionStatus, ImportActionType, ImportJob, ImportJobStatus } from '../types/imports'

const importsStore = useImportsStore()
const detailVisible = ref(false)

const statusText: Record<ImportJobStatus | ImportActionStatus, string> = {
  pending: '待处理',
  completed: '已完成',
  failed: '已失败',
  rolled_back: '已回滚'
}

const statusTag: Record<ImportJobStatus | ImportActionStatus, 'info' | 'success' | 'danger' | 'warning'> = {
  pending: 'info',
  completed: 'success',
  failed: 'danger',
  rolled_back: 'warning'
}

const modeText: Record<ImportActionType, string> = {
  hardlink: '硬链接',
  copy: '复制'
}

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}

function formatTime(value: string): string {
  return new Date(value).toLocaleString('zh-CN')
}

async function loadImports(): Promise<void> {
  try {
    await importsStore.fetchImports()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '读取入库记录失败'))
  }
}

async function openDetail(importJob: ImportJob): Promise<void> {
  detailVisible.value = true
  try {
    await importsStore.fetchDetail(importJob.id)
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '读取入库详情失败'))
  }
}

async function rollback(importJob: ImportJob): Promise<void> {
  try {
    await ElMessageBox.confirm('回滚只会删除本系统创建的媒体库目标文件，不会删除原文件。', '确认回滚入库', {
      confirmButtonText: '确认回滚',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await importsStore.rollback(importJob.id)
    ElMessage.success('入库回滚完成')
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error(getErrorMessage(error, '入库回滚失败'))
  }
}

onMounted(() => {
  void loadImports()
})
</script>

<template>
  <section class="imports-page">
    <div class="page-heading">
      <div>
        <h2>入库记录</h2>
        <p>查看手动执行的入库任务、文件动作和回滚状态。</p>
      </div>
      <el-button :loading="importsStore.loading" @click="loadImports">刷新</el-button>
    </div>

    <el-alert
      v-if="importsStore.errorMessage"
      class="page-alert"
      type="error"
      :title="importsStore.errorMessage"
      show-icon
      :closable="false"
    />

    <el-empty
      v-if="!importsStore.loading && importsStore.imports.length === 0"
      description="暂无入库记录"
    />

    <div v-else class="table-wrap" v-loading="importsStore.loading">
      <el-table :data="importsStore.imports" class="records-table">
        <el-table-column prop="id" label="入库任务 id" min-width="110" />
        <el-table-column prop="download_task_id" label="下载任务 id" min-width="110" />
        <el-table-column label="状态" min-width="110">
          <template #default="{ row }">
            <el-tag :type="statusTag[row.status as ImportJobStatus]">
              {{ statusText[row.status as ImportJobStatus] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="入库方式" min-width="100">
          <template #default="{ row }">{{ modeText[row.mode as ImportActionType] }}</template>
        </el-table-column>
        <el-table-column prop="total_files" label="总文件数" min-width="90" />
        <el-table-column prop="completed_files" label="完成文件数" min-width="100" />
        <el-table-column label="错误信息" min-width="180">
          <template #default="{ row }">
            <span class="path-text">{{ row.error_message || '无' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" min-width="150">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button size="small" @click="openDetail(row)">查看详情</el-button>
              <el-button
                size="small"
                type="warning"
                :loading="importsStore.rollingBackId === row.id"
                :disabled="row.status === 'rolled_back'"
                @click="rollback(row)"
              >
                回滚
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-drawer v-model="detailVisible" title="入库详情" size="min(720px, 100%)">
      <div v-loading="importsStore.detailLoading" class="detail-panel">
        <dl v-if="importsStore.currentJob" class="job-summary">
          <div>
            <dt>入库任务 id</dt>
            <dd>{{ importsStore.currentJob.id }}</dd>
          </div>
          <div>
            <dt>下载任务 id</dt>
            <dd>{{ importsStore.currentJob.download_task_id }}</dd>
          </div>
          <div>
            <dt>状态</dt>
            <dd>{{ statusText[importsStore.currentJob.status] }}</dd>
          </div>
          <div>
            <dt>入库方式</dt>
            <dd>{{ modeText[importsStore.currentJob.mode] }}</dd>
          </div>
        </dl>

        <div class="action-list">
          <article v-for="action in importsStore.actions" :key="action.id" class="action-item">
            <div class="action-item__header">
              <strong>文件动作 {{ action.id }}</strong>
              <el-tag :type="statusTag[action.status]">{{ statusText[action.status] }}</el-tag>
            </div>
            <dl class="action-meta">
              <div>
                <dt>源路径</dt>
                <dd>{{ action.source_path }}</dd>
              </div>
              <div>
                <dt>目标路径</dt>
                <dd>{{ action.target_path }}</dd>
              </div>
              <div>
                <dt>动作类型</dt>
                <dd>{{ modeText[action.action_type] }}</dd>
              </div>
              <div>
                <dt>错误信息</dt>
                <dd>{{ action.error_message || '无' }}</dd>
              </div>
            </dl>
          </article>
        </div>
      </div>
    </el-drawer>
  </section>
</template>

<style scoped>
.imports-page {
  width: 100%;
  max-width: 1120px;
  min-width: 0;
}

.page-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.page-heading h2 {
  margin: 0;
  color: #111827;
  font-size: 24px;
  line-height: 1.3;
}

.page-heading p {
  margin: 6px 0 0;
  color: #6b7280;
  line-height: 1.6;
}

.page-alert {
  margin-bottom: 16px;
}

.table-wrap {
  max-width: 100%;
  overflow-x: auto;
}

.records-table {
  min-width: 920px;
}

.row-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.row-actions .el-button {
  margin-left: 0;
}

.path-text,
.action-meta dd {
  overflow-wrap: anywhere;
  word-break: break-word;
}

.detail-panel {
  min-width: 0;
}

.job-summary,
.action-meta {
  display: grid;
  gap: 12px;
  margin: 0;
}

.job-summary {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-bottom: 16px;
}

.job-summary dt,
.action-meta dt {
  color: #6b7280;
  font-size: 13px;
}

.job-summary dd,
.action-meta dd {
  margin: 4px 0 0;
  color: #111827;
  line-height: 1.5;
}

.action-list {
  display: grid;
  gap: 12px;
}

.action-item {
  min-width: 0;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 14px;
  background: #ffffff;
}

.action-item__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

@media (max-width: 720px) {
  .page-heading {
    flex-direction: column;
  }

  .page-heading .el-button {
    width: 100%;
  }

  .job-summary {
    grid-template-columns: 1fr;
  }
}
</style>
