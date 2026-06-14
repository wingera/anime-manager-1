<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useDownloadsStore } from '../stores/downloads'
import type { DownloadTask } from '../types/downloads'

const downloadsStore = useDownloadsStore()
const router = useRouter()

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    pending: '待提交',
    submitted: '已提交，等待文件分析',
    downloading: '下载中',
    completed: '已完成',
    failed: '已失败',
    missing: '下载器中未找到',
    unknown: '状态未知',
    pausedDL: '已暂停',
    pausedUP: '已暂停',
    stalledDL: '等待下载',
    stalledUP: '等待上传',
    uploading: '做种中',
    checkingDL: '校验中',
    checkingUP: '校验中',
    queuedDL: '排队下载',
    queuedUP: '排队上传',
    error: '下载器报错'
  }
  return labels[status] ?? '下载器状态待识别'
}

function getProgressPercent(progress: number): number {
  return Math.round(Math.max(0, Math.min(progress, 1)) * 100)
}

async function loadDownloads(): Promise<void> {
  try {
    await downloadsStore.fetchDownloads()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '读取下载队列失败'))
  }
}

async function refreshDownload(download: DownloadTask): Promise<void> {
  try {
    await downloadsStore.refreshDownload(download.id)
    ElMessage.success('下载任务状态已刷新')
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '刷新下载任务失败'))
  }
}

async function removeDownload(download: DownloadTask): Promise<void> {
  try {
    await ElMessageBox.confirm(`确认删除“${download.source_title}”的下载任务记录？`, '删除记录', {
      confirmButtonText: '删除记录',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await downloadsStore.removeDownload(download.id)
    ElMessage.success('下载任务记录已删除')
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error(getErrorMessage(error, '删除下载任务记录失败'))
  }
}

function openFileAnalysis(download: DownloadTask): void {
  void router.push({ path: '/analysis', query: { download_id: download.id } })
}

function openRenamePreview(download: DownloadTask): void {
  void router.push({ path: '/preview', query: { download_id: download.id } })
}

onMounted(() => {
  void loadDownloads()
})
</script>

<template>
  <section class="downloads-page">
    <div class="page-heading">
      <div>
        <h2>下载队列</h2>
        <p>查看已手动创建的下载任务，任务提交到 qBittorrent 后会保持暂停。</p>
      </div>
      <el-button :loading="downloadsStore.loading" @click="loadDownloads">刷新</el-button>
    </div>

    <el-alert
      v-if="downloadsStore.errorMessage"
      class="download-alert"
      type="error"
      :title="downloadsStore.errorMessage"
      show-icon
      :closable="false"
    />

    <el-empty
      v-if="!downloadsStore.loading && downloadsStore.downloads.length === 0"
      description="暂无下载任务，请先在资源库为已确认匹配的资源创建任务"
    />

    <div v-else class="download-list" v-loading="downloadsStore.loading">
      <article
        v-for="download in downloadsStore.downloads"
        :key="download.id"
        class="download-card"
      >
        <div class="download-card__main">
          <div class="download-title-row">
            <h3>{{ download.source_title }}</h3>
            <el-tag size="small">{{ getStatusLabel(download.status) }}</el-tag>
          </div>

          <dl class="download-meta">
            <div>
              <dt>磁力入口</dt>
              <dd>{{ download.magnet_uri }}</dd>
            </div>
            <div>
              <dt>保存路径</dt>
              <dd>{{ download.save_path }}</dd>
            </div>
            <div>
              <dt>任务哈希</dt>
              <dd>{{ download.qbittorrent_hash || '下载器尚未返回任务哈希' }}</dd>
            </div>
            <div>
              <dt>错误信息</dt>
              <dd>{{ download.error_message || '暂无错误' }}</dd>
            </div>
          </dl>

          <div class="progress-block">
            <span>进度 {{ getProgressPercent(download.progress) }}%</span>
            <el-progress :percentage="getProgressPercent(download.progress)" />
          </div>
        </div>

        <div class="download-actions">
          <el-button
            :loading="downloadsStore.refreshingId === download.id"
            @click="refreshDownload(download)"
          >
            刷新
          </el-button>
          <el-button type="primary" plain @click="openFileAnalysis(download)">
            文件分析
          </el-button>
          <el-button type="success" plain @click="openRenamePreview(download)">
            命名预览
          </el-button>
          <el-button
            type="danger"
            plain
            :loading="downloadsStore.deletingId === download.id"
            @click="removeDownload(download)"
          >
            删除记录
          </el-button>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.downloads-page {
  width: 100%;
  max-width: 1120px;
  min-width: 0;
}

.page-heading {
  display: flex;
  align-items: center;
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

.download-alert {
  margin-bottom: 16px;
}

.download-list {
  display: grid;
  gap: 16px;
  min-width: 0;
}

.download-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  background: #ffffff;
}

.download-card__main {
  min-width: 0;
}

.download-title-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.download-title-row h3 {
  margin: 0;
  overflow-wrap: anywhere;
  color: #111827;
  font-size: 18px;
  line-height: 1.4;
}

.download-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 16px 0 0;
}

.download-meta div {
  min-width: 0;
}

.download-meta dt {
  margin-bottom: 4px;
  color: #6b7280;
  font-size: 13px;
}

.download-meta dd {
  margin: 0;
  overflow-wrap: anywhere;
  color: #111827;
  line-height: 1.5;
}

.progress-block {
  display: grid;
  gap: 8px;
  margin-top: 16px;
  color: #374151;
  font-size: 14px;
}

.download-actions {
  display: flex;
  align-items: flex-end;
  flex-direction: column;
  gap: 10px;
}

.download-actions .el-button {
  margin-left: 0;
}

@media (max-width: 860px) {
  .download-card,
  .download-meta {
    grid-template-columns: 1fr;
  }

  .download-actions {
    align-items: stretch;
  }
}

@media (max-width: 720px) {
  .page-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .page-heading > .el-button,
  .download-actions .el-button {
    width: 100%;
  }
}
</style>
