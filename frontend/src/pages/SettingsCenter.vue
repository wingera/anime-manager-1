<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'
import { useSettingsStore } from '../stores/settings'
import type { ConnectionTestResponse, SettingsUpdateRequest } from '../types/settings'

const settingsStore = useSettingsStore()
const testingTmdb = ref(false)
const testingQbittorrent = ref(false)
const testingNas115 = ref(false)

const form = reactive({
  tmdb_api_key: '',
  tmdb_language: 'zh-CN',
  tmdb_region: 'CN',
  qbittorrent_url: '',
  qbittorrent_username: '',
  qbittorrent_password: '',
  download_provider: 'qbittorrent' as 'qbittorrent' | 'nas115',
  cloud115_enabled: false,
  cloud115_service_url: 'http://192.168.1.19:9527',
  cloud115_service_token: '',
  download_dir: '/downloads',
  media_library_dir: '/media',
  matching_threshold: 85,
  tmdb_include_adult: false,
  metadata_proxy_type: 'none' as 'none' | 'http' | 'socks5',
  metadata_proxy_host: '',
  metadata_proxy_port: 1080,
  metadata_proxy_username: '',
  metadata_proxy_password: ''
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
  form.download_provider = settings.download_provider
  form.cloud115_enabled = settings.cloud115_enabled
  form.cloud115_service_url = settings.cloud115_service_url ?? 'http://192.168.1.19:9527'
  form.cloud115_service_token = ''
  form.download_dir = settings.download_dir
  form.media_library_dir = settings.media_library_dir
  form.matching_threshold = settings.matching_threshold
  form.tmdb_include_adult = settings.tmdb_include_adult
  form.metadata_proxy_type = settings.metadata_proxy_type
  form.metadata_proxy_host = settings.metadata_proxy_host ?? ''
  form.metadata_proxy_port = settings.metadata_proxy_port ?? 1080
  form.metadata_proxy_username = settings.metadata_proxy_username ?? ''
  form.metadata_proxy_password = ''
}

async function loadSettings(): Promise<void> {
  try {
    await settingsStore.fetchSettings()
    fillForm()
  } catch {
    // 错误内容由页面内 alert 展示，避免加载时同时弹出重复提示。
  }
}

function buildPayload(): SettingsUpdateRequest {
  const payload: SettingsUpdateRequest = {
    tmdb_language: form.tmdb_language,
    tmdb_region: form.tmdb_region,
    qbittorrent_url: form.qbittorrent_url,
    qbittorrent_username: form.qbittorrent_username,
    download_provider: form.download_provider,
    cloud115_enabled: form.cloud115_enabled,
    cloud115_service_url: form.cloud115_service_url,
    download_dir: form.download_dir,
    media_library_dir: form.media_library_dir,
    matching_threshold: form.matching_threshold,
    tmdb_include_adult: form.tmdb_include_adult,
    metadata_proxy_type: form.metadata_proxy_type,
    metadata_proxy_host: form.metadata_proxy_host,
    metadata_proxy_port: form.metadata_proxy_port,
    metadata_proxy_username: form.metadata_proxy_username
  }

  if (form.tmdb_api_key !== '') {
    payload.tmdb_api_key = form.tmdb_api_key
  }
  if (form.qbittorrent_password !== '') {
    payload.qbittorrent_password = form.qbittorrent_password
  }
  if (form.cloud115_service_token !== '') {
    payload.cloud115_service_token = form.cloud115_service_token
  }
  if (form.metadata_proxy_password !== '') {
    payload.metadata_proxy_password = form.metadata_proxy_password
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

function savedLabel(saved: boolean | undefined, savedText: string, emptyText: string): string {
  return saved ? savedText : emptyText
}

function savedTagType(saved: boolean | undefined): 'success' | 'info' {
  return saved ? 'success' : 'info'
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

async function testNas115(): Promise<void> {
  testingNas115.value = true
  try {
    showTestResult(await settingsStore.testNas115())
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : 'NAS 115 连接测试失败')
  } finally {
    testingNas115.value = false
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
            <el-tag size="small" :type="savedTagType(settingsStore.settings?.has_tmdb_api_key)">
              {{ savedLabel(settingsStore.settings?.has_tmdb_api_key, '已保存密钥', '未填写密钥') }}
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
        <el-form-item label="成人内容搜索">
          <el-switch v-model="form.tmdb_include_adult" active-text="允许" inactive-text="不允许" />
        </el-form-item>
        <el-alert
          v-if="form.tmdb_include_adult"
          class="settings-inline-alert"
          type="warning"
          title="开启后 TMDB 搜索会包含成人内容结果，仅影响资料候选搜索。"
          show-icon
          :closable="false"
        />
        <el-button :loading="testingTmdb" @click="testTmdb">测试 TMDB</el-button>
      </el-card>

      <el-card class="settings-section">
        <template #header>
          <div class="section-header">
            <span>资料与来源代理</span>
            <el-tag
              size="small"
              :type="form.metadata_proxy_type === 'none' ? 'info' : 'success'"
            >
              {{ form.metadata_proxy_type === 'none' ? '未启用' : '已启用' }}
            </el-tag>
          </div>
        </template>

        <el-alert
          class="settings-inline-alert"
          type="info"
          title="代理仅用于 TMDB 和来源抓取，不影响 qBittorrent、NAS 115、入库和本地文件操作。"
          show-icon
          :closable="false"
        />
        <el-form-item label="代理类型">
          <el-radio-group v-model="form.metadata_proxy_type">
            <el-radio-button label="none">关闭</el-radio-button>
            <el-radio-button label="http">HTTP</el-radio-button>
            <el-radio-button label="socks5">SOCKS5</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <div class="field-grid">
          <el-form-item label="主机">
            <el-input
              v-model="form.metadata_proxy_host"
              :disabled="form.metadata_proxy_type === 'none'"
              placeholder="127.0.0.1"
            />
          </el-form-item>
          <el-form-item label="端口">
            <el-input-number
              v-model="form.metadata_proxy_port"
              :disabled="form.metadata_proxy_type === 'none'"
              :min="1"
              :max="65535"
              :step="1"
            />
          </el-form-item>
        </div>
        <div class="field-grid">
          <el-form-item label="用户名">
            <el-input
              v-model="form.metadata_proxy_username"
              :disabled="form.metadata_proxy_type === 'none'"
              autocomplete="username"
              placeholder="可留空"
            />
          </el-form-item>
          <el-form-item label="密码">
            <el-input
              v-model="form.metadata_proxy_password"
              :disabled="form.metadata_proxy_type === 'none'"
              type="password"
              show-password
              autocomplete="new-password"
              placeholder="可留空；已保存的密码不会显示"
            />
          </el-form-item>
        </div>
        <el-tag
          size="small"
          :type="savedTagType(settingsStore.settings?.has_metadata_proxy_password)"
        >
          {{
            savedLabel(
              settingsStore.settings?.has_metadata_proxy_password,
              '已保存代理密码',
              '未填写代理密码'
            )
          }}
        </el-tag>
      </el-card>

      <el-card class="settings-section">
        <template #header>
          <div class="section-header">
            <span>qBittorrent 设置</span>
            <el-tag
              size="small"
              :type="savedTagType(settingsStore.settings?.has_qbittorrent_password)"
            >
              {{
                savedLabel(
                  settingsStore.settings?.has_qbittorrent_password,
                  '已保存密码',
                  '未填写密码'
                )
              }}
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
        <template #header>
          <div class="section-header">
            <span>下载器类型</span>
            <el-tag size="small" :type="form.download_provider === 'nas115' ? 'success' : 'info'">
              {{ form.download_provider === 'nas115' ? 'NAS 115' : 'qBittorrent' }}
            </el-tag>
          </div>
        </template>

        <el-form-item label="下载器类型">
          <el-radio-group v-model="form.download_provider">
            <el-radio-button label="qbittorrent">qBittorrent</el-radio-button>
            <el-radio-button label="nas115">NAS 115</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-alert
          class="settings-inline-alert"
          type="info"
          title="NAS 115 服务运行在你的 NAS Docker 中，当前项目只调用该服务提供的本地接口，授权信息会加密保存。"
          show-icon
          :closable="false"
        />

        <el-form-item label="启用 NAS 115 服务">
          <el-switch v-model="form.cloud115_enabled" active-text="启用" inactive-text="关闭" />
        </el-form-item>
        <el-form-item label="NAS 115 服务地址">
          <el-input v-model="form.cloud115_service_url" placeholder="http://192.168.1.19:9527" />
        </el-form-item>
        <el-form-item label="NAS 115 服务令牌">
          <el-input
            v-model="form.cloud115_service_token"
            type="password"
            show-password
            autocomplete="new-password"
            placeholder="可留空；已保存的令牌不会显示，输入新令牌后保存"
          />
        </el-form-item>
        <div class="section-footer">
          <el-tag
            size="small"
            :type="savedTagType(settingsStore.settings?.has_cloud115_service_token)"
          >
            {{
              savedLabel(
                settingsStore.settings?.has_cloud115_service_token,
                '已保存令牌',
                '未填写令牌'
              )
            }}
          </el-tag>
          <el-button :loading="testingNas115" @click="testNas115">
            测试 NAS 115
          </el-button>
        </div>
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

.settings-inline-alert {
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

.section-footer {
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
  .section-header,
  .section-footer {
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
