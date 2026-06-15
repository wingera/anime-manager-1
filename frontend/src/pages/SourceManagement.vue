<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { useSourcesStore } from '../stores/sources'
import type { SourceFormPayload, SourcePreviewItem, SourceSite, SourceType } from '../types/sources'

const sourcesStore = useSourcesStore()
const dialogVisible = ref(false)
const editingSourceId = ref<number | null>(null)
const selectedPreviewItems = ref<SourcePreviewItem[]>([])
const legalPermissionConfirmed = ref(false)

const emptyForm = (): SourceFormPayload => ({
  name: '',
  url: '',
  source_type: 'webpage',
  enabled: false,
  auth_note: '',
  fetch_interval_minutes: 60,
  hash_pattern: '',
  title_cleanup_rules: ''
})

const form = reactive<SourceFormPayload>(emptyForm())

const dialogTitle = computed(() => (editingSourceId.value === null ? '新增来源' : '编辑来源'))
const previewSourceName = computed(() => {
  const source = sourcesStore.sources.find((item) => item.id === sourcesStore.previewSourceId)
  return source?.name ?? '当前来源'
})

function resetForm(): void {
  Object.assign(form, emptyForm())
  editingSourceId.value = null
}

function openCreateDialog(): void {
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(source: SourceSite): void {
  editingSourceId.value = source.id
  Object.assign(form, {
    name: source.name,
    url: source.url,
    source_type: source.source_type,
    enabled: source.enabled,
    auth_note: source.auth_note,
    fetch_interval_minutes: source.fetch_interval_minutes,
    hash_pattern: source.hash_pattern,
    title_cleanup_rules: source.title_cleanup_rules
  })
  dialogVisible.value = true
}

function getSourceTypeLabel(sourceType: SourceType): string {
  const labels: Record<SourceType, string> = {
    webpage: '网页',
    manual: '手动录入',
    rss: 'RSS 订阅'
  }
  return labels[sourceType]
}

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}

async function loadSources(): Promise<void> {
  try {
    await sourcesStore.fetchSources()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '读取来源失败'))
  }
}

async function submitForm(): Promise<void> {
  try {
    const source = await sourcesStore.saveSource({ ...form }, editingSourceId.value ?? undefined)
    dialogVisible.value = false
    ElMessage.success(editingSourceId.value === null ? '来源已创建' : '来源已更新')
    editingSourceId.value = source.id
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '保存来源失败'))
  }
}

async function toggleSource(source: SourceSite, enabled: boolean): Promise<void> {
  try {
    await sourcesStore.updateSource(source.id, { enabled })
    ElMessage.success(enabled ? '来源已启用' : '来源已停用')
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '更新来源状态失败'))
  }
}

async function removeSource(source: SourceSite): Promise<void> {
  try {
    await ElMessageBox.confirm(`确认删除来源“${source.name}”？`, '删除来源', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await sourcesStore.removeSource(source.id)
    ElMessage.success('来源已删除')
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error(getErrorMessage(error, '删除来源失败'))
  }
}

async function testSource(source: SourceSite): Promise<void> {
  try {
    const result = await sourcesStore.testSource(source.id)
    selectedPreviewItems.value = []
    legalPermissionConfirmed.value = false
    ElMessage.success(result.message)
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '来源测试失败'))
  }
}

function handlePreviewSelectionChange(items: SourcePreviewItem[]): void {
  selectedPreviewItems.value = items
}

async function addSelectedPreviewItems(): Promise<void> {
  if (sourcesStore.previewSourceId === null || selectedPreviewItems.value.length === 0) {
    ElMessage.warning('请先选择要加入资源库的资源')
    return
  }
  if (!legalPermissionConfirmed.value) {
    ElMessage.warning('请先确认该来源和资源具有合法访问、下载和整理权限')
    return
  }
  try {
    const result = await sourcesStore.addPreviewItems(
      sourcesStore.previewSourceId,
      selectedPreviewItems.value,
      legalPermissionConfirmed.value
    )
    ElMessage.success(`资源已加入资源库，新增 ${result.created_count} 个，跳过 ${result.skipped_count} 个`)
    selectedPreviewItems.value = []
    legalPermissionConfirmed.value = false
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '加入资源库失败'))
  }
}

