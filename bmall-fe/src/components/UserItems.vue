<template>
  <div class="user-items">
    <div class="header">
      <div class="user-info">
        <h3>{{ seller_name }}</h3>
        <el-link 
          :href="`https://space.bilibili.com/${seller_uid}`"
          target="_blank"
          type="primary"
          class="user-uid"
        >
          UID: {{ seller_uid }}
        </el-link>
      </div>
      <el-tag v-if="is_blacklisted" type="danger">黑名单用户</el-tag>
    </div>

    <el-table :data="items" style="width: 100%" v-loading="loading">
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
      <el-table-column prop="name" label="商品名称" show-overflow-tooltip />
      <el-table-column label="价格区间" width="180">
        <template #default="{ row }">
          <div>市场价：¥{{ row.market_price.toFixed(2) }}</div>
          <div class="price-range">
            ¥{{ row.min_price.toFixed(2) }} - ¥{{ row.max_price.toFixed(2) }}
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="listing_count" label="上架次数" width="100" sortable />
      <el-table-column label="上架时间" width="300">
        <template #default="{ row }">
          <div>首次: {{ formatDate(row.first_listing) }}</div>
          <div>最近: {{ formatDate(row.last_listing) }}</div>
        </template>
      </el-table-column>
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
import { apiClient } from '../api/client'
import ItemList from './ItemList.vue'

interface UserItem {
  sku_id: number
  name: string
  img: string
  market_price: number
  listing_count: number
  min_price: number
  max_price: number
  first_listing: string
  last_listing: string
}

const props = defineProps<{
  seller_uid: string
  seller_name: string
  is_blacklisted: boolean
}>()

const items = ref<UserItem[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const currentItems = ref([])

const fetchItems = async () => {
  loading.value = true
  try {
    const response = await apiClient.get('/user/items', {
      params: {
        uid: props.seller_uid,
        uname: props.seller_name
      }
    })
    items.value = response.data
  } catch (error) {
    ElMessage.error('获取用户商品列表失败')
  } finally {
    loading.value = false
  }
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

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  })
}

onMounted(() => {
  fetchItems()
})
</script>

<style scoped>
.user-items {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

h3 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.user-uid {
  font-size: 12px;
}

.price-range {
  color: #f56c6c;
  font-weight: 500;
}
</style> 