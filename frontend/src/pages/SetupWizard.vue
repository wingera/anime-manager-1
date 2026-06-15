<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useSetupStore } from '../stores/setup'

const setupStore = useSetupStore()
const router = useRouter()

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

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}

async function loadStatus(): Promise<void> {
  try {
    await setupStore.fetchStatus()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '读取安装状态失败'))
  }
}

async function saveSetup(): Promise<void> {
  try {
    await setupStore.saveSetup({ ...form })
    ElMessage.success('安装向导已完成')
    void router.push('/')
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '保存安装向导失败'))
  }
}

onMounted(() => {
  void loadStatus()
})
</script>

<template>
  <section class="setup-page">
    <div class="page-heading">
      <div>
        <h2>首次安装向导</h2>
        <p>填写影视资料、下载器和目录配置后，再进入日常整理流程。</p>
      </div>
      <el-button :loading="setupStore.saving" type="primary" @click="saveSetup">保存</el-button>
    </div>

    <el-alert
      v-if="setupStore.status && !setupStore.status.installed"
      class="setup-alert"
      type="warning"
      title="还有必要配置未完成"
      :description="setupStore.status.missing_items.join('、')"
      show-icon
      :closable="false"
    />

    <el-form label-position="top" class="setup-form" :model="form" @submit.prevent="saveSetup">
      <el-card class="setup-section">
        <template #header>TMDB 设置</template>
        <el-form-item label="TMDB API 密钥" required>
          <el-input
            v-model="form.tmdb_api_key"
            type="password"
            show-password
            autocomplete="new-password"
            placeholder="请输入 TMDB API 密钥"
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
      </el-card>

      <el-card class="setup-section">
        <template #header>qBittorrent 设置</template>
        <el-form-item label="地址" required>
          <el-input v-model="form.qbittorrent_url" placeholder="http://127.0.0.1:8080" />
        </el-form-item>
        <div class="field-grid">
          <el-form-item label="用户名" required>
            <el-input v-model="form.qbittorrent_username" autocomplete="username" />
          </el-form-item>
          <el-form-item label="密码" required>
            <el-input
              v-model="form.qbittorrent_password"
              type="password"
              show-password
              autocomplete="new-password"
            />
          </el-form-item>
        </div>
      </el-card>

      <el-card class="setup-section">
        <template #header>目录与匹配</template>
        <div class="field-grid">
          <el-form-item label="下载目录" required>
            <el-input v-model="form.download_dir" placeholder="/downloads" />
          </el-form-item>
          <el-form-item label="媒体库目录" required>
            <el-input v-model="form.media_library_dir" placeholder="/media" />
          </el-form-item>
        </div>
        <el-form-item label="匹配阈值" required>
          <el-input-number v-model="form.matching_threshold" :min="0" :max="100" :step="1" />
        </el-form-item>
      </el-card>

      <div class="bottom-actions">
        <el-button :loading="setupStore.saving" type="primary" @click="saveSetup">保存</el-button>
      </div>
    </el-form>
  </section>
</template>

<style scoped>
.setup-page {
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

.setup-alert {
  margin-bottom: 16px;
}

.setup-form {
  display: grid;
  gap: 16px;
  min-width: 0;
}

.setup-section {
  border-radius: 8px;
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
  .page-heading {
    display: block;
  }

  .page-heading .el-button,
  .bottom-actions .el-button {
    width: 100%;
  }

  .field-grid {
    grid-template-columns: 1fr;
  }
}
</style>
