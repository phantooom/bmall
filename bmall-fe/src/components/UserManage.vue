<template>
  <div class="user-manage">
    <div class="header">
      <h2>用户管理</h2>
      <el-button type="primary" @click="fetchData">
        刷新
      </el-button>
    </div>

    <!-- 可疑用户列表 -->
    <div class="section">
      <h3>可疑用户 
        <el-tag type="danger">1小时内对同一商品上架超过20次</el-tag>
      </h3>
      <el-table :data="suspiciousUsers" style="width: 100%" v-loading="loading">
        <el-table-column label="用户信息" width="200">
          <template #default="{ row }">
            <div class="user-info">
              <span class="user-name">{{ row.uname }}</span>
              <el-link 
                :href="`https://space.bilibili.com/${row.uid}`"
                target="_blank"
                type="primary"
                class="user-uid"
              >
                UID: {{ row.uid }}
              </el-link>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="sku_name" label="商品名称" show-overflow-tooltip />
        <el-table-column prop="listing_count" label="上架次数" width="100" />
        <el-table-column label="上架时间" width="300">
          <template #default="{ row }">
            <div>首次: {{ row.first_listing }}</div>
            <div>最近: {{ row.last_listing }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="total_skus" label="商品种类" width="100" />
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button-group>
              <el-button 
                type="primary" 
                size="small"
                @click="showUserItems(row)"
              >
                查看商品
              </el-button>
              <el-button 
                v-if="!row.is_blacklisted"
                type="danger" 
                size="small"
                @click="addToBlacklist(row)"
              >
                加入黑名单
              </el-button>
              <el-button 
                v-else
                type="info" 
                size="small"
                @click="removeFromBlacklist(row)"
              >
                移除黑名单
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 黑名单用户列表 -->
    <div class="section">
      <h3>黑名单用户</h3>
      <el-table :data="blacklist.items" style="width: 100%" v-loading="loading">
        <el-table-column label="用户信息" width="200">
          <template #default="{ row }">
            <div class="user-info">
              <span class="user-name">{{ row.uname }}</span>
              <el-link 
                :href="`https://space.bilibili.com/${row.uid}`"
                target="_blank"
                type="primary"
                class="user-uid"
              >
                UID: {{ row.uid }}
              </el-link>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="原因" />
        <el-table-column prop="total_items" label="商品数量" width="100" />
        <el-table-column prop="created_at" label="加入时间" width="180" />
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button-group>
              <el-button 
                type="primary" 
                size="small"
                @click="showUserItems(row)"
              >
                查看商品
              </el-button>
              <el-button 
                type="primary" 
                size="small"
                @click="removeFromBlacklist(row)"
              >
                移出黑名单
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>

      <!-- 黑名单分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="blacklist.total"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </div>

    <!-- 用户统计面板 -->
    <div class="section">
      <h3>用户行为统计</h3>
      <el-tabs v-model="activePeriod">
        <el-tab-pane 
          v-for="(users, period) in userStats" 
          :key="period"
          :label="period"
          :name="period"
        >
          <el-table :data="users" style="width: 100%" v-loading="loading">
            <el-table-column label="用户信息" width="200">
              <template #default="{ row }">
                <div class="user-info">
                  <span class="user-name">
                    {{ row.uname }}
                    <el-tag 
                      v-if="row.is_blacklisted" 
                      type="danger" 
                      size="small"
                    >
                      黑名单
                    </el-tag>
                  </span>
                  <el-link 
                    :href="`https://space.bilibili.com/${row.uid}`"
                    target="_blank"
                    type="primary"
                    class="user-uid"
                  >
                    UID: {{ row.uid }}
                  </el-link>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="listing_count" label="上架数量" width="100" sortable />
            <el-table-column prop="sku_count" label="商品种类" width="100" sortable />
            <el-table-column label="价格区间" width="180">
              <template #default="{ row }">
                ¥{{ row.min_price.toFixed(2) }} - ¥{{ row.max_price.toFixed(2) }}
              </template>
            </el-table-column>
            <el-table-column label="上架时间" width="300">
              <template #default="{ row }">
                <div>首次: {{ row.first_listing }}</div>
                <div>最近: {{ row.last_listing }}</div>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200">
              <template #default="{ row }">
                <el-button-group>
                  <el-button 
                    type="primary" 
                    size="small"
                    @click="showUserItems(row)"
                  >
                    查看商品
                  </el-button>
                  <el-button 
                    v-if="!row.is_blacklisted"
                    type="danger" 
                    size="small"
                    @click="addToBlacklist({
                      uid: row.uid,
                      uname: row.uname,
                      reason: `${activePeriod}内上架 ${row.listing_count} 个商品`
                    })"
                  >
                    加入黑名单
                  </el-button>
                  <el-tooltip
                    v-else
                    :content="row.blacklist_reason"
                    placement="top"
                  >
                    <el-button 
                      type="info" 
                      size="small"
                      disabled
                    >
                      已拉黑
                    </el-button>
                  </el-tooltip>
                </el-button-group>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 用户商品对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="`${currentUser?.uname || ''} 的商品列表`"
      width="90%"
      destroy-on-close
    >
      <el-table :data="userItems" style="width: 100%" v-loading="itemsLoading">
        <template #header>
          <div class="compact-header"></div>
        </template>
        <el-table-column label="商品图片" width="80">
          <template #default="{ row }">
            <el-image 
              :src="row.img" 
              style="width: 50px; height: 50px"
              :preview-src-list="[row.img]"
              referrerpolicy="no-referrer"
              fit="cover"
              class="clickable"
              @click="showItems(row.sku_id)"
            />
          </template>
        </el-table-column>
        <el-table-column label="商品名称" min-width="120">
          <template #default="{ row }">
            <el-link 
              type="primary" 
              :underline="false"
              @click="showItems(row.sku_id)"
            >
              {{ row.name }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column label="价格区间" width="150">
          <template #default="{ row }">
            <div class="price-info">
              <span class="market-price">¥{{ row.market_price.toFixed(2) }}</span>
              <span class="price-range">
                ¥{{ row.min_price.toFixed(2) }} - ¥{{ row.max_price.toFixed(2) }}
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="listing_count" label="上架次数" width="80" sortable />
        <el-table-column label="上架时间" width="200">
          <template #default="{ row }">
            <div class="time-info">
              <span>首次: {{ formatDate(row.first_listing, true) }}</span>
              <span>最近: {{ formatDate(row.last_listing, true) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
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
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- SKU商品详情对话框 -->
    <el-dialog
      v-model="skuDialogVisible"
      title="商品详情"
      width="70%"
      append-to-body
    >
      <item-list :items="skuItems" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import ItemList from './ItemList.vue'

interface SuspiciousUser {
  uid: string
  uname: string
  sku_id: number
  sku_name: string
  listing_count: number
  first_listing: string
  last_listing: string
  total_skus: number
}

interface BlacklistUser {
  id: number
  uid: string
  uname: string
  reason: string
  created_at: string
  total_items: number
}

interface BlacklistResponse {
  items: BlacklistUser[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

interface UserStat {
  uid: string
  uname: string
  listing_count: number
  sku_count: number
  min_price: number
  max_price: number
  first_listing: string
  last_listing: string
  is_blacklisted: boolean
  blacklist_reason: string | null
}

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

const suspiciousUsers = ref<SuspiciousUser[]>([])
const blacklist = ref<BlacklistResponse>({
  items: [],
  total: 0,
  page: 1,
  page_size: 20,
  total_pages: 0
})
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const userStats = ref<Record<string, UserStat[]>>({})
const activePeriod = ref('1小时')
const dialogVisible = ref(false)
const itemsLoading = ref(false)
const currentUser = ref<SuspiciousUser | BlacklistUser | null>(null)
const userItems = ref<UserItem[]>([])
const skuDialogVisible = ref(false)
const skuItems = ref([])

const fetchData = async () => {
  loading.value = true
  try {
    // 获取可疑用户
    const suspiciousResponse = await axios.get<SuspiciousUser[]>('http://localhost:8000/api/suspicious-users')
    suspiciousUsers.value = suspiciousResponse.data

    // 获取黑名单用户
    const blacklistResponse = await axios.get<BlacklistResponse>('http://localhost:8000/api/blacklist', {
      params: {
        page: currentPage.value,
        page_size: pageSize.value
      }
    })
    blacklist.value = blacklistResponse.data

    // 获取用户统计数据
    const statsResponse = await axios.get<Record<string, UserStat[]>>('http://localhost:8000/api/user-stats')
    userStats.value = statsResponse.data
  } catch (error) {
    ElMessage.error('获取数据失败')
  } finally {
    loading.value = false
  }
}

const addToBlacklist = async (user: SuspiciousUser) => {
  try {
    await ElMessageBox.confirm(
      `确定将用户 ${user.uname}(UID:${user.uid}) 加入黑名单吗？`,
      '确认操作',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const response = await axios.post('http://localhost:8000/api/blacklist', {
      uid: user.uid,
      uname: user.uname,
      reason: `1小时内对商品 ${user.sku_name} 上架 ${user.listing_count} 次`
    })

    if (response.data.success) {
      ElMessage.success('已添加到黑名单')
      fetchData()
    } else {
      ElMessage.warning(response.data.message)
    }
  } catch (error) {
    if (error instanceof Error) {
      ElMessage.error('操作失败：' + error.message)
    }
  }
}

const removeFromBlacklist = async (user: BlacklistUser) => {
  try {
    await ElMessageBox.confirm(
      `确定将用户 ${user.uname}(UID:${user.uid}) 从黑名单中移除吗？`,
      '确认操作',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const response = await axios.delete(`http://localhost:8000/api/blacklist/${user.uid}`)
    if (response.data.success) {
      ElMessage.success('已从黑名单中移除')
      fetchData()
    }
  } catch (error) {
    if (error instanceof Error) {
      ElMessage.error('操作失败：' + error.message)
    }
  }
}

const handleSizeChange = (size: number) => {
  pageSize.value = size
  fetchData()
}

const handleCurrentChange = (page: number) => {
  currentPage.value = page
  fetchData()
}

const showUserItems = async (user: SuspiciousUser | BlacklistUser) => {
  currentUser.value = user
  dialogVisible.value = true
  itemsLoading.value = true
  
  try {
    const response = await axios.get<UserItem[]>('http://localhost:8000/api/user/items', {
      params: {
        uid: user.uid,
        uname: user.uname
      }
    })
    userItems.value = response.data
  } catch (error) {
    ElMessage.error('获取用户商品列表失败')
  } finally {
    itemsLoading.value = false
  }
}

const formatDate = (dateStr: string, short = false) => {
  // 将UTC时间转换为中国时区时间
  const date = new Date(dateStr + '+08:00')
  if (short) {
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    })
  }
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

const showItems = async (skuId: number) => {
  try {
    const response = await axios.get(`http://localhost:8000/api/sku/${skuId}/items`)
    skuItems.value = response.data
    skuDialogVisible.value = true
  } catch (error) {
    ElMessage.error('获取商品详情失败')
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.user-manage {
  padding: 0;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section {
  margin-bottom: 30px;
}

h2 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

h3 {
  margin: 0 0 16px 0;
  font-size: 18px;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.user-name {
  font-weight: 500;
}

.user-uid {
  font-size: 12px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.el-tabs {
  margin-top: 16px;
}

:deep(.el-table .cell) {
  white-space: normal;
}

.price-range {
  color: #f56c6c;
  font-weight: 500;
  margin-top: 4px;
}

.el-button-group {
  display: flex;
  gap: 8px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

:deep(.el-dialog__body) {
  padding: 20px;
}

:deep(.el-image) {
  border-radius: 4px;
  overflow: hidden;
}

/* 紧凑表格样式 */
.compact-header {
  height: 0;
  padding: 0;
}

:deep(.el-table__header-wrapper) {
  display: none;
}

:deep(.el-table__cell) {
  padding: 4px 0;
}

.price-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.market-price {
  font-size: 12px;
  color: #909399;
  text-decoration: line-through;
}

.price-range {
  color: #f56c6c;
  font-size: 14px;
}

.time-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 13px;
  line-height: 1.2;
}

:deep(.el-dialog__body) {
  padding: 10px;
}

:deep(.el-dialog__header) {
  padding: 15px;
  margin-right: 0;
}

:deep(.el-dialog__footer) {
  padding: 10px 15px;
}

:deep(.el-table) {
  --el-table-header-bg-color: #f5f7fa;
  --el-table-row-hover-bg-color: #f5f7fa;
}

:deep(.el-table__row) {
  height: 60px;
}

:deep(.el-table--enable-row-hover .el-table__body tr:hover > td) {
  background-color: var(--el-table-row-hover-bg-color);
}

.clickable {
  cursor: pointer;
  transition: transform 0.2s;
}

.clickable:hover {
  transform: scale(1.05);
}
</style> 