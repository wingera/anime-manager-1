<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useDashboardStore } from '../stores/dashboard'
import type { OperationLog, OperationLogLevel } from '../types/logs'

const dashboardStore = useDashboardStore()
const router = useRouter()

const summary = computed(() => dashboardStore.summary)

const statusCards = computed(() => [
  { label: '来源数量', value: summary.value?.sources_count ?? 0 },
  { label: '资源数量', value: summary.value?.source_items_count ?? 0 },
  { label: '匹配数量', value: summary.value?.matches_count ?? 0 },
  { label: '已确认匹配', value: summary.value?.confirmed_matches_count ?? 0 },
  { label: '下载任务', value: summary.value?.downloads_count ?? 0 },
  { label: '文件分析', value: summary.value?.download_files_count ?? 0 },
  { label: '命名预览', value: summary.value?.rename_previews_count ?? 0 },
  { label: '入库记录', value: summary.value?.imports_count ?? 0 },
  { label: '失败入库', value: summary.value?.failed_imports_count ?? 0 }
])

const quickLinks = [
  { label: '来源管理', path: '/sources' },
  { label: '资源库', path: '/resources' },
  { label: '下载队列', path: '/downloads' },
  { label: '文件分析', path: '/analysis' },
  { label: '命名预览', path: '/preview' },
  { label: '入库记录', path: '/imports' },
  { label: '系统设置', path: '/settings' }
]

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
  const labels: Record<string, string> = {
    settings: '系统设置',
    sources: '来源管理',
    matching: '资料匹配',
    downloads: '下载队列',
    analysis: '文件分析',
    imports: '入库记录'
  }
  return labels[module] ?? module
}

function formatTime(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'short',
    timeStyle: 'short'
  }).format(new Date(value))
}

function logKey(log: OperationLog): string {
  return `${log.id}-${log.created_at}`
}

async function loadSummary(): Promise<void> {
  try {
    await dashboardStore.fetchSummary()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '读取任务看板失败'))
  }
}

function openPath(path: string): void {
  void router.push(path)
}

onMounted(() => {
  void loadSummary()
})
</script>

<template>
  <section class="dashboard-page">
    <div class="page-heading">
      <div>
        <h2>任务看板</h2>
        <p>集中查看来源、资源、匹配、下载、分析、命名预览和入库状态。</p>
      </div>
      <el-button :loading="dashboardStore.loading" @click="loadSummary">刷新</el-button>
    </div>

    <el-alert
      v-if="dashboardStore.errorMessage"
      class="dashboard-alert"
      type="error"
      :title="dashboardStore.errorMessage"
      show-icon
      :closable="false"
    />

    <div class="status-grid" v-loading="dashboardStore.loading">
      <article v-for="card in statusCards" :key="card.label" class="status-card">
        <span>{{ card.label }}</span>
        <strong>{{ card.value }}</strong>
      </article>
    </div>

    <section class="quick-section">
      <div class="section-heading">
        <h3>常用入口</h3>
      </div>
      <div class="quick-links">
        <el-button
          v-for="link in quickLinks"
          :key="link.path"
          type="primary"
          plain
          @click="openPath(link.path)"
        >
          {{ link.label }}
        </el-button>
      </div>
    </section>

    <section class="logs-section">
      <div class="section-heading">
        <h3>最近运行日志</h3>
        <el-button text type="primary" @click="openPath('/logs')">查看全部</el-button>
      </div>

      <el-empty
        v-if="!dashboardStore.loading && (summary?.latest_logs.length ?? 0) === 0"
        description="暂无运行日志"
      />

      <div v-else class="latest-log-list">
        <article
          v-for="log in summary?.latest_logs ?? []"
          :key="logKey(log)"
          class="latest-log"
        >
          <div class="latest-log__meta">
            <el-tag size="small" :type="getLevelType(log.level)">
              {{ getLevelLabel(log.level) }}
            </el-tag>
            <span>{{ getModuleLabel(log.module) }}</span>
            <time :datetime="log.created_at">{{ formatTime(log.created_at) }}</time>
          </div>
          <p>{{ log.message }}</p>
          <small>{{ log.detail || '暂无详细信息' }}</small>
        </article>
      </div>
    </section>
  </section>
</template>

<style scoped>
.dashboard-page {
  width: 100%;
  max-width: 1180px;
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

.dashboard-alert {
  margin-bottom: 16px;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  min-width: 0;
}

.status-card {
  min-width: 0;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  background: #ffffff;
}

.status-card span {
  display: block;
  color: #6b7280;
  line-height: 1.4;
}

.status-card strong {
  display: block;
  margin-top: 10px;
  color: #111827;
  font-size: 28px;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}

.quick-section,
.logs-section {
  margin-top: 24px;
  min-width: 0;
}

.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.section-heading h3 {
  margin: 0;
  color: #111827;
  font-size: 18px;
  line-height: 1.4;
}

.quick-links {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  min-width: 0;
}

.latest-log-list {
  display: grid;
  gap: 12px;
  min-width: 0;
}

.latest-log {
  min-width: 0;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 14px 16px;
  background: #ffffff;
}

.latest-log__meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.5;
}

.latest-log p {
  margin: 10px 0 4px;
  overflow-wrap: anywhere;
  color: #111827;
  line-height: 1.5;
}

.latest-log small {
  display: block;
  overflow-wrap: anywhere;
  color: #6b7280;
  line-height: 1.6;
}

@media (max-width: 900px) {
  .status-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .page-heading {
    display: block;
  }

  .page-heading .el-button {
    width: 100%;
    margin-top: 12px;
  }

  .status-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .quick-links .el-button {
    width: 100%;
    margin-left: 0;
  }
}
</style>
