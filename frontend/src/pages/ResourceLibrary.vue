<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { useDownloadsStore } from '../stores/downloads'
import { useMatchingStore } from '../stores/matching'
import { useSourcesStore } from '../stores/sources'
import type { MediaMatch, MediaMatchPayload, TmdbCandidate } from '../types/matching'
import type { SourceItem } from '../types/sources'

const sourcesStore = useSourcesStore()
const matchingStore = useMatchingStore()
const downloadsStore = useDownloadsStore()
const matchDialogVisible = ref(false)
const activeItem = ref<SourceItem | null>(null)
const selectedCandidateId = ref<number | null>(null)

const matchForm = reactive<MediaMatchPayload>({
  tmdb_id: null,
  title: null,
  original_title: null,
  year: null,
  season_number: null,
  episode_number: null,
  episode_title: null,
  match_score: 0,
  status: 'confirmed'
})

const matchesByItemId = computed(() => {
  const map = new Map<number, MediaMatch>()
  for (const item of matchingStore.matches) {
    map.set(item.source_item_id, item)
  }
  return map
})

const activeCandidates = computed(() => {
  if (!activeItem.value) return []
  return matchingStore.candidatesByItemId[activeItem.value.id] ?? []
})

const activeSearchQueries = computed(() => {
  if (!activeItem.value) return []
  return matchingStore.searchQueriesByItemId[activeItem.value.id] ?? []
})

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}

function getMatch(itemId: number): MediaMatch | undefined {
  return matchesByItemId.value.get(itemId)
}

function isMatchConfirmed(itemId: number): boolean {
  return getMatch(itemId)?.status === 'confirmed'
}

function getMatchStatus(itemId: number): string {
  const mediaMatch = getMatch(itemId)
  if (!mediaMatch) return '未匹配'
  if (mediaMatch.status === 'confirmed') return '已确认'
  return '待确认'
}

function getSourceItemStatus(status: string): string {
  const labels: Record<string, string> = {
    pending: '待处理',
    pending_review: '待确认',
    pending_download: '待下载',
    downloading: '下载中',
    pending_analysis: '待分析',
    pending_import: '待入库',
    completed: '已完成',
    failed: '已失败'
  }
  return labels[status] ?? '状态待识别'
}

function resetForm(): void {
  Object.assign(matchForm, {
    tmdb_id: null,
    title: null,
    original_title: null,
    year: null,
    season_number: null,
    episode_number: null,
    episode_title: null,
    match_score: 0,
    status: 'confirmed'
  })
  selectedCandidateId.value = null
}

function fillFromMatch(mediaMatch: MediaMatch): void {
  Object.assign(matchForm, {
    tmdb_id: mediaMatch.tmdb_id,
    title: mediaMatch.title,
    original_title: mediaMatch.original_title,
    year: mediaMatch.year,
    season_number: mediaMatch.season_number,
    episode_number: mediaMatch.episode_number,
    episode_title: mediaMatch.episode_title,
    match_score: mediaMatch.match_score,
    status: mediaMatch.status
  })
  selectedCandidateId.value = mediaMatch.tmdb_id
}

function getYearFromCandidate(candidate: TmdbCandidate): number | null {
  if (!candidate.first_air_date) return null
  const year = Number(candidate.first_air_date.slice(0, 4))
  return Number.isFinite(year) ? year : null
}

function applyCandidate(candidate: TmdbCandidate): void {
  selectedCandidateId.value = candidate.tmdb_id
  Object.assign(matchForm, {
    tmdb_id: candidate.tmdb_id,
    title: candidate.title,
    original_title: candidate.original_title,
    year: getYearFromCandidate(candidate),
    match_score: candidate.match_score,
    status: 'confirmed'
  })
}

function openMatchDialog(item: SourceItem): void {
  activeItem.value = item
  resetForm()
  const mediaMatch = getMatch(item.id)
  if (mediaMatch) {
    fillFromMatch(mediaMatch)
  }
  matchDialogVisible.value = true
}

async function searchTmdb(item: SourceItem): Promise<void> {
  try {
    const response = await matchingStore.searchCandidates(item.id)
    openMatchDialog(item)
    if (response.candidates.length > 0) {
      applyCandidate(response.candidates[0])
    }
    ElMessage.success(response.message)
  } catch (error) {
    ElMessage.error(getErrorMessage(error, 'TMDB 搜索失败'))
  }
}

async function saveCurrentMatch(): Promise<void> {
  if (!activeItem.value) return
  try {
    await matchingStore.saveItemMatch(activeItem.value.id, { ...matchForm })
    matchDialogVisible.value = false
    ElMessage.success('匹配信息已保存')
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '保存匹配失败'))
  }
}

