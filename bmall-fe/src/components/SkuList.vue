<template>
  <div class="sku-list">
    <div class="filter-bar">
      <div class="sort-controls">
        <el-radio-group v-model="sortBy" @change="handleSortChange">
          <el-radio-button label="total_items">按数量</el-radio-button>
          <el-radio-button label="min_price">按价格</el-radio-button>
        </el-radio-group>
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
            <el-button type="primary" @click="showItems(sku.sku_id)">查看详情</el-button>
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
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { Picture, PictureFilled, Search } from '@element-plus/icons-vue'
import type { SkuInfo, ItemDetail } from '../types'
import ItemList from './ItemList.vue'

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
const sortBy = ref('total_items')

const fetchBrands = async () => {
  try {
    const response = await axios.get<Brand[]>('http://localhost:8000/api/brands')
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
  sort?: string
) => {
  try {
    const url = new URL('http://localhost:8000/api/skus')
    if (brandId) {
      url.searchParams.set('brand_id', brandId.toString())
    }
    url.searchParams.set('page', page.toString())
    url.searchParams.set('page_size', pageSize.toString())
    if (keyword) {
      url.searchParams.set('keyword', keyword)
    }
    if (sort) {
      url.searchParams.set('sort_by', sort)
    }
    
    const response = await axios.get<SkuListResponse>(url.toString())
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
  fetchSkus(brandId || undefined, currentPage.value, pageSize.value, searchKeyword.value, sortBy.value)
}

const handleSearch = (value: string) => {
  currentPage.value = 1
  fetchSkus(selectedBrand.value || undefined, currentPage.value, pageSize.value, value, sortBy.value)
}

const handleSizeChange = (size: number) => {
  pageSize.value = size
  fetchSkus(selectedBrand.value || undefined, currentPage.value, size, searchKeyword.value, sortBy.value)
}

const handleCurrentChange = (page: number) => {
  currentPage.value = page
  fetchSkus(selectedBrand.value || undefined, page, pageSize.value, searchKeyword.value, sortBy.value)
}

const handleSortChange = (value: string) => {
  fetchSkus(
    selectedBrand.value || undefined,
    currentPage.value,
    pageSize.value,
    searchKeyword.value,
    value
  )
}

const showItems = async (skuId: number) => {
  try {
    const response = await axios.get<ItemDetail[]>(`http://localhost:8000/api/sku/${skuId}/items`)
    currentItems.value = response.data
    dialogVisible.value = true
  } catch (error) {
    console.error('获取商品列表失败:', error)
  }
}

onMounted(() => {
  fetchSkus(undefined, currentPage.value, pageSize.value, searchKeyword.value, sortBy.value)
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
</style> 