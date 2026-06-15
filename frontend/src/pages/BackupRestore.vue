<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { ref } from 'vue'
import { useBackupStore } from '../stores/backup'
import type { BackupImportRequest } from '../types/backup'

const backupStore = useBackupStore()
const selectedFileName = ref('')

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}

function downloadJson(filename: string, data: unknown): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

async function exportConfig(): Promise<void> {
  try {
    const data = await backupStore.exportConfig()
    downloadJson(`anime-manager-backup-${new Date().toISOString().slice(0, 10)}.json`, data)
    ElMessage.success('配置备份导出成功')
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '导出配置备份失败'))
  }
}

async function importFile(file: File): Promise<void> {
  selectedFileName.value = file.name
  try {
    const text = await file.text()
    const payload = JSON.parse(text) as BackupImportRequest
    await backupStore.importConfig(payload)
    ElMessage.success('配置备份导入成功')
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '导入配置备份失败，请确认 JSON 文件格式'))
  }
}

function handleFileChange(event: Event): void {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  void importFile(file)
  input.value = ''
}
</script>

<template>
  <section class="backup-page">
    <div class="page-heading">
      <div>
        <h2>备份恢复</h2>
        <p>导出和导入系统配置，密钥和密码不会明文导出。</p>
      </div>
    </div>

    <el-alert
      class="backup-alert"
      type="info"
      title="敏感信息保护"
      description="备份文件只包含密钥和密码是否已设置，不包含 TMDB API 密钥或 qBittorrent 密码明文。"
      show-icon
      :closable="false"
    />

    <div class="action-grid">
      <el-card class="action-card">
        <template #header>导出配置</template>
        <p>导出设置、来源、匹配阈值、下载目录和媒体库目录。</p>
        <el-button type="primary" :loading="backupStore.loading" @click="exportConfig">
          导出 JSON 文件
        </el-button>
      </el-card>

      <el-card class="action-card">
        <template #header>导入配置</template>
        <p>只导入非敏感配置，不导入运行日志、下载任务、入库记录或数据库编号。</p>
        <label class="file-button">
          <input type="file" accept="application/json,.json" @change="handleFileChange" />
          <span>{{ backupStore.importing ? '正在导入' : '选择 JSON 文件导入' }}</span>
        </label>
        <small v-if="selectedFileName">已选择：{{ selectedFileName }}</small>
      </el-card>
    </div>
  </section>
</template>

<style scoped>
.backup-page {
  width: 100%;
  max-width: 960px;
  min-width: 0;
}

.page-heading {
  margin-bottom: 16px;
}

.page-heading h2 {
  margin: 0;
  color: #111827;
  font-size: 24px;
  line-height: 1.3;
}

.page-heading p,
.action-card p {
  margin: 6px 0 0;
  color: #6b7280;
  line-height: 1.6;
}

.backup-alert {
  margin-bottom: 16px;
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  min-width: 0;
}

.action-card {
  min-width: 0;
  border-radius: 8px;
}

.action-card .el-button,
.file-button {
  margin-top: 16px;
}

.file-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 32px;
  border: 1px solid #409eff;
  border-radius: 4px;
  padding: 0 14px;
  color: #409eff;
  cursor: pointer;
  line-height: 1.4;
}

.file-button input {
  display: none;
}

.action-card small {
  display: block;
  margin-top: 10px;
  overflow-wrap: anywhere;
  color: #6b7280;
}

@media (max-width: 720px) {
  .action-grid {
    grid-template-columns: 1fr;
  }

  .action-card .el-button,
  .file-button {
    width: 100%;
  }
}
</style>