async function createDownloadTask(item: SourceItem): Promise<void> {
  if (!isMatchConfirmed(item.id)) {
    ElMessage.warning('请先确认资料匹配')
    return
  }
  try {
    await downloadsStore.createForSourceItem(item.id)
    ElMessage.success('下载任务已创建')
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '创建下载任务失败'))
  }
}

async function loadResources(): Promise<void> {
  try {
    await Promise.all([sourcesStore.fetchSourceItems(), matchingStore.fetchMatches()])
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '读取资源库失败'))
  }
}

onMounted(() => {
  void loadResources()
})
</script>

<template>
  <section class="resource-page">
    <div class="page-heading">
      <div>
        <h2>资源库</h2>
        <p>查看已确认加入的资源指纹，并为每条资源保存电视剧资料匹配结果。</p>
      </div>
      <el-button :loading="sourcesStore.loading || matchingStore.loading" @click="loadResources">
        刷新
      </el-button>
    </div>

    <el-alert
      v-if="sourcesStore.errorMessage || matchingStore.errorMessage"
      class="resource-alert"
      type="error"
      :title="sourcesStore.errorMessage || matchingStore.errorMessage"
      show-icon
      :closable="false"
    />

    <el-empty
      v-if="!sourcesStore.loading && sourcesStore.sourceItems.length === 0"
      description="暂无资源，请先在来源管理中测试来源并加入资源库"
    />

    <div v-else class="resource-list" v-loading="sourcesStore.loading || matchingStore.loading">
      <article v-for="item in sourcesStore.sourceItems" :key="item.id" class="resource-card">
        <div class="resource-card__main">
          <div class="resource-title-row">
            <h3>{{ item.title }}</h3>
            <el-tag size="small">{{ getSourceItemStatus(item.status) }}</el-tag>
            <el-tag :type="getMatch(item.id) ? 'success' : 'warning'" size="small">
              {{ getMatchStatus(item.id) }}
            </el-tag>
          </div>
          <dl class="resource-meta">
            <div>
              <dt>资源指纹</dt>
              <dd>{{ item.info_hash }}</dd>
            </div>
            <div>
              <dt>磁力入口</dt>
              <dd>{{ item.magnet_uri }}</dd>
            </div>
            <div>
              <dt>匹配资料</dt>
              <dd>{{ getMatch(item.id)?.title || '尚未保存匹配' }}</dd>
            </div>
            <div>
              <dt>季集</dt>
              <dd>
                <template v-if="getMatch(item.id)">
                  第 {{ getMatch(item.id)?.season_number ?? '未定' }} 季 /
                  第 {{ getMatch(item.id)?.episode_number ?? '未定' }} 集
                </template>
                <template v-else>尚未确认</template>
              </dd>
            </div>
          </dl>
        </div>
        <div class="resource-actions">
          <el-button
            :loading="matchingStore.searchingItemId === item.id"
            type="primary"
            plain
            @click="searchTmdb(item)"
          >
            搜索 TMDB
          </el-button>
          <el-button @click="openMatchDialog(item)">确认匹配</el-button>
          <el-tooltip
            :disabled="isMatchConfirmed(item.id)"
            content="请先确认资料匹配"
            placement="top"
          >
            <span class="action-tooltip-wrap">
              <el-button
                type="success"
                plain
                :disabled="!isMatchConfirmed(item.id)"
                :loading="downloadsStore.creatingItemId === item.id"
                @click="createDownloadTask(item)"
              >
                创建下载任务
              </el-button>
            </span>
          </el-tooltip>
        </div>
      </article>
    </div>

    <el-dialog v-model="matchDialogVisible" title="确认匹配" width="min(860px, 94vw)">
      <div v-if="activeItem" class="match-dialog">
        <section>
          <h3>当前资源</h3>
          <p>{{ activeItem.title }}</p>
          <p class="hash-text">{{ activeItem.info_hash }}</p>
        </section>

        <section>
          <h3>TMDB 候选</h3>
          <div v-if="activeSearchQueries.length > 0" class="search-query-list">
            <span>搜索词</span>
            <el-tag v-for="query in activeSearchQueries" :key="query" size="small">
              {{ query }}
            </el-tag>
          </div>
          <el-empty v-if="activeCandidates.length === 0" description="暂无候选，可手动填写匹配信息" />
          <el-radio-group v-else v-model="selectedCandidateId" class="candidate-list">
            <label
              v-for="candidate in activeCandidates"
              :key="candidate.tmdb_id"
              class="candidate-card"
              @click="applyCandidate(candidate)"
            >
              <el-radio :label="candidate.tmdb_id">
                <span class="candidate-title">{{ candidate.title }}</span>
              </el-radio>
              <span class="candidate-meta">
                {{ candidate.first_air_date || '首播日期未知' }} · 匹配分 {{ candidate.match_score }}
              </span>
              <span class="candidate-meta">命中搜索词：{{ candidate.search_query }}</span>
              <span class="candidate-overview">{{ candidate.overview || '暂无简介' }}</span>
            </label>
          </el-radio-group>
        </section>

        <el-form label-position="top" :model="matchForm" @submit.prevent="saveCurrentMatch">
          <div class="field-grid">
            <el-form-item label="TMDB 电视编号">
              <el-input-number v-model="matchForm.tmdb_id" :min="0" />
            </el-form-item>
            <el-form-item label="匹配状态">
              <el-select v-model="matchForm.status">
                <el-option label="已确认" value="confirmed" />
                <el-option label="待确认" value="pending" />
              </el-select>
            </el-form-item>
          </div>
          <div class="field-grid">
            <el-form-item label="剧名">
              <el-input v-model="matchForm.title" placeholder="请输入剧名" />
            </el-form-item>
            <el-form-item label="原名">
              <el-input v-model="matchForm.original_title" placeholder="请输入原名" />
            </el-form-item>
          </div>
          <div class="field-grid four">
            <el-form-item label="年份">
              <el-input-number v-model="matchForm.year" :min="0" />
            </el-form-item>
            <el-form-item label="季号">
              <el-input-number v-model="matchForm.season_number" :min="0" />
            </el-form-item>
            <el-form-item label="集号">
              <el-input-number v-model="matchForm.episode_number" :min="0" />
            </el-form-item>
            <el-form-item label="匹配分">
              <el-input-number v-model="matchForm.match_score" :min="0" :max="100" />
            </el-form-item>
          </div>
          <el-form-item label="集名">
            <el-input v-model="matchForm.episode_title" placeholder="暂时无法判断时可留空" />
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="matchDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="matchingStore.saving" @click="saveCurrentMatch">
            保存匹配
          </el-button>
        </div>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.resource-page {
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

.resource-alert {
  margin-bottom: 16px;
}

.resource-list {
  display: grid;
  gap: 16px;
  min-width: 0;
}

.resource-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  background: #ffffff;
}

