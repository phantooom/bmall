<template>
  <div class="status-changes">
    <div class="header">
      <div class="left-controls">
        <h2>商品状态变更</h2>
        <el-radio-group v-model="statusFilter" size="small">
          <el-radio-button :value="'all'">全部</el-radio-button>
          <el-radio-button :value="'sold'">已售</el-radio-button>
          <el-radio-button :value="'offline'">下架</el-radio-button>
        </el-radio-group>
      </div>
      <el-button type="primary" @click="fetchStatusChanges">
        刷新
      </el-button>
    </div>

    <el-table :data="filteredItems" style="width: 100%" v-loading="loading">
      <el-table-column label="商品图片" width="120">
        <template #default="{ row }">
          <el-image 
            :src="row.img" 
            style="width: 80px; height: 80px"
            :preview-src-list="[row.img]"
            referrerpolicy="no-referrer"
          />
        </template>
      </el-table-column>
      <el-table-column label="商品名称" min-width="200">
        <template #default="{ row }">
          <div class="name-cell">{{ row.name }}</div>
        </template>
      </el-table-column>
      <el-table-column label="卖家" width="200">
        <template #default="{ row }">
          <div class="seller-info">
            <span class="seller-name">{{ row.seller_name }}</span>
            <el-link 
              v-if="row.seller_url"
              :href="row.seller_url" 
              target="_blank"
              type="primary"
              class="seller-uid"
            >
              UID: {{ row.seller_uid }}
            </el-link>
            <span v-else class="seller-uid">UID: {{ row.seller_uid }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.publish_status)">
            {{ getStatusText(row.publish_status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="price" label="价格" width="120">
        <template #default="{ row }">
          ¥{{ row.price.toFixed(2) }}
        </template>
      </el-table-column>
      <el-table-column prop="last_check_time" label="检查时间" width="180" />
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button 
            type="primary" 
            size="small" 
            @click="showItems(row.sku_id)"
          >
            查看详情
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页组件 -->
    <div class="pagination-container">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="statusChanges.total"
        layout="total, sizes, prev, pager, next"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- 商品详情对话框 -->
    <el-dialog
      v-model="dialogVisible"
      title="商品详情"
      width="70%"
    >
      <item-list :items="currentItems" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import ItemList from './ItemList.vue'
import { apiClient } from '../api/client'

interface StatusChange {
  id: number
  sku_id: number
  name: string
  img: string
  price: number
  publish_status: number
  last_check_time: string
  seller_name: string
  seller_uid: string
  seller_url: string
}

interface StatusChangeResponse {
  items: StatusChange[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

const statusChanges = ref<StatusChangeResponse>({
  items: [],
  total: 0,
  page: 1,
  page_size: 20,
  total_pages: 0
})
const loading = ref(false)
const dialogVisible = ref(false)
const currentItems = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const statusFilter = ref('all')

// 使用后端过滤后的商品列表
const filteredItems = computed(() => statusChanges.value.items)

const fetchStatusChanges = async () => {
  loading.value = true
  try {
    const response = await apiClient.get<StatusChangeResponse>('/status-changes', {
      params: {
        page: currentPage.value,
        page_size: pageSize.value,
        status: statusFilter.value
      }
    })
    statusChanges.value = response.data
  } catch (error) {
    ElMessage.error('获取状态变更记录失败')
  } finally {
    loading.value = false
  }
}

const handleSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1  // 重置页码
  fetchStatusChanges()
}

const handleCurrentChange = (page: number) => {
  currentPage.value = page
  fetchStatusChanges()
}

const showItems = async (skuId: number) => {
  try {
    const response = await apiClient.get(`/sku/${skuId}/items`)
    currentItems.value = response.data
    dialogVisible.value = true
  } catch (error) {
    ElMessage.error('获取商品详情失败')
  }
}

const getStatusType = (status: number) => {
  switch (status) {
    case 1:
      return 'success'
    case -2:
      return 'warning'
    default:
      return 'danger'
  }
}

const getStatusText = (status: number) => {
  switch (status) {
    case 1:
      return '在售'
    case -2:
      return '已售'
    default:
      return '已下架'
  }
}

// 监听状态过滤器变化，重新加载数据
watch(statusFilter, () => {
  currentPage.value = 1  // 重置页码
  fetchStatusChanges()
})

onMounted(() => {
  fetchStatusChanges()
})
</script>

<style scoped>
.status-changes {
  padding: 0;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

h2 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.name-cell {
  white-space: normal;
  word-break: break-all;
  line-height: 1.5;
}

.seller-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.seller-name {
  font-weight: 500;
}

.seller-uid {
  font-size: 12px;
  color: #909399;
}

:deep(.el-table .cell) {
  white-space: normal;
}

.left-controls {
  display: flex;
  align-items: center;
  gap: 16px;
}

:deep(.el-radio-button__inner) {
  padding: 8px 16px;
}
</style> 