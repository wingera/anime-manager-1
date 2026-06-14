<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useFileAnalysisStore } from '../stores/fileAnalysis'
import { useImportsStore } from '../stores/imports'

const route = useRoute()
const router = useRouter()
const fileAnalysisStore = useFileAnalysisStore()
const importsStore = useImportsStore()
const downloadId = computed(() => Number(route.query.download_id ?? 0))

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}

async function loadPreviews(): Promise<void> {
  if (!downloadId.value) {
    ElMessage.warning('请先从下载队列选择下载任务')
    return
  }
  try {
    await fileAnalysisStore.fetchPreviews(downloadId.value)
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '读取命名预览失败'))
  }
}

async function generatePreviews(): Promise<void> {
  if (!downloadId.value) {
    ElMessage.warning('请先从下载队列选择下载任务')
    return
  }
  try {
    await fileAnalysisStore.generatePreviews(downloadId.value)
    ElMessage.success('命名预览已生成')
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '生成命名预览失败'))
  }
}

async function executeImport(): Promise<void> {
  if (!downloadId.value) {
    ElMessage.warning('请先从下载队列选择下载任务')
    return
  }
  try {
    await importsStore.executeForDownload(downloadId.value)
    ElMessage.success('入库执行完成')
    void router.push('/imports')
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '执行入库失败'))
  }
}

onMounted(() => {
  void loadPreviews()
})
</script>

<template>
  <section class="preview-page">
    <div class="page-heading">
      <div>
        <h2>命名预览</h2>
        <p>根据已确认资料匹配生成 Emby 目录结构预览，本页不会执行真实文件操作。</p>
      </div>
      <div class="heading-actions">
        <el-button :loading="fileAnalysisStore.loading" @click="loadPreviews">刷新</el-button>
        <el-button type="primary" :loading="fileAnalysisStore.generating" @click="generatePreviews">
          生成预览
        </el-button>
        <el-button
          type="success"
          :loading="importsStore.executing"
          :disabled="fileAnalysisStore.previews.length === 0"
          @click="executeImport"
        >
          执行入库
        </el-button>
      </div>
    </div>

    <el-alert
      class="page-alert"
      type="warning"
      title="当前只会硬链接或复制到媒体库，不会删除原文件。"
      show-icon
      :closable="false"
    />

    <el-alert
      v-if="fileAnalysisStore.errorMessage"
      class="page-alert"
      type="error"
      :title="fileAnalysisStore.errorMessage"
      show-icon
      :closable="false"
    />

    <el-empty
      v-if="!fileAnalysisStore.loading && fileAnalysisStore.previews.length === 0"
      description="暂无命名预览，请先完成文件分析并生成预览"
    />

    <div v-else class="preview-list" v-loading="fileAnalysisStore.loading">
      <article v-for="preview in fileAnalysisStore.previews" :key="preview.id" class="preview-card">
        <div class="preview-card__header">
          <h3>{{ preview.original_path }}</h3>
          <el-tag :type="preview.conflict ? 'danger' : 'success'">
            {{ preview.conflict ? '存在冲突' : '无冲突' }}
          </el-tag>
        </div>

        <dl class="preview-meta">
          <div>
            <dt>原路径</dt>
            <dd>{{ preview.original_path }}</dd>
          </div>
          <div>
            <dt>目标路径</dt>
            <dd>{{ preview.target_path }}</dd>
          </div>
          <div>
            <dt>警告</dt>
            <dd>{{ preview.warning_message || '暂无警告' }}</dd>
          </div>
        </dl>
      </article>
    </div>
  </section>
</template>

<style scoped>
.preview-page {
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

.preview-list {
  display: grid;
  gap: 16px;
  min-width: 0;
}

.preview-card {
  min-width: 0;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  background: #ffffff;
}

.preview-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.preview-card__header h3 {
  min-width: 0;
  margin: 0;
  overflow-wrap: anywhere;
  color: #111827;
  font-size: 17px;
  line-height: 1.5;
}

.preview-meta {
  display: grid;
  gap: 12px;
  margin: 16px 0 0;
}

.preview-meta dt {
  color: #6b7280;
  font-size: 13px;
}

.preview-meta dd {
  margin: 4px 0 0;
  overflow-wrap: anywhere;
  color: #111827;
  line-height: 1.5;
}

@media (max-width: 720px) {
  .page-heading {
    flex-direction: column;
  }

  .heading-actions,
  .heading-actions .el-button {
    width: 100%;
  }
}
</style>