onMounted(() => {
  void loadSources()
})
</script>

<template>
  <section class="sources-page">
    <div class="page-heading">
      <div>
        <h2>来源管理</h2>
        <p>维护你已获得授权的来源，测试时只解析资源指纹并展示预览。</p>
      </div>
      <el-button type="primary" @click="openCreateDialog">新增来源</el-button>
    </div>

    <el-alert
      v-if="sourcesStore.errorMessage"
      class="source-alert"
      type="error"
      :title="sourcesStore.errorMessage"
      show-icon
      :closable="false"
    />

    <el-empty
      v-if="!sourcesStore.loading && sourcesStore.sources.length === 0"
      description="暂无来源，请手动新增已授权来源"
    >
      <el-button type="primary" @click="openCreateDialog">新增来源</el-button>
    </el-empty>

    <div v-else class="source-list" v-loading="sourcesStore.loading">
      <article v-for="source in sourcesStore.sources" :key="source.id" class="source-card">
        <div class="source-card__main">
          <div class="source-title-row">
            <h3>{{ source.name }}</h3>
            <el-tag :type="source.enabled ? 'success' : 'info'" size="small">
              {{ source.enabled ? '已启用' : '已停用' }}
            </el-tag>
          </div>
          <p class="source-url">{{ source.url }}</p>
          <dl class="source-meta">
            <div>
              <dt>来源类型</dt>
              <dd>{{ getSourceTypeLabel(source.source_type) }}</dd>
            </div>
            <div>
              <dt>抓取间隔</dt>
              <dd>{{ source.fetch_interval_minutes }} 分钟</dd>
            </div>
            <div>
              <dt>授权备注</dt>
              <dd>{{ source.auth_note || '未填写' }}</dd>
            </div>
            <div>
              <dt>最后检查</dt>
              <dd>{{ source.last_checked_at ? source.last_checked_at : '尚未检查' }}</dd>
            </div>
          </dl>
        </div>
        <div class="source-actions">
          <el-switch
            :model-value="source.enabled"
            active-text="启用"
            inactive-text="停用"
            @change="(value: boolean | string | number) => toggleSource(source, Boolean(value))"
          />
          <el-button :loading="sourcesStore.testing" @click="testSource(source)">测试来源</el-button>
          <el-button @click="openEditDialog(source)">编辑</el-button>
          <el-button type="danger" plain @click="removeSource(source)">删除</el-button>
        </div>
      </article>
    </div>

    <section v-if="sourcesStore.previewSourceId !== null" class="preview-section">
      <div class="section-heading">
        <div>
          <h3>测试结果</h3>
          <p>
            {{ previewSourceName }} 共识别到 {{ sourcesStore.previewFoundCount }} 个资源指纹，当前显示前
            {{ sourcesStore.previewItems.length }} 个。
          </p>
        </div>
        <div class="preview-actions">
          <el-checkbox v-model="legalPermissionConfirmed" class="permission-confirm">
            我确认该来源和资源具有合法访问、下载和整理权限。
          </el-checkbox>
          <el-button
            type="primary"
            :disabled="selectedPreviewItems.length === 0 || !legalPermissionConfirmed"
            :loading="sourcesStore.saving"
            @click="addSelectedPreviewItems"
          >
            加入资源库
          </el-button>
        </div>
      </div>
      <el-alert
        v-if="sourcesStore.previewWarningMessage"
        class="preview-warning"
        type="warning"
        :title="sourcesStore.previewWarningMessage"
        show-icon
        :closable="false"
      />
      <div class="table-wrap">
        <el-table
          :data="sourcesStore.previewItems"
          empty-text="未识别到资源指纹"
          @selection-change="handlePreviewSelectionChange"
        >
          <el-table-column type="selection" width="48" />
          <el-table-column prop="title" label="标题" min-width="220" />
          <el-table-column prop="url" label="文章链接" min-width="240" />
          <el-table-column prop="published_at" label="发布时间" min-width="180" />
          <el-table-column prop="info_hash" label="资源指纹" min-width="300" />
          <el-table-column prop="magnet_uri" label="磁力入口" min-width="360" />
        </el-table>
      </div>
    </section>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="min(720px, 92vw)">
      <el-form label-position="top" :model="form" @submit.prevent="submitForm">
        <div class="field-grid">
          <el-form-item label="来源名称" required>
            <el-input v-model="form.name" placeholder="请输入来源名称" />
          </el-form-item>
          <el-form-item label="来源类型" required>
            <el-select v-model="form.source_type">
              <el-option label="网页" value="webpage" />
              <el-option label="手动录入" value="manual" />
              <el-option label="RSS 订阅" value="rss" />
            </el-select>
          </el-form-item>
        </div>

        <el-form-item label="来源地址" required>
          <el-input v-model="form.url" placeholder="请输入你已获得授权的来源地址" />
        </el-form-item>

        <div class="field-grid">
          <el-form-item label="是否启用">
            <el-switch v-model="form.enabled" active-text="启用" inactive-text="停用" />
          </el-form-item>
          <el-form-item label="抓取间隔">
            <el-input-number v-model="form.fetch_interval_minutes" :min="1" :step="5" />
          </el-form-item>
        </div>

        <el-form-item label="授权备注">
          <el-input
            v-model="form.auth_note"
            type="textarea"
            :rows="3"
            placeholder="启用来源前必须填写授权备注"
          />
        </el-form-item>

        <el-form-item label="资源指纹规则">
          <el-input v-model="form.hash_pattern" placeholder="可填写自定义识别规则，留空使用默认规则" />
        </el-form-item>

        <el-form-item label="标题清洗规则">
          <el-input
            v-model="form.title_cleanup_rules"
            type="textarea"
            :rows="3"
            placeholder="可填写标题清洗规则，留空不处理"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="sourcesStore.saving" @click="submitForm">保存</el-button>
        </div>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.sources-page {
  width: 100%;
  max-width: 1120px;
  min-width: 0;
}

