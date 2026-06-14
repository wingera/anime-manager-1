<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'
import { useSettingsStore } from '../stores/settings'
import type { ConnectionTestResponse, SettingsUpdateRequest } from '../types/settings'

const settingsStore = useSettingsStore()
const testingTmdb = ref(false)
const testingQbittorrent = ref(false)

const form = reactive({
  tmdb_api_key: '',
  tmdb_language: 'zh-CN',
  tmdb_region: 'CN',
  qbittorrent_url: '',
  qbittorrent_username: '',
  qbittorrent_password: '',
  download_dir: '/downloads',
  media_library_dir: '/media',
  matching_threshold: 85
})

function fillForm(): void {
  const settings = settingsStore.settings
  if (!settings) return

  form.tmdb_api_key = ''
  form.tmdb_language = settings.tmdb_language
  form.tmdb_region = settings.tmdb_region
  form.qbittorrent_url = settings.qbittorrent_url ?? ''
  form.qbittorrent_username = settings.qbittorrent_username ?? ''
  form.qbittorrent_password = ''
  form.download_dir = settings.download_dir
  form.media_library_dir = settings.media_library_dir
  form.matching_threshold = settings.matching_threshold
}

async function loadSettings(): Promise<void> {
  try {
    await settingsStore.fetchSettings()
    fillForm()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取设置失败')
  }
}

function buildPayload(): SettingsUpdateRequest {
  const payload: SettingsUpdateRequest = {
    tmdb_language: form.tmdb_language,
    tmdb_region: form.tmdb_region,
    qbittorrent_url: form.qbittorrent_url,
    qbittorrent_username: form.qbittorrent_username,
    download_dir: form.download_dir,
    media_library_dir: form.media_library_dir,
    matching_threshold: form.matching_threshold
  }

  if (form.tmdb_api_key !== '') {
    payload.tmdb_api_key = form.tmdb_api_key
  }
  if (form.qbittorrent_password !== '') {
    payload.qbittorrent_password = form.qbittorrent_password
  }

  return payload
}

async function saveSettings(): Promise<void> {
  try {
    await settingsStore.saveSettings(buildPayload())
    fillForm()
    ElMessage.success('设置已保存')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '保存设置失败')
  }
}

function showTestResult(result: ConnectionTestResponse): void {
  if (result.success) {
    ElMessage.success(result.message)
    return
  }
  ElMessage.error(result.message)
}

async function testTmdb(): Promise<void> {
  testingTmdb.value = true
  try {
    showTestResult(await settingsStore.testTmdb())
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : 'TMDB 连接测试失败')
  } finally {
    testingTmdb.value = false
  }
}

async function testQbittorrent(): Promise<void> {
  testingQbittorrent.value = true
  try {
    showTestResult(await settingsStore.testQbittorrent())
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : 'qBittorrent 连接测试失败')
  } finally {
    testingQbittorrent.value = false
  }
}

onMounted(() => {
  void loadSettings()
})
</script>

<template>
  <section class="settings-page">
    <div class="page-heading">
      <div>
        <h2>设置中心</h2>
        <p>保存影视资料、下载器和媒体库目录配置。</p>
      </div>
      <el-button type="primary" :loading="settingsStore.loading" @click="saveSettings">
        保存
      </el-button>
    </div>

    <el-alert
      v-if="settingsStore.errorMessage"
      class="settings-alert"
      type="error"
      :title="settingsStore.errorMessage"
      show-icon
      :closable="false"
    />

    <el-form
      label-position="top"
      class="settings-form"
      :model="form"
      @submit.prevent="saveSettings"
    >
      <el-card class="settings-section">
        <template #header>
          <div class="section-header">
            <span>TMDB 设置</span>
            <el-tag size="small" :type="settingsStore.settings?.has_tmdb_api_key ? 'success' : 'info'">
              {{ settingsStore.settings?.has_tmdb_api_key ? '已保存密钥' : '未填写密钥' }}
            </el-tag>
          </div>
        </template>

        <el-form-item label="TMDB API 密钥">
          <el-input
            v-model="form.tmdb_api_key"
            type="password"
            show-password
            autocomplete="new-password"
            placeholder="已保存的密钥不会显示，输入新密钥后保存"
          />
        </el-form-item>
        <div class="field-grid">
          <el-form-item label="语言">
            <el-input v-model="form.tmdb_language" placeholder="zh-CN" />
          </el-form-item>
          <el-form-item label="地区">
            <el-input v-model="form.tmdb_region" placeholder="CN" />
          </el-form-item>
        </div>
        <el-button :loading="testingTmdb" @click="testTmdb">测试 TMDB</el-button>
      </el-card>

      <el-card class="settings-section">
        <template #header>
          <div class="section-header">
            <span>qBittorrent 设置</span>
            <el-tag
              size="small"
              :type="settingsStore.settings?.has_qbittorrent_password ? 'success' : 'info'"
            >
              {{ settingsStore.settings?.has_qbittorrent_password ? '已保存密码' : '未填写密码' }}
            </el-tag>
          </div>
        </template>

        <el-form-item label="地址">
          <el-input v-model="form.qbittorrent_url" placeholder="http://127.0.0.1:8080" />
        </el-form-item>
        <div class="field-grid">
          <el-form-item label="用户名">
            <el-input v-model="form.qbittorrent_username" autocomplete="username" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input
              v-model="form.qbittorrent_password"
              type="password"
              show-password
              autocomplete="new-password"
              placeholder="已保存的密码不会显示，输入新密码后保存"
            />
          </el-form-item>
        </div>
        <el-button :loading="testingQbittorrent" @click="testQbittorrent">
          测试 qBittorrent
        </el-button>
      </el-card>

      <el-card class="settings-section">
        <template #header>媒体库设置</template>
        <div class="field-grid">
          <el-form-item label="下载目录">
            <el-input v-model="form.download_dir" placeholder="/downloads" />
          </el-form-item>
          <el-form-item label="媒体库目录">
            <el-input v-model="form.media_library_dir" placeholder="/media" />
          </el-form-item>
        </div>
        <el-form-item label="自动匹配阈值">
          <el-input-number v-model="form.matching_threshold" :min="0" :max="100" :step="1" />
        </el-form-item>
      </el-card>

      <div class="bottom-actions">
        <el-button type="primary" :loading="settingsStore.loading" @click="saveSettings">
          保存
        </el-button>
      </div>
    </el-form>
  </section>
</template>

<style scoped>
.settings-page {
  width: 100%;
  max-width: 960px;
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

.settings-alert {
  margin-bottom: 16px;
}

.settings-form {
  display: grid;
  gap: 16px;
  min-width: 0;
}

.settings-section {
  border-radius: 8px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.bottom-actions {
  display: flex;
  justify-content: flex-end;
}

:deep(.el-input),
:deep(.el-input-number) {
  width: 100%;
}

@media (max-width: 720px) {
  .page-heading,
  .section-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .page-heading > .el-button,
  .bottom-actions .el-button {
    width: 100%;
  }

  .field-grid {
    grid-template-columns: 1fr;
  }
}
</style>
