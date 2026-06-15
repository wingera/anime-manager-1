<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { onMounted } from 'vue'
import { useDiagnosticsStore } from '../stores/diagnostics'
import type { DiagnosticStatus } from '../types/diagnostics'

const diagnosticsStore = useDiagnosticsStore()

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}

function statusLabel(status: DiagnosticStatus): string {
  const labels: Record<DiagnosticStatus, string> = {
    ok: '正常',
    warning: '提醒',
    error: '异常'
  }
  return labels[status]
}

function tagType(status: DiagnosticStatus): 'success' | 'warning' | 'danger' {
  if (status === 'error') return 'danger'
  if (status === 'warning') return 'warning'
  return 'success'
}

async function runDiagnostics(): Promise<void> {
  try {
    await diagnosticsStore.fetchDiagnostics()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '系统诊断失败'))
  }
}

onMounted(() => {
  void runDiagnostics()
})
</script>

<template>
  <section class="diagnostics-page">
    <div class="page-heading">
      <div>
        <h2>系统诊断</h2>
        <p>检查目录、外部工具、下载器配置、资料库配置、数据库和密钥状态。</p>
      </div>
      <el-button :loading="diagnosticsStore.loading" type="primary" @click="runDiagnostics">
        重新检查
      </el-button>
    </div>

    <el-alert
      v-if="diagnosticsStore.errorMessage"
      class="diagnostics-alert"
      type="error"
      :title="diagnosticsStore.errorMessage"
      show-icon
      :closable="false"
    />

    <el-empty
      v-if="!diagnosticsStore.loading && diagnosticsStore.checks.length === 0"
      description="暂无诊断结果"
    />

    <div v-else class="check-list" v-loading="diagnosticsStore.loading">
      <article v-for="check in diagnosticsStore.checks" :key="check.name" class="check-card">
        <div class="check-card__top">
          <h3>{{ check.name }}</h3>
          <el-tag :type="tagType(check.status)">{{ statusLabel(check.status) }}</el-tag>
        </div>
        <p>{{ check.message }}</p>
      </article>
    </div>
  </section>
</template>

<style scoped>
.diagnostics-page {
  width: 100%;
  max-width: 960px;
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

.diagnostics-alert {
  margin-bottom: 16px;
}

.check-list {
  display: grid;
  gap: 12px;
  min-width: 0;
}

.check-card {
  min-width: 0;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  background: #ffffff;
}

.check-card__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.check-card h3 {
  margin: 0;
  overflow-wrap: anywhere;
  color: #111827;
  font-size: 17px;
  line-height: 1.4;
}

.check-card p {
  margin: 10px 0 0;
  overflow-wrap: anywhere;
  color: #374151;
  line-height: 1.7;
}

@media (max-width: 720px) {
  .page-heading {
    display: block;
  }

  .page-heading .el-button {
    width: 100%;
    margin-top: 12px;
  }

  .check-card__top {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
