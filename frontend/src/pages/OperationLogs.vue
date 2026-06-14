<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { computed, onMounted } from 'vue'
import { useLogsStore } from '../stores/logs'
import type { OperationLog, OperationLogLevel } from '../types/logs'

const logsStore = useLogsStore()

const moduleOptions = [
  { label: '全部模块', value: '' },
  { label: '系统设置', value: 'settings' },
  { label: '来源管理', value: 'sources' },
  { label: '资料匹配', value: 'matching' },
  { label: '下载队列', value: 'downloads' },
  { label: '文件分析', value: 'analysis' },
  { label: '入库记录', value: 'imports' }
]

const selectedModule = computed({
  get: () => logsStore.selectedModule,
  set: (value: string) => {
    void loadLogs(value)
  }
})

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}

function getLevelLabel(level: OperationLogLevel): string {
  const labels: Record<OperationLogLevel, string> = {
    info: '信息',
    warning: '警告',
    error: '错误'
  }
  return labels[level] ?? '信息'
}

function getLevelType(level: OperationLogLevel): 'success' | 'warning' | 'danger' {
  if (level === 'error') return 'danger'
  if (level === 'warning') return 'warning'
  return 'success'
}

function getModuleLabel(module: string): string {
  return moduleOptions.find((item) => item.value === module)?.label ?? module
}

function formatTime(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'medium'
  }).format(new Date(value))
}

async function loadLogs(module = logsStore.selectedModule): Promise<void> {
  try {
    await logsStore.fetchLogs(module)
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '读取运行日志失败'))
  }
}

function logKey(log: OperationLog): string {
  return `${log.id}-${log.created_at}`
}

onMounted(() => {
  void loadLogs()
})
</script>

<template>
  <section class="logs-page">
    <div class="page-heading">
      <div>
        <h2>运行日志</h2>
        <p>查看系统关键操作记录，日志不会展示密钥、密码或完整敏感链接。</p>
      </div>
      <div class="toolbar">
        <el-select v-model="selectedModule" class="module-select" aria-label="模块筛选">
          <el-option
            v-for="option in moduleOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
        <el-button :loading="logsStore.loading" @click="loadLogs()">刷新</el-button>
      </div>
    </div>

    <el-alert
      v-if="logsStore.errorMessage"
      class="logs-alert"
      type="error"
      :title="logsStore.errorMessage"
      show-icon
      :closable="false"
    />

    <el-empty
      v-if="!logsStore.loading && logsStore.logs.length === 0"
      description="暂无运行日志"
    />

    <div v-else class="log-list" v-loading="logsStore.loading">
      <article v-for="log in logsStore.logs" :key="logKey(log)" class="log-card">
        <div class="log-card__top">
          <div class="log-card__tags">
            <el-tag size="small" :type="getLevelType(log.level)">
              {{ getLevelLabel(log.level) }}
            </el-tag>
            <el-tag size="small" effect="plain">{{ getModuleLabel(log.module) }}</el-tag>
          </div>
          <time :datetime="log.created_at">{{ formatTime(log.created_at) }}</time>
        </div>
        <h3>{{ log.message }}</h3>
        <p>{{ log.detail || '暂无详细信息' }}</p>
      </article>
    </div>
  </section>
</template>

<style scoped>
.logs-page {
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

.toolbar {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 12px;
  min-width: 0;
}

.module-select {
  width: 180px;
  max-width: 100%;
}

.logs-alert {
  margin-bottom: 16px;
}

.log-list {
  display: grid;
  gap: 12px;
  min-width: 0;
}

.log-card {
  min-width: 0;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  background: #ffffff;
}

.log-card__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.log-card__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  min-width: 0;
}

.log-card time {
  flex: 0 0 auto;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.5;
}

.log-card h3 {
  margin: 12px 0 6px;
  overflow-wrap: anywhere;
  color: #111827;
  font-size: 17px;
  line-height: 1.4;
}

.log-card p {
  margin: 0;
  overflow-wrap: anywhere;
  color: #374151;
  line-height: 1.7;
}

@media (max-width: 720px) {
  .page-heading {
    display: block;
  }

  .toolbar {
    justify-content: stretch;
    margin-top: 12px;
  }

  .module-select,
  .toolbar .el-button {
    width: 100%;
  }

  .log-card__top {
    display: block;
  }

  .log-card time {
    display: block;
    margin-top: 10px;
  }
}
</style>
