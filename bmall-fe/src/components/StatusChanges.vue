<template>
  <div class="status-changes">
    <div class="header">
      <h2>商品状态变更</h2>
      <el-button type="primary" @click="fetchStatusChanges">
        刷新
      </el-button>
    </div>

    <el-table :data="statusChanges.items" style="width: 100%" v-loading="loading">
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
          <el-tag :type="row.publish_status === 1 ? 'success' : 'danger'">
            {{ row.publish_status === 1 ? '在售' : '已下架' }}
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

    <!-- 添加分页组件 -->
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
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import ItemList from './ItemList.vue'

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

const fetchStatusChanges = async () => {
  loading.value = true
  try {
    const response = await axios.get<StatusChangeResponse>('http://localhost:8000/api/status-changes', {
      params: {
        page: currentPage.value,
        page_size: pageSize.value
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
  fetchStatusChanges()
}

const handleCurrentChange = (page: number) => {
  currentPage.value = page
  fetchStatusChanges()
}

const showItems = async (skuId: number) => {
  try {
    const response = await axios.get(`http://localhost:8000/api/sku/${skuId}/items`)
    currentItems.value = response.data
    dialogVisible.value = true
  } catch (error) {
    ElMessage.error('获取商品详情失败')
  }
}

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
</style> 