.page-heading,
.section-heading {
  display: flex;
  align-items: center;
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
.section-heading p {
  margin: 6px 0 0;
  color: #6b7280;
  line-height: 1.6;
}

.source-alert {
  margin-bottom: 16px;
}

.source-list {
  display: grid;
  gap: 16px;
  min-width: 0;
}

.source-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  background: #ffffff;
}

.source-card__main {
  min-width: 0;
}

.source-title-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.source-title-row h3 {
  margin: 0;
  color: #111827;
  font-size: 18px;
  line-height: 1.4;
}

.source-url {
  margin: 8px 0 0;
  overflow-wrap: anywhere;
  color: #4b5563;
  line-height: 1.6;
}

.source-meta {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin: 16px 0 0;
}

.source-meta div {
  min-width: 0;
}

.source-meta dt {
  margin-bottom: 4px;
  color: #6b7280;
  font-size: 13px;
}

.source-meta dd {
  margin: 0;
  overflow-wrap: anywhere;
  color: #111827;
  line-height: 1.5;
}

.source-actions {
  display: flex;
  align-items: flex-end;
  flex-direction: column;
  gap: 10px;
}

.source-actions .el-button {
  margin-left: 0;
}

.preview-section {
  margin-top: 24px;
}

.preview-actions {
  display: flex;
  align-items: flex-end;
  flex-direction: column;
  gap: 10px;
}

.permission-confirm {
  max-width: 360px;
  white-space: normal;
}

.preview-warning {
  margin-bottom: 12px;
}

.table-wrap {
  max-width: 100%;
  overflow-x: auto;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #ffffff;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

:deep(.el-select),
:deep(.el-input),
:deep(.el-input-number),
:deep(.el-textarea) {
  width: 100%;
}

@media (max-width: 860px) {
  .source-card,
  .source-meta,
  .field-grid {
    grid-template-columns: 1fr;
  }

  .source-actions {
    align-items: stretch;
  }
}

@media (max-width: 720px) {
  .page-heading,
  .section-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .page-heading > .el-button,
  .section-heading > .el-button,
  .source-actions .el-button,
  .dialog-footer .el-button {
    width: 100%;
  }

  .dialog-footer {
    flex-direction: column-reverse;
  }
}
</style>
