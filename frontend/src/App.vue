<template>
  <el-container class="layout">
    <el-aside width="240px" class="sidebar">
      <h1>番剧自动整理管家</h1>
      <el-menu default-active="dashboard">
        <el-menu-item index="dashboard">任务看板</el-menu-item>
        <el-menu-item index="sources">来源管理</el-menu-item>
        <el-menu-item index="matching">匹配中心</el-menu-item>
        <el-menu-item index="downloads">下载队列</el-menu-item>
        <el-menu-item index="analysis">文件分析</el-menu-item>
        <el-menu-item index="preview">命名预览</el-menu-item>
        <el-menu-item index="imports">入库记录</el-menu-item>
        <el-menu-item index="settings">系统设置</el-menu-item>
        <el-menu-item index="logs">运行日志</el-menu-item>
      </el-menu>
    </el-aside>
    <el-main>
      <el-card>
        <template #header>开工前检查</template>
        <p>当前骨架已完成标准目录、健康检查接口、页面入口、数据库初始结构和样例数据。</p>
        <p>下一步先完成系统设置页，再接入下载器连接测试和影视资料访问测试。</p>
      </el-card>
    </el-main>
  </el-container>
</template>

<style scoped>
.layout {
  min-height: 100vh;
}
.sidebar {
  border-right: 1px solid #e5e7eb;
  padding: 16px;
}
h1 {
  font-size: 18px;
  margin: 0 0 16px;
}
</style>
