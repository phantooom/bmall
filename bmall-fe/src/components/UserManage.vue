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
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button 
              type="danger" 
              size="small"
              @click="addToBlacklist(row)"
            >
              加入黑名单
            </el-button>
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
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button 
              type="primary" 
              size="small"
              @click="removeFromBlacklist(row)"
            >
              移出黑名单
            </el-button>
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
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
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
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

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
</style> 