<template>
  <div class="app-container">
    <!-- 固定在顶部的导航栏 -->
    <div class="nav-header">
      <div class="nav-buttons">
        <el-button 
          :type="currentTab === 'home' ? 'primary' : 'default'"
          @click="switchTab('home')"
        >
          首页
        </el-button>
        <el-button 
          :type="currentTab === 'brand' ? 'primary' : 'default'"
          @click="switchTab('brand')"
        >
          品牌管理
        </el-button>
        <el-button 
          :type="currentTab === 'status' ? 'primary' : 'default'"
          @click="switchTab('status')"
        >
          商品状态
        </el-button>
        <el-button 
          :type="currentTab === 'user' ? 'primary' : 'default'"
          @click="switchTab('user')"
        >
          用户管理
        </el-button>
        <el-button 
          :type="currentTab === 'stats' ? 'primary' : 'default'"
          @click="switchTab('stats')"
        >
          数据统计
        </el-button>
      </div>
    </div>

    <!-- 主内容区域 -->
    <div class="main-container">
      <div class="content-wrapper">
        <sku-list v-if="currentTab === 'home'" />
        <brand-manage v-else-if="currentTab === 'brand'" />
        <status-changes v-else-if="currentTab === 'status'" />
        <user-manage v-else-if="currentTab === 'user'" />
        <statistics v-else />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import SkuList from './components/SkuList.vue'
import BrandManage from './components/BrandManage.vue'
import StatusChanges from './components/StatusChanges.vue'
import UserManage from './components/UserManage.vue'
import Statistics from './components/Statistics.vue'

const currentTab = ref('home')

const switchTab = (tab: 'home' | 'brand' | 'status' | 'user' | 'stats') => {
  currentTab.value = tab
}
</script>

<style>
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.nav-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 60px;
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  display: flex;
  justify-content: center;
  align-items: center;
}

.nav-buttons {
  display: flex;
  gap: 16px;
}

.main-container {
  margin-top: 60px; /* 与导航栏高度相同 */
  flex: 1;
  background-color: #f5f7fa;
  min-height: calc(100vh - 60px);
}

.content-wrapper {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

:deep(.el-button) {
  min-width: 100px;
}
</style>
