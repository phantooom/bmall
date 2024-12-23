<template>
  <div class="sku-list">
    <div class="filter-bar">
      <div class="left-controls">
        <el-checkbox 
          v-model="isAllSelected"
          @change="toggleSelectAll"
          :indeterminate="isIndeterminate"
        >
          全选
        </el-checkbox>
        <el-button 
          type="danger" 
          :disabled="!selectedSkus.length"
          @click="handleBatchDelete"
        >
          批量删除 ({{ selectedSkus.length }})
        </el-button>
      </div>
      <div class="sort-controls">
        <el-radio-group v-model="sortBy" @change="handleSortChange" size="small">
          <el-radio-button value="">默认排序</el-radio-button>
          <el-radio-button value="total_items">
            数量{{ sortOrder === 'desc' ? '多到少' : '少到多' }}
          </el-radio-button>
          <el-radio-button value="min_price">
            价格{{ sortOrder === 'desc' ? '高到低' : '低到高' }}
          </el-radio-button>
        </el-radio-group>
        <el-button-group>
          <el-button 
            :type="sortOrder === 'desc' ? 'primary' : ''" 
            size="small"
            @click="toggleSortOrder"
          >
            降序
          </el-button>
          <el-button 
            :type="sortOrder === 'asc' ? 'primary' : ''" 
            size="small"
            @click="toggleSortOrder"
          >
            升序
          </el-button>
        </el-button-group>
      </div>
      <div class="right-controls">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索商品"
          clearable
          @input="handleSearch"
          class="search-input"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-select v-model="selectedBrand" placeholder="选择品牌" clearable @change="handleBrandChange">
          <el-option
            v-for="brand in brands"
            :key="brand.id"
            :label="`${brand.name} (${brand.total_items})`"
            :value="brand.id"
          />
        </el-select>
      </div>
    </div>
    
    <el-row :gutter="20">
      <el-col :span="6" v-for="sku in skuList.items" :key="sku.sku_id">
        <el-card :body-style="{ padding: '0px' }" class="sku-card">
          <div class="card-selection">
            <el-checkbox 
              :model-value="selectedSkus.includes(sku.sku_id)"
              @update:model-value="(val) => toggleSelection(sku.sku_id, val)"
            />
          </div>
          <el-image 
            :src="sku.img" 
            class="sku-image" 
            referrerpolicy="no-referrer"
            :lazy="true"
            loading="lazy"
            fit="cover"
          >
            <template #placeholder>
              <div class="image-placeholder">
                <el-icon><Picture /></el-icon>
              </div>
            </template>
            <template #error>
              <div class="image-error">
                <el-icon><PictureFilled /></el-icon>
              </div>
            </template>
          </el-image>
          <div class="sku-info">
            <h3>{{ sku.name }}</h3>
            <div class="price-info">
              <div class="market-price">
                市场价: ¥{{ sku.market_price.toFixed(2) }}
              </div>
              <div class="price-range">
                二手价: ¥{{ sku.price_range.min.toFixed(2) }} - ¥{{ sku.price_range.max.toFixed(2) }}
              </div>
            </div>
            <div class="total-items">
              在售数量: {{ sku.total_items }}
            </div>
            <div class="button-group">
              <el-button type="primary" @click="showItems(sku.sku_id)">查看详情</el-button>
              <el-button type="danger" @click="handleDelete(sku.sku_id)">删除</el-button>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <div class="pagination-container">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[20, 50, 100, 200]"
        :total="skuList.total"
        layout="total, sizes, prev, pager, next"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

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
import { ref, onMounted, watch } from 'vue'
import { apiClient } from '../api/client'
import { Picture, PictureFilled, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { SkuInfo, ItemDetail } from '../types'
import ItemList from './ItemList.vue'
import { API_BASE_URL } from '../config'

interface Brand {
  id: number
  name: string
  total_items: number
}

interface SkuListResponse {
  items: SkuInfo[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

const skuList = ref<SkuListResponse>({
  items: [],
  total: 0,
  page: 1,
  page_size: 100,
  total_pages: 0
})
const brands = ref<Brand[]>([])
const selectedBrand = ref<number | null>(null)
const searchKeyword = ref('')
const dialogVisible = ref(false)
const currentItems = ref<ItemDetail[]>([])
const currentPage = ref(1)
const pageSize = ref(100)
const sortBy = ref('')
const sortOrder = ref('desc')
const selectedSkus = ref<number[]>([])
const isAllSelected = ref(false)
const isIndeterminate = ref(false)

const fetchBrands = async () => {
  try {
    const response = await apiClient.get('/brands')
    brands.value = response.data
  } catch (error) {
    console.error('获取品牌列表失败:', error)
  }
}

const fetchSkus = async (
  brandId?: number, 
  page: number = 1, 
  pageSize: number = 100,
  keyword?: string,
  sort_by?: string,
  sort_order: string = 'desc'
) => {
  try {
    const params = new URLSearchParams()
    if (brandId) {
      params.set('brand_id', brandId.toString())
    }
    params.set('page', page.toString())
    params.set('page_size', pageSize.toString())
    if (keyword) {
      params.set('keyword', keyword)
    }
    if (sort_by) {
      params.set('sort_by', sort_by)
      params.set('sort_order', sort_order)
    }
    
    const response = await apiClient.get('/skus', { params })
    skuList.value = {
      ...response.data,
      items: response.data.items.map(sku => ({
        ...sku,
        img: sku.img.startsWith('//') ? `https:${sku.img}` : sku.img
      }))
    }
  } catch (error) {
    console.error('获取SKU列表失败:', error)
  }
}

const handleBrandChange = (brandId: number | null) => {
  currentPage.value = 1
  fetchSkus(brandId || undefined, currentPage.value, pageSize.value, searchKeyword.value, sortBy.value, sortOrder.value)
}

const handleSearch = (value: string) => {
  currentPage.value = 1
  fetchSkus(selectedBrand.value || undefined, currentPage.value, pageSize.value, value, sortBy.value, sortOrder.value)
}

const handleSizeChange = (size: number) => {
  pageSize.value = size
  fetchSkus(selectedBrand.value || undefined, currentPage.value, size, searchKeyword.value, sortBy.value, sortOrder.value)
}

const handleCurrentChange = (page: number) => {
  currentPage.value = page
  fetchSkus(selectedBrand.value || undefined, page, pageSize.value, searchKeyword.value, sortBy.value, sortOrder.value)
}

const handleSortChange = (value: string) => {
  fetchSkus(
    selectedBrand.value || undefined,
    currentPage.value,
    pageSize.value,
    searchKeyword.value,
    value,
    sortOrder.value
  )
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

const toggleSelection = (skuId: number, checked: boolean) => {
  if (checked) {
    selectedSkus.value.push(skuId)
  } else {
    const index = selectedSkus.value.indexOf(skuId)
    if (index !== -1) {
      selectedSkus.value.splice(index, 1)
    }
  }
  updateSelectAllStatus()
}

const toggleSelectAll = (val: boolean) => {
  if (val) {
    selectedSkus.value = skuList.value.items.map(sku => sku.sku_id)
  } else {
    selectedSkus.value = []
  }
  isIndeterminate.value = false
}

const updateSelectAllStatus = () => {
  const total = skuList.value.items.length
  const selected = selectedSkus.value.length
  isAllSelected.value = selected === total && total > 0
  isIndeterminate.value = selected > 0 && selected < total
}

// 在数据更新时也要更新全选状态
watch(() => skuList.value.items, () => {
  updateSelectAllStatus()
}, { deep: true })

const handleBatchDelete = async () => {
  if (!selectedSkus.value.length) {
    ElMessage.warning('请先选择要删除的商品')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedSkus.value.length} 个商品吗？删除后将同时删除该商品的所有 SKU，此操作不可恢复！`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const response = await apiClient.delete('/products/batch', {
      data: {
        productIds: selectedSkus.value
      }
    })

    if (response.data.success) {
      ElMessage.success('删除成功')
      // 刷新列表
      fetchSkus(
        selectedBrand.value || undefined,
        currentPage.value,
        pageSize.value,
        searchKeyword.value,
        sortBy.value,
        sortOrder.value
      )
      // 清空选择
      selectedSkus.value = []
    } else {
      throw new Error(response.data.message)
    }
  } catch (error) {
    if (error instanceof Error) {
      ElMessage.error('删除失败：' + error.message)
    }
  }
}

const handleDelete = async (skuId: number) => {
  try {
    await ElMessageBox.confirm(
      '确定要删除该商品吗？删除后将同时删除该商品的所有 SKU，此操作不可恢复！',
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const response = await apiClient.delete('/products/batch', {
      data: {
        productIds: [skuId]
      }
    })

    if (response.data.success) {
      ElMessage.success('删除成功')
      // 刷新列表
      fetchSkus(
        selectedBrand.value || undefined,
        currentPage.value,
        pageSize.value,
        searchKeyword.value,
        sortBy.value,
        sortOrder.value
      )
    } else {
      throw new Error(response.data.message)
    }
  } catch (error) {
    if (error instanceof Error) {
      ElMessage.error('删除失败：' + error.message)
    }
  }
}

const toggleSortOrder = () => {
  sortOrder.value = sortOrder.value === 'desc' ? 'asc' : 'desc'
  if (sortBy.value) {
    handleSortChange(sortBy.value)
  }
}

onMounted(() => {
  fetchSkus(undefined, currentPage.value, pageSize.value, searchKeyword.value, sortBy.value, sortOrder.value)
  fetchBrands()
})
</script>

<style scoped>
.sku-list {
  margin-top: 20px;
}

.sku-card {
  margin-bottom: 20px;
  transition: transform 0.3s;
}

.sku-card:hover {
  transform: translateY(-5px);
}

.sku-image {
  width: 100%;
  height: 200px;
  object-fit: cover;
}

.sku-info {
  padding: 14px;
}

.sku-info h3 {
  margin: 0;
  font-size: 16px;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.price-info {
  margin: 10px 0;
}

.market-price {
  color: #999;
  text-decoration: line-through;
  font-size: 14px;
}

.price-range {
  color: #f56c6c;
  font-size: 16px;
  font-weight: bold;
  margin-top: 5px;
}

.total-items {
  color: #67c23a;
  margin-bottom: 10px;
}

.filter-bar {
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.right-controls {
  display: flex;
  gap: 16px;
  align-items: center;
}

.search-input {
  width: 300px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.left-controls {
  display: flex;
  gap: 16px;
  align-items: center;
}

.card-selection {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 1;
  background-color: rgba(255, 255, 255, 0.8);
  border-radius: 4px;
  padding: 4px;
}

.sku-card {
  position: relative;
}

.button-group {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.sort-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}
</style> 