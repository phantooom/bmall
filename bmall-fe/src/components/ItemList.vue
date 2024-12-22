<template>
  <div class="item-list">
    <el-table :data="items" style="width: 100%">
      <el-table-column label="卖家信息" width="200">
        <template #default="{ row }">
          <div class="seller-info">
            <el-image 
              :size="40" 
              :src="row.seller_avatar"
              referrerpolicy="no-referrer"
              style="width: 40px; height: 40px; border-radius: 4px;"
              :preview-src-list="[]"
            >
              <template #error>
                <div class="avatar-error">
                  <el-icon><User /></el-icon>
                </div>
              </template>
            </el-image>
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
  </div>
</template>

<script setup lang="ts">
import { defineProps } from 'vue'
import { User } from '@element-plus/icons-vue'

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
</script>

<style scoped>
.avatar-error {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f5f7fa;
  color: #909399;
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

:deep(.el-avatar) {
  border-radius: 4px;
}
</style> 