.resource-card__main {
  min-width: 0;
}

.resource-title-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.resource-title-row h3 {
  margin: 0;
  overflow-wrap: anywhere;
  color: #111827;
  font-size: 18px;
  line-height: 1.4;
}

.resource-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 16px 0 0;
}

.resource-meta div {
  min-width: 0;
}

.resource-meta dt {
  margin-bottom: 4px;
  color: #6b7280;
  font-size: 13px;
}

.resource-meta dd {
  margin: 0;
  overflow-wrap: anywhere;
  color: #111827;
  line-height: 1.5;
}

.resource-actions {
  display: flex;
  align-items: flex-end;
  flex-direction: column;
  gap: 10px;
}

.resource-actions .el-button {
  margin-left: 0;
}

.action-tooltip-wrap {
  display: inline-flex;
}

.match-dialog {
  display: grid;
  gap: 18px;
}

.match-dialog h3 {
  margin: 0 0 8px;
  color: #111827;
  font-size: 16px;
}

.match-dialog p {
  margin: 0 0 6px;
  overflow-wrap: anywhere;
  color: #374151;
  line-height: 1.6;
}

.hash-text {
  color: #6b7280;
  font-size: 13px;
}

.candidate-list {
  display: grid;
  gap: 10px;
  width: 100%;
}

.search-query-list {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
  color: #6b7280;
  font-size: 13px;
}

.candidate-card {
  display: grid;
  gap: 4px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
}

.candidate-card:hover {
  border-color: #409eff;
}

.candidate-title {
  color: #111827;
  font-weight: 600;
}

.candidate-meta,
.candidate-overview {
  display: block;
  overflow-wrap: anywhere;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.5;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.field-grid.four {
  grid-template-columns: repeat(4, minmax(0, 1fr));
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
  .resource-card,
  .resource-meta,
  .field-grid,
  .field-grid.four {
    grid-template-columns: 1fr;
  }

  .resource-actions {
    align-items: stretch;
  }
}

@media (max-width: 720px) {
  .page-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .page-heading > .el-button,
  .resource-actions .el-button,
  .action-tooltip-wrap,
  .dialog-footer .el-button {
    width: 100%;
  }

  .action-tooltip-wrap :deep(.el-button) {
    width: 100%;
  }

  .dialog-footer {
    flex-direction: column-reverse;
  }
}
</style>
