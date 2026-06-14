<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useFileAnalysisStore } from '../stores/fileAnalysis'
import type { DownloadFile, DownloadFileType } from '../types/fileAnalysis'

const route = useRoute()
const fileAnalysisStore = useFileAnalysisStore()
const downloadId = computed(() => Number(route.query.download_id ?? 0))

const fileTypeOptions: Array<{ label: string; value: DownloadFileType }> = [
  { label: '正片', value: 'video' },
  { label: '字幕', value: 'subtitle' },
  { label: '图片', value: 'image' },
  { label: '样片', value: 'sample' },
  { label: '文档', value: 'document' },
  { label: '其他', value: 'other' },
  { label: '未知', value: 'unknown' }
]

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}

function formatSize(size: number): string {
  if (size >= 1024 * 1024 * 1024) return `${(size / 1024 / 1024 / 1024).toFixed(2)} GB`
  if (size >= 1024 * 1024) return `${(size / 1024 / 1024).toFixed(2)} MB`
  if (size >= 1024) return `${(size / 1024).toFixed(2)} KB`
  return `${size} B`
}

function typeLabel(type: string): string {
  return fileTypeOptions.find((option) => option.value === type)?.label ?? '未知'
}

async function loadFiles(): Promise<void> {
  if (!downloadId.value) {
    ElMessage.warning('请先从下载队列选择下载任务')
    return
  }
  try {
    await fileAnalysisStore.fetchFiles(downloadId.value)
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '读取文件清单失败'))
  }
}

async function analyzeFiles(): Promise<void> {
  if (!downloadId.value) {
    ElMessage.warning('请先从下载队列选择下载任务')
    return
  }
  try {
    await fileAnalysisStore.analyzeFiles(downloadId.value)
    ElMessage.success('文件分析完成')
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '分析文件失败'))
  }
}

async function saveFile(file: DownloadFile): Promise<void> {
  try {
    await fileAnalysisStore.saveFile(file.id, {
      selected: file.selected,
      file_type: file.file_type,
      season_number: file.season_number,
      episode_number: file.episode_number
    })
    ElMessage.success('文件修改已保存')
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '保存文件修改失败'))
  }
}

async function applyPriority(): Promise<void> {
  if (!downloadId.value) {
    ElMessage.warning('请先从下载队列选择下载任务')
    return
  }
  try {
    await fileAnalysisStore.applyPriority(downloadId.value)
    ElMessage.success('文件优先级已应用')
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '应用文件优先级失败'))
  }
}

onMounted(() => {
  void loadFiles()
})
</script>

<template>
  <section class="analysis-page">
    <div class="page-heading">
      <div>
        <h2>文件分析</h2>
        <p>读取下载器文件清单，确认正片、字幕、样片和下载优先级。</p>
      </div>
      <div class="heading-actions">
        <el-button :loading="fileAnalysisStore.loading" @click="loadFiles">刷新</el-button>
        <el-button type="primary" :loading="fileAnalysisStore.analyzing" @click="analyzeFiles">
          分析文件
        </el-button>
        <el-button type="success" :loading="fileAnalysisStore.applying" @click="applyPriority">
          应用优先级
        </el-button>
      </div>
    </div>

    <el-alert
      v-if="fileAnalysisStore.errorMessage"
      class="page-alert"
      type="error"
      :title="fileAnalysisStore.errorMessage"
      show-icon
      :closable="false"
    />

    <el-empty
      v-if="!fileAnalysisStore.loading && fileAnalysisStore.files.length === 0"
      description="暂无文件清单，请点击分析文件"
    />

    <div v-else class="file-list" v-loading="fileAnalysisStore.loading">
      <article v-for="file in fileAnalysisStore.files" :key="file.id" class="file-card">
        <div class="file-card__header">
          <h3>{{ file.name }}</h3>
          <el-tag>{{ typeLabel(file.file_type) }}</el-tag>
        </div>

        <dl class="file-meta">
          <div>
            <dt>文件大小</dt>
            <dd>{{ formatSize(file.size) }}</dd>
          </div>
          <div>
            <dt>文件编号</dt>
            <dd>{{ file.file_index }}</dd>
          </div>
          <div>
            <dt>当前优先级</dt>
            <dd>{{ file.priority }}</dd>
          </div>
          <div>
            <dt>分析分</dt>
            <dd>{{ file.analysis_score }}</dd>
          </div>
        </dl>

        <div class="file-controls">
          <el-checkbox v-model="file.selected">选择下载</el-checkbox>
          <el-select v-model="file.file_type" aria-label="文件类型">
            <el-option
              v-for="option in fileTypeOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
          <el-input-number v-model="file.season_number" :min="0" :controls="false" placeholder="季号" />
          <el-input-number v-model="file.episode_number" :min="1" :controls="false" placeholder="集号" />
          <el-button
            type="primary"
            plain
            :loading="fileAnalysisStore.savingFileId === file.id"
            @click="saveFile(file)"
          >
            保存修改
          </el-button>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.analysis-page {
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

.heading-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.heading-actions .el-button {
  margin-left: 0;
}

.page-alert {
  margin-bottom: 16px;
}

.file-list {
  display: grid;
  gap: 16px;
  min-width: 0;
}

.file-card {
  min-width: 0;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  background: #ffffff;
}

.file-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.file-card__header h3 {
  min-width: 0;
  margin: 0;
  overflow-wrap: anywhere;
  color: #111827;
  font-size: 17px;
  line-height: 1.5;
}

.file-meta {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin: 16px 0;
}

.file-meta dt {
  color: #6b7280;
  font-size: 13px;
}

.file-meta dd {
  margin: 4px 0 0;
  overflow-wrap: anywhere;
  color: #111827;
}

.file-controls {
  display: grid;
  grid-template-columns: 120px minmax(140px, 1fr) 120px 120px auto;
  align-items: center;
  gap: 12px;
}

.file-controls .el-button {
  margin-left: 0;
}

@media (max-width: 980px) {
  .file-meta,
  .file-controls {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .page-heading {
    flex-direction: column;
  }

  .heading-actions,
  .heading-actions .el-button,
  .file-controls,
  .file-controls .el-button {
    width: 100%;
  }

  .file-meta,
  .file-controls {
    grid-template-columns: 1fr;
  }
}
</style>
