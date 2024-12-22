<template>
  <div class="item-list">
    <el-table 
      :data="items" 
      style="width: 100%"
      v-loading="loading"
      border
      stripe
    >
      <el-table-column label="卖家" min-width="200">
        <template #default="scope">
          <div class="seller-info">
            <div class="seller-detail">
              <div class="seller-info-row">
                <span class="seller-name">{{ scope.row.seller_name }}</span>
                <span class="seller-uid">UID: {{ scope.row.seller_uid }}</span>
                <el-tag 
                  :type="scope.row.publish_status === 1 ? 'success' : 'danger'"
                  size="small"
                >
                  {{ scope.row.publish_status === 1 ? '在售' : '已下架' }}
                </el-tag>
              </div>
              <template v-if="scope.row.seller_url">
                <el-link
                  type="primary"
                  :href="scope.row.seller_url"
                  target="_blank"
                  class="seller-space"
                >
                  个人空间
                </el-link>
              </template>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="price" label="价格" width="120" align="right">
        <template #default="scope">
          <span class="price">¥{{ scope.row.price.toFixed(2) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="market_price" label="市场价" width="120" align="right">
        <template #default="scope">
          <span class="market-price">¥{{ scope.row.market_price.toFixed(2) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="scope">
          <el-button
            type="primary"
            size="small"
            @click="openItemUrl(scope.row.url)"
            :type="scope.row.publish_status === 1 ? 'primary' : 'warning'"
          >
            {{ scope.row.publish_status === 1 ? '查看商品' : '查看链接' }}
          </el-button>
          <el-button
            v-if="scope.row.seller_url"
            type="info"
            size="small"
            @click="openSellerUrl(scope.row.seller_url)"
          >
            查看店铺
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { ItemDetail } from '../types'

defineProps<{
  items: ItemDetail[]
}>()

const loading = ref(false)

const openItemUrl = (url: string) => {
  window.open(url, '_blank')
}

const openSellerUrl = (url: string) => {
  window.open(url, '_blank')
}
</script>

<style scoped>
.item-list {
  margin-top: 20px;
}

.seller-info {
  display: flex;
  gap: 12px;
}

.seller-detail {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.seller-info-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.seller-name {
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.seller-uid {
  font-size: 12px;
  color: #909399;
}

.seller-space {
  font-size: 12px;
}

.price {
  font-weight: bold;
  color: #f56c6c;
}

.market-price {
  color: #909399;
  text-decoration: line-through;
}

:deep(.el-button + .el-button) {
  margin-left: 8px;
}

:deep(.el-table) {
  --el-table-border-color: #ebeef5;
  --el-table-header-bg-color: #f5f7fa;
}

:deep(.el-table__header) {
  font-weight: 600;
}

:deep(.el-tag) {
  margin-left: 4px;
}

:deep(.el-tag--success) {
  background-color: var(--el-color-success-light-9);
}

:deep(.el-tag--danger) {
  background-color: var(--el-color-danger-light-9);
}
</style> 