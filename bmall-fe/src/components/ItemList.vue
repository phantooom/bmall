<template>
  <div class="item-list">
    <div class="filter-bar">
      <el-switch
        v-model="showOffline"
        active-text="显示下架商品"
        @change="handleFilterChange"
      />
    </div>

    <el-table :data="currentItems" style="width: 100%">
      <el-table-column label="卖家信息" width="200">
        <template #default="{ row }">
          <div class="seller-info">
            <el-avatar 
              :size="40" 
              :src="row.seller_avatar"
              referrerpolicy="no-referrer"
            />
            <div class="seller-detail">
              <span class="seller-name">
                {{ row.seller_name }}
                <el-tag 
                  v-if="row.is_blacklisted" 
                  type="danger" 
                  size="small"
                >
                  黑名单
                </el-tag>
              </span>
              <el-link 
                :href="row.seller_url" 
                target="_blank"
                type="primary"
                class="seller-uid"
              >
                UID: {{ row.seller_uid }}
              </el-link>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="price" label="价格" width="120">
        <template #default="{ row }">
          ¥{{ row.price.toFixed(2) }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.publish_status === 1 ? 'success' : 'danger'">
            {{ row.publish_status === 1 ? '在售' : '已下架' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="上架时间" width="180">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-link 
            :href="row.url" 
            target="_blank"
            type="primary"
          >
            查看详情
          </el-link>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-container">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="filteredItems.length"
        layout="total, sizes, prev, pager, next"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { toBeijingTime } from '../utils/date'

interface ItemDetail {
  c2c_items_id: number
  seller_name: string
  seller_uid: string
  seller_avatar: string
  seller_url: string
  price: number
  market_price: number
  url: string
  publish_status: number
  created_at: string
  is_blacklisted: boolean
}

const props = defineProps<{
  items: ItemDetail[]
}>()

const showOffline = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)

// 过滤商品列表
const filteredItems = computed(() => {
  return showOffline.value 
    ? props.items 
    : props.items.filter(item => item.publish_status === 1)
})

// 当前页的商品
const currentItems = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredItems.value.slice(start, end)
})

const handleFilterChange = () => {
  currentPage.value = 1
}

const handleSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
}

const handleCurrentChange = (page: number) => {
  currentPage.value = page
}

const formatDate = (dateStr: string) => {
  return toBeijingTime(dateStr) as string
}
</script>

<style scoped>
.item-list {
  padding: 20px 0;
}

.filter-bar {
  margin-bottom: 20px;
  display: flex;
  justify-content: flex-end;
}

.seller-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.seller-detail {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.seller-name {
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
}

.seller-uid {
  font-size: 12px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

:deep(.el-avatar) {
  border-radius: 4px;
}
</style> 